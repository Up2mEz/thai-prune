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


_DIAG, _DEL, _INS = 0, 1, 2


def align_anchored(reference: str, hypothesis: str
                   ) -> tuple[list[tuple[int | None, int | None]], int, int]:
    """Reference-anchored (semi-global) alignment and the matched window.

    Every reference character is aligned; hypothesis text before and after the
    best-matching window costs nothing. This scores *reading* the reference
    without charging for text the model produced outside it (a whole page when
    the reference is one region, or a runaway repetition after the answer);
    that surplus is reported separately as over-generation. Within the window,
    insertions, deletions and substitutions count as usual, so the distance is
    at most `len(reference)`.

    Returns (pairs, window_start, window_end) with pairs covering only the
    window. Ties prefer a diagonal step, then a deletion, then an insertion,
    and the earliest window end, so the result is deterministic.
    """
    n, m = len(reference), len(hypothesis)
    if n == 0:
        return [], 0, 0
    previous = [0] * (m + 1)          # free hypothesis prefix
    moves: list[bytearray] = [bytearray(m + 1)]
    for i in range(1, n + 1):
        a = reference[i - 1]
        current = [i] + [0] * m
        row = bytearray(m + 1)
        row[0] = _DEL
        for j in range(1, m + 1):
            diagonal = previous[j - 1] + (a != hypothesis[j - 1])
            deletion = previous[j] + 1
            insertion = current[j - 1] + 1
            best, move = diagonal, _DIAG
            if deletion < best:
                best, move = deletion, _DEL
            if insertion < best:
                best, move = insertion, _INS
            current[j] = best
            row[j] = move
        moves.append(row)
        previous = current
    end = min(range(m + 1), key=lambda j: (previous[j], j))  # free suffix
    pairs: list[tuple[int | None, int | None]] = []
    i, j = n, end
    while i > 0:
        move = moves[i][j] if j > 0 else _DEL
        if move == _DIAG:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif move == _DEL:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    pairs.reverse()
    return pairs, j, end


def _fates_from(pairs, reference: str, hypothesis: str):
    fates: dict[int, str] = {}
    substitute: dict[int, str] = {}
    for ref_index, hyp_index in pairs:
        if ref_index is None:
            continue
        if hyp_index is None:
            fates[ref_index] = "deleted"
        elif reference[ref_index] == hypothesis[hyp_index]:
            fates[ref_index] = "correct"
        else:
            fates[ref_index] = "substituted"
            substitute[ref_index] = hypothesis[hyp_index]
    return fates, substitute


def reference_fates(reference: str, hypothesis: str) -> dict[int, str]:
    """Fate of every reference character: correct, deleted, or substituted."""
    return _fates_from(align(reference, hypothesis), reference, hypothesis)[0]


def _base_index(reference: str, index: int) -> int | None:
    j = index - 1
    while j >= 0 and reference[j] in COMBINING:
        j -= 1
    return j if j >= 0 and reference[j] in CONSONANTS else None


def mark_decomposition(reference: str, hypothesis: str,
                       pairs: list | None = None) -> dict[str, Any]:
    """Per-class counts of mark fates, overall and conditioned on a correct base.

    One alignment serves everything: pass `pairs` to reuse an alignment the
    caller already computed, since a full page makes alignment the dominant cost.
    """
    if pairs is None:
        pairs = align(reference, hypothesis)
    fates, substitute = _fates_from(pairs, reference, hypothesis)

    out: dict[str, Any] = {}
    for name, members in MARK_CLASSES.items():
        counts = collections.Counter()
        for index, char in enumerate(reference):
            if char not in members:
                continue
            fate = fates.get(index, "deleted")
            if fate == "substituted":
                fate = "same_class" if substitute.get(index) in members else "other_char"
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


def edit_distance_from(pairs, reference: str, hypothesis: str) -> int:
    return sum(
        1 for r, h in pairs
        if r is None or h is None or reference[r] != hypothesis[h]
    )


def is_repetitive(text: str, *, tail: int = 200, span: int = 20, times: int = 3) -> bool:
    """Whether the last `tail` characters repeat some `span`-character substring."""
    window = text[-tail:]
    if len(window) < span * times:
        return False
    seen = collections.Counter(window[i : i + span] for i in range(len(window) - span + 1))
    return any(count >= times for count in seen.values())

