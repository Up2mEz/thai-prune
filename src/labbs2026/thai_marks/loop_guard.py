"""Windowed no-repeat n-gram blocking, as DeepSeek-OCR ships it (T5 arm `ngram_block`).

Reimplements `NoRepeatNGramLogitsProcessor` from DeepSeek-OCR
(`DeepSeek-OCR-vllm/process/ngram_norepeat.py`; the same class in vLLM
`model_executor/models/deepseek_ocr.py`, where it reads the request's output
token ids). At each step, any token that would complete an n-gram already
present among the last `window_size` generated tokens is banned, except
whitelisted tokens. DeepSeek-OCR's recommended setting is `ngram_size=30`,
`window_size=90`, whitelisting its `<td>` and `</td>` tokens.

Only generated tokens are searched (as vLLM's output ids), never the prompt.
`docs/stage0/T5_LOOP_DECODING_DRAFT.md`.
"""

from __future__ import annotations

from typing import Iterable, Sequence


def banned_tokens(output_ids: Sequence[int], ngram_size: int, window_size: int,
                  whitelist: Iterable[int] = ()) -> set[int]:
    """Tokens the reference implementation bans at the next step."""
    if ngram_size <= 0 or window_size <= 0:
        raise ValueError("ngram_size and window_size must be positive")
    if len(output_ids) < ngram_size:
        return set()
    prefix = tuple(output_ids[len(output_ids) - (ngram_size - 1):]) if ngram_size > 1 else ()
    start = max(0, len(output_ids) - window_size)
    end = len(output_ids) - ngram_size + 1
    banned = set()
    for i in range(start, end):
        ngram = tuple(output_ids[i:i + ngram_size])
        if ngram[:-1] == prefix:
            banned.add(ngram[-1])
    return banned - set(whitelist)


class WindowedNoRepeatNGram:
    """A transformers logits processor (batch size 1) applying `banned_tokens`.

    `prompt_length` is the length of the prompt in `input_ids`, so only
    generated tokens are searched; None takes it from the first call, which
    `generate()` makes before any token is generated. `interventions` counts the steps at which
    the ban removed the token greedy decoding would have chosen — the steps
    where the output actually differs from plain greedy.
    """

    def __init__(self, ngram_size: int, window_size: int, prompt_length: int | None = None,
                 whitelist: Iterable[int] = ()):
        self.ngram_size = int(ngram_size)
        self.window_size = int(window_size)
        self.prompt_length = None if prompt_length is None else int(prompt_length)
        self.whitelist = frozenset(int(t) for t in whitelist)
        self.interventions = 0
        self.steps = 0

    def __call__(self, input_ids, scores):
        if input_ids.shape[0] != 1:
            raise ValueError("WindowedNoRepeatNGram supports batch size 1 only")
        if self.prompt_length is None:
            self.prompt_length = int(input_ids.shape[1])
        output = input_ids[0, self.prompt_length:].tolist()
        banned = banned_tokens(output, self.ngram_size, self.window_size, self.whitelist)
        self.steps += 1
        if not banned:
            return scores
        if int(scores[0].argmax()) in banned:
            self.interventions += 1
        scores = scores.clone()
        scores[0, sorted(banned)] = -float("inf")
        return scores


def whitelist_ids(tokenizer, texts: Iterable[str]) -> list[int]:
    """Every token id that makes up the whitelisted texts, as encoded alone.

    DeepSeek-OCR whitelists its `<td>` and `</td>` tokens so that runs of
    table cells (e.g. empty `<td></td>` rows) are never blocked. In the Qwen
    tokenizer those tags are several tokens each (`<td>` = `<td` + `>`;
    `<td></td>` = `<td` + `></` + `td` + `>`), so the closest equivalent
    whitelists all of their pieces, including the common `>`. Pass the texts
    as they occur (`<td>`, `</td>`, `<td></td>`); the ids are recorded per run.
    """
    ids: set[int] = set()
    for text in texts:
        ids.update(int(t) for t in tokenizer.encode(text, add_special_tokens=False))
    return sorted(ids)
