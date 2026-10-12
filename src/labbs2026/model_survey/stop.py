"""The stop at a loop as a decode-time stopping criterion (W4, Up2mEz's addition 1).

T5b, W1, M5 and M6 cut finished outputs offline with `loop_cut.variant_b`
(k = 8, k_long = 6). This module stops generation instead: after every new
token it decodes the generated text and stops as soon as `loop_onset` finds a
run. The final output is that prefix cut with `cut_at_loop`, the same rule.

Greedy decoding is prefix-deterministic, so the stopped output equals the
offline cut exactly when the earliest prefix in which a run is found already
contains the run the full output's cut keeps. `replay` checks this on recorded
outputs without a GPU.

`thai_marks.loop_cut` is imported read-only; it is Up2mEz's file.
"""

from __future__ import annotations

from typing import Callable, Sequence

from labbs2026.thai_marks.loop_cut import cut_at_loop, loop_onset

K, K_LONG = 8, 6  # variant_b


def loop_found(text: str, k: int = K, k_long: int = K_LONG) -> bool:
    return loop_onset(text, k, k_long) is not None


class LoopStoppingCriteria:
    """A `transformers` stopping criterion: stop when the generated text holds a run.

    `prompt_length` is the number of input tokens; only the tokens after it are
    decoded. Works for batch size 1, as every runner here generates one item at a time.
    """

    def __init__(self, tokenizer, prompt_length: int, k: int = K, k_long: int = K_LONG):
        self.tokenizer, self.prompt_length, self.k, self.k_long = tokenizer, prompt_length, k, k_long
        self.stopped_at: int | None = None

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        generated = input_ids[0, self.prompt_length:].tolist()
        text = self.tokenizer.decode(generated, skip_special_tokens=True)
        if loop_found(text, self.k, self.k_long):
            self.stopped_at = len(generated)
            return True
        return False

    def finish(self, text: str) -> str:
        """The output after stopping: the same cut as `variant_b`."""
        return cut_at_loop(text, self.k, self.k_long)


def first_stop(ids: Sequence[int], decode: Callable[[Sequence[int]], str],
               k: int = K, k_long: int = K_LONG) -> int | None:
    """The number of tokens after which the criterion first fires, or None.

    The criterion fires on the first prefix whose decoded text holds a run. A run
    found in a prefix is still found in every longer prefix, so the first firing
    is found by bisection; both neighbours of the answer are checked directly.
    """
    if not loop_found(decode(ids), k, k_long):
        return None
    lo, hi = 1, len(ids)          # loop_found(decode(ids[:hi])) is true
    while lo < hi:
        mid = (lo + hi) // 2
        if loop_found(decode(ids[:mid]), k, k_long):
            hi = mid
        else:
            lo = mid + 1
    if lo > 1 and loop_found(decode(ids[:lo - 1]), k, k_long):
        raise AssertionError("a run found in a prefix was lost in a longer one")
    return lo


def replay(ids: Sequence[int], decode: Callable[[Sequence[int]], str], offline: str,
           k: int = K, k_long: int = K_LONG) -> dict:
    """Replay greedy decoding of `ids` under the criterion and compare with the offline cut."""
    full = decode(ids)
    t = first_stop(ids, decode, k, k_long)
    stopped = full if t is None else cut_at_loop(decode(ids[:t]), k, k_long)
    return {"tokens": len(ids), "stopped_at": t, "equal": stopped == offline,
            "stopped_chars": len(stopped), "offline_chars": len(offline)}
