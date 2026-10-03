"""Scoring short region answers: was the text found, and how well was it read.

A Fine-grained answer is a few words; a model that fails to follow the box may
return another line, or the whole page. Global CER mixes those failures with
misreading. Here the reference is aligned against the **best-matching window**
of the hypothesis (semi-global edit distance: free start and end in the
hypothesis):

- `found`: window distance / reference length <= `FOUND_MAX`;
- reading error is measured on the window only: CER, and per reference mark its
  fate and whether its base consonant was read correctly (`mark_fates`, the
  same conditioning as T1's `mark_decomposition`). Marks with a misread base
  are not scored, which already removes wrong-line answers from mark rates;
  an answer with no base-correct mark at all is a localisation failure.
- `extra_chars`: hypothesis characters outside the window (over-generation).

A long hypothesis can contain a short reference by chance; `chance_found_rate`
estimates that rate by scoring each reference against another item's
hypothesis, and is reported next to every found rate.
"""

from __future__ import annotations

from typing import Any, Sequence

from labbs2026.thai_marks.decompose import align, mark_decomposition
from labbs2026.thai_marks.orthography import COMBINING, CONSONANTS, LOWER_VOWELS, TONE_MARKS, UPPER_VOWELS

FOUND_MAX = 0.5   # fixed before any F1 output; descriptive only (no decision rule uses it)
KIND_OF = {**{c: "TONE" for c in TONE_MARKS}, **{c: "UPPER" for c in UPPER_VOWELS},
           **{c: "LOWER" for c in LOWER_VOWELS}}


def mark_fates(reference: str, hypothesis: str) -> list[dict[str, Any]]:
    """Every reference mark: class, fate against `hypothesis`, and whether its base
    consonant was read correctly. Mirrors `thai_marks.decompose.mark_decomposition`
    (same alignment, same base rule), but keeps marks individually so two arms
    can be paired mark by mark."""
    fate_of: dict[int, str] = {}
    sub_of: dict[int, str] = {}
    for r, h in align(reference, hypothesis):
        if r is None:
            continue
        if h is None:
            fate_of[r] = "deleted"
        elif reference[r] == hypothesis[h]:
            fate_of[r] = "correct"
        else:
            fate_of[r] = "substituted"
            sub_of[r] = hypothesis[h]
    out = []
    for i, char in enumerate(reference):
        kind = KIND_OF.get(char)
        if kind is None:
            continue
        j = i - 1
        while j >= 0 and reference[j] in COMBINING:
            j -= 1
        base = j if j >= 0 and reference[j] in CONSONANTS else None
        fate = fate_of.get(i, "deleted")
        if fate == "substituted":
            fate = "same_class" if KIND_OF.get(sub_of.get(i)) == kind else "other_char"
        out.append({"index": i, "kind": kind, "fate": fate,
                    "base_correct": base is not None and fate_of.get(base) == "correct"})
    return out


def best_window(reference: str, hypothesis: str) -> tuple[int, int, int]:
    """(distance, start, end): min edit distance of `reference` to any `hypothesis[start:end]`.

    Two-row DP over the reference with free leading and trailing hypothesis
    characters; ties prefer the earliest end, then the latest start.
    """
    m = len(reference)
    if m == 0:
        return 0, 0, 0
    # entry j: (cost, start) of the best alignment of reference[:i] ending at hypothesis[:j]
    prev = [(0, j) for j in range(len(hypothesis) + 1)]
    for i in range(1, m + 1):
        cur = [(i, 0)]
        a = reference[i - 1]
        for j in range(1, len(hypothesis) + 1):
            diag = (prev[j - 1][0] + (a != hypothesis[j - 1]), prev[j - 1][1])
            up = (prev[j][0] + 1, prev[j][1])
            left = (cur[j - 1][0] + 1, cur[j - 1][1])
            cur.append(min(diag, up, left, key=lambda t: (t[0], -t[1])))
        prev = cur
    end = min(range(len(hypothesis) + 1), key=lambda j: (prev[j][0], j))
    return prev[end][0], prev[end][1], end


def score_answer(reference: str, hypothesis: str) -> dict[str, Any]:
    """Found / read metrics for one normalized (reference, hypothesis) pair."""
    if not reference:
        return {"ref_chars": 0, "found": None}
    distance, start, end = best_window(reference, hypothesis)
    window = hypothesis[start:end]
    out: dict[str, Any] = {
        "ref_chars": len(reference), "hyp_chars": len(hypothesis),
        "window_distance": distance, "window_cer": distance / len(reference),
        "found": distance / len(reference) <= FOUND_MAX,
        "exact": distance == 0,
        "extra_chars": len(hypothesis) - len(window),
    }
    marks = mark_decomposition(reference, window)
    out["mark_fates"] = mark_fates(reference, window)
    out["has_base_correct_mark"] = any(m["base_correct"] for m in out["mark_fates"])
    out["consonant_n"] = marks["CONSONANT"]["n"]
    out["consonant_error"] = marks["CONSONANT"]["error"]
    for kind in ("TONE", "UPPER", "LOWER"):
        out[f"{kind}_base_n"] = marks[kind].get("base_correct_n", 0)
        out[f"{kind}_base_error"] = marks[kind].get("base_correct_error", 0)
        out[f"{kind}_n"] = marks[kind].get("n", 0)
        out[f"{kind}_error"] = marks[kind].get("n", 0) - marks[kind].get("correct", 0)
    return out


def chance_found_rate(references: Sequence[str], hypotheses: Sequence[str]) -> float | None:
    """Found rate when reference i is scored against hypothesis i+1 (cyclic)."""
    if len(hypotheses) < 2:
        return None
    pairs = [(r, hypotheses[(i + 1) % len(hypotheses)]) for i, r in enumerate(references) if r]
    if not pairs:
        return None
    return sum(best_window(r, h)[0] / len(r) <= FOUND_MAX for r, h in pairs) / len(pairs)
