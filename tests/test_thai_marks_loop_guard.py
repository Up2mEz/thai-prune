"""Windowed no-repeat n-gram blocking matches DeepSeek-OCR's reference logic."""

from __future__ import annotations

import random

import pytest

from labbs2026.thai_marks.loop_guard import WindowedNoRepeatNGram, banned_tokens, whitelist_ids


def _reference(input_ids, ngram_size, window_size, whitelist):
    # Verbatim logic of DeepSeek-OCR NoRepeatNGramLogitsProcessor.__call__.
    if len(input_ids) < ngram_size:
        return set()
    current_prefix = tuple(input_ids[-(ngram_size - 1):])
    search_start = max(0, len(input_ids) - window_size)
    search_end = len(input_ids) - ngram_size + 1
    banned = set()
    for i in range(search_start, search_end):
        ngram = tuple(input_ids[i:i + ngram_size])
        if ngram[:-1] == current_prefix:
            banned.add(ngram[-1])
    return banned - set(whitelist)


@pytest.mark.parametrize("seed", range(20))
def test_matches_the_reference_on_random_repetitive_sequences(seed: int) -> None:
    rng = random.Random(seed)
    unit = [rng.randrange(6) for _ in range(rng.randrange(1, 8))]
    ids = (unit * 20)[: rng.randrange(5, 120)] + [rng.randrange(6) for _ in range(rng.randrange(0, 10))]
    for n, w in ((3, 10), (5, 20), (30, 90), (2, 4)):
        for k in range(len(ids) + 1):
            assert banned_tokens(ids[:k], n, w, {1}) == _reference(ids[:k], n, w, {1})


def test_a_loop_is_blocked_and_fresh_text_is_not() -> None:
    loop = [7, 8, 9] * 4
    assert banned_tokens(loop, 3, 12) == {7}
    assert banned_tokens([1, 2, 3, 4, 5, 6], 3, 12) == set()


def test_repeats_outside_the_window_are_allowed() -> None:
    ids = [7, 8, 9] + list(range(20, 40)) + [7, 8]
    assert banned_tokens(ids, 3, 90) == {9}
    assert banned_tokens(ids, 3, 10) == set()


def test_whitelisted_tokens_are_never_banned() -> None:
    assert banned_tokens([5, 6] * 5, 2, 20, whitelist={5, 6}) == set()


def test_invalid_sizes_are_rejected() -> None:
    with pytest.raises(ValueError):
        banned_tokens([1, 2], 0, 5)


torch = pytest.importorskip("torch")


def test_processor_searches_only_generated_tokens_and_counts_interventions() -> None:
    prompt = [7, 8, 9, 7, 8]  # would ban 9 if the prompt were searched
    proc = WindowedNoRepeatNGram(2, 90, prompt_length=len(prompt))
    scores = torch.zeros(1, 12)
    scores[0, 9] = 5.0
    out = proc(torch.tensor([prompt]), scores)
    assert torch.equal(out, scores) and proc.interventions == 0

    generated = [1, 2, 1]  # next 2 would repeat "1 2"
    scores = torch.zeros(1, 12)
    scores[0, 2] = 5.0
    out = proc(torch.tensor([prompt + generated]), scores)
    assert out[0, 2] == -float("inf") and int(out[0].argmax()) != 2
    assert proc.interventions == 1 and proc.steps == 2


def test_processor_bans_without_counting_when_greedy_choice_is_allowed() -> None:
    proc = WindowedNoRepeatNGram(2, 90, prompt_length=0)
    scores = torch.zeros(1, 12)
    scores[0, 4] = 5.0
    out = proc(torch.tensor([[1, 2, 1]]), scores)
    assert out[0, 2] == -float("inf") and int(out[0].argmax()) == 4
    assert proc.interventions == 0


def test_prompt_length_is_taken_from_the_first_call() -> None:
    proc = WindowedNoRepeatNGram(2, 90)
    scores = torch.zeros(1, 12)
    proc(torch.tensor([[7, 8, 7]]), scores)  # the prompt: nothing generated yet
    assert proc.prompt_length == 3 and proc.interventions == 0
    scores[0, 2] = 5.0
    out = proc(torch.tensor([[7, 8, 7, 1, 2, 1]]), scores)
    assert out[0, 2] == -float("inf") and out[0, 8] == 0


def test_processor_rejects_batches() -> None:
    proc = WindowedNoRepeatNGram(3, 90, prompt_length=0)
    with pytest.raises(ValueError):
        proc(torch.tensor([[1, 2], [3, 4]]), torch.zeros(2, 12))


class _Tok:
    def encode(self, text, add_special_tokens=False):
        return {"<td>": [6868, 29], "</td>": [522, 1296, 29], "<td></td>": [6868, 1472, 1296, 29]}[text]


def test_whitelist_takes_every_piece_of_the_tags() -> None:
    assert whitelist_ids(_Tok(), ["<td>", "</td>", "<td></td>"]) == [29, 522, 1296, 1472, 6868]


def test_runs_of_empty_cells_are_not_blocked_when_their_pieces_are_whitelisted() -> None:
    cells = [6868, 1472, 1296, 29] * 30
    assert banned_tokens(cells, 30, 90, whitelist_ids(_Tok(), ["<td></td>"])) == set()
    assert banned_tokens(cells, 30, 90) != set()
