"""Where each wrongly transcribed reference mark comes from, line by line.

Every reference mark that is not `correct` under reference-anchored
alignment is given exactly one cause:

- `line_reordered` — its whole line (>=80% deleted) appears verbatim
  elsewhere in the output: the model read it, in another order;
- `line_reordered_approx` (only with `approximate_reorder`) — not verbatim,
  but a stretch of the output matches the whole line at a CER below
  `READ_ELSEWHERE_CER`: read in another order, with reading errors or with
  its line break joined (added 2026-10-02, after lines read in another column
  order were found counted as missing);
- `line_missing` — its whole line is deleted and absent from the output;
- `span_missing` — deleted together with its base inside a line that is
  otherwise kept;
- `misread_with_base` — the mark is wrong or dropped while its base consonant is
  right (mark-specific error);
- `misread_other` — wrong together with its base consonant.

Single reads at about reference length only (anchored alignment is not valid
for comparing outputs of different lengths; `THAI_MARKS_T1_SCORING_V2.md` §8).
"""

from __future__ import annotations

import collections

from labbs2026.thai_marks.decompose import (
    _base_index,
    _fates_from,
    align_anchored,
    edit_distance_from,
)
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.orthography import LOWER_VOWELS, TONE_MARKS, UPPER_VOWELS

MARKS = frozenset(TONE_MARKS) | frozenset(UPPER_VOWELS) | frozenset(LOWER_VOWELS)
CAUSES = ("line_reordered", "line_missing", "span_missing", "misread_with_base", "misread_other")
WHOLE_LINE = 0.8
# A line counts as read elsewhere when some stretch of the output matches it
# at under 20% CER. Against other pages' outputs (the chance level), lines of
# 8+ characters match at a median 5th percentile of 0.63-0.74, so 0.2 is far
# from chance. Shorter lines (page numbers, axis ticks, "0") match anywhere
# by chance and are never credited as read elsewhere.
READ_ELSEWHERE_CER = 0.2
MIN_ELSEWHERE_CHARS = 8
CAUSES_APPROX = ("line_reordered", "line_reordered_approx", "line_missing", "span_missing",
                 "misread_with_base", "misread_other")


def reference_lines(raw_reference: str) -> list[str]:
    """Extracted, non-empty reference lines; joined by one space they are the scored text."""
    return [line for line in (extract_text(part) for part in raw_reference.split("\n")) if line]


def elsewhere_cer(line: str, hypothesis: str) -> float:
    """CER of the best-matching stretch of `hypothesis` for the whole of `line`."""
    pairs, _, _ = align_anchored(line, hypothesis)
    return edit_distance_from(pairs, line, hypothesis) / len(line)


def read_elsewhere(line: str, hypothesis: str) -> bool:
    return (len(line) >= MIN_ELSEWHERE_CHARS
            and elsewhere_cer(line, hypothesis) < READ_ELSEWHERE_CER)


def attribute_marks(raw_reference: str, raw_output: str, *,
                    approximate_reorder: bool = False) -> collections.Counter:
    """Counts of reference marks by outcome: `correct` or one cause.

    Default: causes in `CAUSES` (as reported 2026-10-01). With
    `approximate_reorder`, causes in `CAUSES_APPROX`: a whole-line deletion not
    found verbatim is `line_reordered_approx` if `read_elsewhere`.
    """
    lines = reference_lines(raw_reference)
    reference = " ".join(lines)
    hypothesis = extract_text(raw_output)
    pairs, _, _ = align_anchored(reference, hypothesis)
    fates, _ = _fates_from(pairs, reference, hypothesis)
    out: collections.Counter = collections.Counter()
    start = 0
    for line in lines:
        span = range(start, start + len(line))
        start += len(line) + 1
        deleted = sum(fates.get(j) == "deleted" for j in span) / len(line)
        whole = deleted >= WHOLE_LINE
        if whole and line in hypothesis:
            whole_cause = "line_reordered"
        elif whole and approximate_reorder and read_elsewhere(line, hypothesis):
            whole_cause = "line_reordered_approx"
        else:
            whole_cause = "line_missing"
        for j in span:
            if reference[j] not in MARKS:
                continue
            fate = fates.get(j, "deleted")
            if fate == "correct":
                out["correct"] += 1
            elif whole:
                out[whole_cause] += 1
            else:
                base = _base_index(reference, j)
                if base is not None and fates.get(base) == "correct":
                    out["misread_with_base"] += 1  # dropped or replaced, base read right
                elif fate == "deleted":
                    out["span_missing"] += 1
                else:
                    out["misread_other"] += 1
    return out
