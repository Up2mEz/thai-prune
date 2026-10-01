"""Where each wrongly transcribed reference mark comes from, line by line.

Every reference mark that is not `correct` under reference-anchored
alignment is given exactly one cause:

- `line_reordered` — its whole line (>=80% deleted) appears verbatim
  elsewhere in the output: the model read it, in another order;
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

from labbs2026.thai_marks.decompose import _base_index, _fates_from, align_anchored
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.orthography import LOWER_VOWELS, TONE_MARKS, UPPER_VOWELS

MARKS = frozenset(TONE_MARKS) | frozenset(UPPER_VOWELS) | frozenset(LOWER_VOWELS)
CAUSES = ("line_reordered", "line_missing", "span_missing", "misread_with_base", "misread_other")
WHOLE_LINE = 0.8


def reference_lines(raw_reference: str) -> list[str]:
    """Extracted, non-empty reference lines; joined by one space they are the scored text."""
    return [line for line in (extract_text(part) for part in raw_reference.split("\n")) if line]


def attribute_marks(raw_reference: str, raw_output: str) -> collections.Counter:
    """Counts of reference marks by outcome: `correct` or one cause in `CAUSES`."""
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
        for j in span:
            if reference[j] not in MARKS:
                continue
            fate = fates.get(j, "deleted")
            if fate == "correct":
                out["correct"] += 1
            elif whole:
                out["line_reordered" if line in hypothesis else "line_missing"] += 1
            else:
                base = _base_index(reference, j)
                if base is not None and fates.get(base) == "correct":
                    out["misread_with_base"] += 1  # dropped or replaced, base read right
                elif fate == "deleted":
                    out["span_missing"] += 1
                else:
                    out["misread_other"] += 1
    return out
