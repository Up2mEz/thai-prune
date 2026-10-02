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
# The matched stretch must be mostly output text the page alignment has not
# already credited to other reference text; otherwise a line repeated in the
# reference, or two near-identical captions, would be credited twice from one
# read. On the 2026-10-02 calibration outputs the used share of matched
# stretches is <= 0.23 or >= 0.93, so any cut between gives the same result.
MAX_USED_SHARE = 0.5
CAUSES_APPROX = ("line_reordered", "line_reordered_approx", "line_missing", "span_missing",
                 "misread_with_base", "misread_other")


def reference_lines(raw_reference: str) -> list[str]:
    """Extracted, non-empty reference lines; joined by one space they are the scored text."""
    return [line for line in (extract_text(part) for part in raw_reference.split("\n")) if line]


def _best_stretch(line: str, hypothesis: str) -> tuple[float, range]:
    pairs, _, _ = align_anchored(line, hypothesis)
    hyp = [h for _, h in pairs if h is not None]
    stretch = range(min(hyp), max(hyp) + 1) if hyp else range(0)
    return edit_distance_from(pairs, line, hypothesis) / len(line), stretch


def _free(stretch: range, used) -> bool:
    return bool(stretch) and sum(h in used for h in stretch) / len(stretch) <= MAX_USED_SHARE


def elsewhere_cer(line: str, hypothesis: str) -> float:
    """CER of the best-matching stretch of `hypothesis` for the whole of `line`."""
    return _best_stretch(line, hypothesis)[0]


def find_elsewhere(line: str, hypothesis: str, used=frozenset()) -> tuple[str | None, range]:
    """Where `line` was read in output text `used` does not already claim.

    Returns ("verbatim" | "approx" | None, the output stretch). `used`: output
    indices the page alignment pairs with reference text, plus stretches
    already credited to other lines. Lines under `MIN_ELSEWHERE_CHARS` match
    anywhere by chance and are never found.
    """
    if len(line) < MIN_ELSEWHERE_CHARS:
        return None, range(0)
    at = hypothesis.find(line)
    while at != -1:
        if _free(range(at, at + len(line)), used):
            return "verbatim", range(at, at + len(line))
        at = hypothesis.find(line, at + 1)
    cer, stretch = _best_stretch(line, hypothesis)
    if cer < READ_ELSEWHERE_CER and _free(stretch, used):
        return "approx", stretch
    return None, range(0)


def read_elsewhere(line: str, hypothesis: str, used=frozenset()) -> bool:
    return find_elsewhere(line, hypothesis, used)[0] is not None


def attribute_marks(raw_reference: str, raw_output: str, *,
                    approximate_reorder: bool = False) -> collections.Counter:
    """Counts of reference marks by outcome: `correct` or one cause.

    Default: causes in `CAUSES` (as reported 2026-10-01). With
    `approximate_reorder`, causes in `CAUSES_APPROX`, and a whole-line deletion
    is credited as read elsewhere (verbatim: `line_reordered`; approximately:
    `line_reordered_approx`) only in output text the page alignment has not
    credited to other reference text (`MAX_USED_SHARE`).
    """
    lines = reference_lines(raw_reference)
    reference = " ".join(lines)
    hypothesis = extract_text(raw_output)
    pairs, _, _ = align_anchored(reference, hypothesis)
    fates, _ = _fates_from(pairs, reference, hypothesis)
    used = {h for r, h in pairs if r is not None and h is not None}
    out: collections.Counter = collections.Counter()
    start = 0
    for line in lines:
        span = range(start, start + len(line))
        start += len(line) + 1
        deleted = sum(fates.get(j) == "deleted" for j in span) / len(line)
        whole = deleted >= WHOLE_LINE
        if whole and approximate_reorder:
            found, stretch = find_elsewhere(line, hypothesis, used)
            used.update(stretch)  # one stretch of output is credited to one line only
            whole_cause = {"verbatim": "line_reordered", "approx": "line_reordered_approx",
                           None: "line_missing"}[found]
        elif whole and line in hypothesis:  # 2026-10-01 rule, kept as the default
            whole_cause = "line_reordered"
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
