"""What happens to each Thai mark between reference and hypothesis.

A codepoint Levenshtein alignment assigns every reference mark a fate. The
*mark-specific* error counts only marks whose base consonant was itself read
correctly, which separates a mark that failed on its own from one lost with a
misread syllable — the distinction `THAI_MARK_FAILURE_MODES.md` §7 made on the
earlier backbone and that this module makes reusable and tested.
"""

from __future__ import annotations

import collections
from typing import Any

from labbs2026.thai_marks.orthography import (
    COMBINING,
    CONSONANTS,
    LOWER_VOWELS,
    TONE_MARKS,
    UPPER_VOWELS,
)

MARK_CLASSES = {
    "TONE": frozenset(TONE_MARKS),
    "UPPER": frozenset(UPPER_VOWELS),
    "LOWER": frozenset(LOWER_VOWELS),
}


def align(reference: str, hypothesis: str) -> list[tuple[int | None, int | None]]:
    """Levenshtein alignment as (reference index, hypothesis index) pairs.

    Ties prefer a diagonal step, then a deletion, then an insertion, so the
    result is deterministic.
    """
    n, m = len(reference), len(hypothesis)
    previous = list(range(m + 1))
    rows = [previous]
    for i in range(1, n + 1):
        current = [i] + [0] * m
        a = reference[i - 1]
        for j in range(1, m + 1):
            current[j] = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (a != hypothesis[j - 1]),
            )
        rows.append(current)
        previous = current
    pairs: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and rows[i][j] == rows[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]):
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and rows[i][j] == rows[i - 1][j] + 1:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    pairs.reverse()
    return pairs


def reference_fates(reference: str, hypothesis: str) -> dict[int, str]:
    """Fate of every reference character: correct, deleted, or substituted."""
    fates: dict[int, str] = {}
    for ref_index, hyp_index in align(reference, hypothesis):
        if ref_index is None:
            continue
        if hyp_index is None:
            fates[ref_index] = "deleted"
        elif reference[ref_index] == hypothesis[hyp_index]:
            fates[ref_index] = "correct"
        else:
            fates[ref_index] = "substituted"
    return fates


def _base_index(reference: str, index: int) -> int | None:
    j = index - 1
    while j >= 0 and reference[j] in COMBINING:
        j -= 1
    return j if j >= 0 and reference[j] in CONSONANTS else None


def mark_decomposition(reference: str, hypothesis: str) -> dict[str, Any]:
    """Per-class counts of mark fates, overall and conditioned on a correct base."""
    fates = reference_fates(reference, hypothesis)
    substitution_class: dict[int, str] = {}
    for ref_index, hyp_index in align(reference, hypothesis):
        if ref_index is not None and hyp_index is not None:
            substitution_class[ref_index] = hypothesis[hyp_index]

    out: dict[str, Any] = {}
    for name, members in MARK_CLASSES.items():
        counts = collections.Counter()
        for index, char in enumerate(reference):
            if char not in members:
                continue
            fate = fates.get(index, "deleted")
            if fate == "substituted":
                fate = "same_class" if substitution_class.get(index) in members else "other_char"
            counts["n"] += 1
            counts[fate] += 1
            base = _base_index(reference, index)
            if base is not None and fates.get(base) == "correct":
                counts["base_correct_n"] += 1
                counts["base_correct_error"] += fate != "correct"
        out[name] = dict(counts)
    consonants = [i for i, c in enumerate(reference) if c in CONSONANTS]
    out["CONSONANT"] = {
        "n": len(consonants),
        "error": sum(fates.get(i) != "correct" for i in consonants),
    }
    return out


def is_repetitive(text: str, *, tail: int = 200, span: int = 20, times: int = 3) -> bool:
    """Whether the last `tail` characters repeat some `span`-character substring."""
    window = text[-tail:]
    if len(window) < span * times:
        return False
    seen = collections.Counter(window[i : i + span] for i in range(len(window) - span + 1))
    return any(count >= times for count in seen.values())

