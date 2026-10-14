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

    `stride` > 1 checks every `stride`-th token only, to save the decode and the
    search. The output is unchanged if it is then finished with `stopped_output`:
    a run found in a prefix is found in every longer one, and greedy decoding is
    prefix-deterministic, so the tokens up to the first firing are the same and
    `first_stop` finds that token afterwards. `decode` replaces the tokenizer's
    decode where a runner's record text is decoded differently.
    """

    def __init__(self, tokenizer, prompt_length: int, k: int = K, k_long: int = K_LONG,
                 stride: int = 1, decode: Callable[[Sequence[int]], str] | None = None):
        self.tokenizer, self.prompt_length, self.k, self.k_long = tokenizer, prompt_length, k, k_long
        self.stride = int(stride)
        self.decode = decode or (lambda ids: tokenizer.decode(list(ids), skip_special_tokens=True))
        self.stopped_at: int | None = None

    def __call__(self, input_ids, scores, **kwargs) -> bool:
        generated = input_ids[0, self.prompt_length:].tolist()
        if len(generated) % self.stride:
            return False
        if loop_found(self.decode(generated), self.k, self.k_long):
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


def stopped_output(ids: Sequence[int], decode: Callable[[Sequence[int]], str],
                   k: int = K, k_long: int = K_LONG) -> dict:
    """The output of greedy decoding under the criterion, from the tokens generated with it attached.

    The tokens may run past the first firing (a `stride` > 1, or generation that ended
    first); `first_stop` finds the firing token and the text is cut there, as `replay` does.
    """
    t = first_stop(ids, decode, k, k_long)
    text = decode(ids) if t is None else cut_at_loop(decode(ids[:t]), k, k_long)
    return {"first_stop": t, "text": text}


def live_items(rows: list[dict], sample: int, seed: int, k: int = K, k_long: int = K_LONG) -> list[dict]:
    """The calibration outputs a live check generates again: every one the offline cut changes,
    and a seeded sample of `sample` it leaves unchanged. Rows are one model's outputs at one prompt."""
    import random

    rows = sorted(rows, key=lambda r: r["id"])
    looping = [r for r in rows if cut_at_loop(r["raw_output"], k, k_long) != r["raw_output"]]
    rest = [r for r in rows if cut_at_loop(r["raw_output"], k, k_long) == r["raw_output"]]
    chosen = random.Random(seed).sample(rest, min(sample, len(rest)))
    return ([{"id": r["id"], "looping_offline": True} for r in looping]
            + [{"id": r["id"], "looping_offline": False} for r in sorted(chosen, key=lambda r: r["id"])])
