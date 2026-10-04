"""Cut an output at its loop onset (`docs/stage0/T5B_STOP_AT_LOOP_DRAFT.md`).

Greedy decoding is prefix-deterministic, so the cut output is what stopping
decoding at the onset would have produced. A run is a substring of 4–400
characters containing a Thai consonant or Latin letter, repeated exactly and
consecutively at least `k` times (`k_long` for units of 50+ characters). The
cut keeps the first copy of the unit.
"""

from __future__ import annotations

import re
from functools import lru_cache

LETTER = re.compile(r"[A-Za-zก-ฮ]")
LONG_UNIT = 50
MAX_UNIT = 400
MIN_UNIT = 4


@lru_cache(maxsize=8)
def _patterns(k: int, k_long: int) -> tuple[re.Pattern, re.Pattern]:
    short = re.compile(r"(.{%d,%d}?)\1{%d,}" % (MIN_UNIT, LONG_UNIT - 1, k - 1), re.S)
    long = re.compile(r"(.{%d,%d}?)\1{%d,}" % (LONG_UNIT, MAX_UNIT, k_long - 1), re.S)
    return short, long


def _first_run(text: str, pattern: re.Pattern) -> tuple[int, int] | None:
    pos = 0
    while True:
        m = pattern.search(text, pos)
        if m is None:
            return None
        if LETTER.search(m.group(1)):
            return m.start(), len(m.group(1))
        pos = m.start() + 1


def loop_onset(text: str, k: int, k_long: int) -> tuple[int, int] | None:
    """(start, unit length) of the earliest run, or None."""
    found = [r for r in (_first_run(text, p) for p in _patterns(k, k_long)) if r]
    return min(found) if found else None


def cut_at_loop(text: str, k: int, k_long: int) -> str:
    onset = loop_onset(text, k, k_long)
    if onset is None:
        return text
    start, unit = onset
    return text[:start + unit]


def variant_a(record: dict) -> str:
    """Cut runaway outputs only (reached `max_new_tokens`), k = 4 / 3."""
    if not record["reached_max_new_tokens"]:
        return record["raw_output"]
    return cut_at_loop(record["raw_output"], 4, 3)


def variant_b(record: dict) -> str:
    """Stop during decoding: every output, k = 8 / 6."""
    return cut_at_loop(record["raw_output"], 8, 6)
