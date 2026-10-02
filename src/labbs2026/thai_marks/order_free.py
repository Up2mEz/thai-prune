"""Mark precision/recall that does not charge reading order (diagnostic draft).

`docs/stage0/ORDER_FREE_MARK_METRIC_DRAFT.md`. Not a primary metric. Each
reference line is located in the output on its own (longest first, claimed
output masked), so a line read in another column order is credited; mark
precision counts every mark character in the output, so surplus text is
charged. `mode="global"` gives the same numbers from one global alignment.
"""

from __future__ import annotations

from typing import Any

from labbs2026.thai_marks.attribution import MARKS, MIN_ELSEWHERE_CHARS, reference_lines
from labbs2026.thai_marks.decompose import _fates_from, align, align_anchored, edit_distance_from
from labbs2026.thai_marks.extract import extract_text

LINE_MATCH_CER = 0.4
# Never equal to any reference character, so a claimed output position can
# only ever be a substitution, not a correct match, for a later line.
MASK = "￿"


def _marks(text: str) -> int:
    return sum(c in MARKS for c in text)


def _correct_marks(pairs, reference: str, hypothesis: str) -> int:
    fates, _ = _fates_from(pairs, reference, hypothesis)
    return sum(1 for j, c in enumerate(reference) if c in MARKS and fates.get(j) == "correct")


def _prf(correct: int, reference_marks: int, output_marks: int) -> dict[str, float | None]:
    recall = correct / reference_marks if reference_marks else None
    precision = correct / output_marks if output_marks else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else (0.0 if precision is not None and recall is not None
                                        else None))
    return {"recall": recall, "precision": precision, "f1": f1}


def mark_counts(raw_reference: str, raw_output: str, *, mode: str = "line_matched",
                max_cer: float = LINE_MATCH_CER, residual: bool = False) -> dict[str, Any]:
    """Counts behind mark precision/recall for one observation (sum these, then `prf`).

    `residual=False` is v1 (draft §2; failed its base check, §5). `residual=True`
    is v2 (§6): unmatched lines, in reference order, are globally aligned
    against the output with every claimed character removed.
    """
    lines = reference_lines(raw_reference)
    hypothesis = extract_text(raw_output)
    reference_marks = sum(_marks(line) for line in lines)
    out = {"reference_marks": reference_marks, "output_marks": _marks(hypothesis),
           "short_line_marks": sum(_marks(line) for line in lines
                                   if len(line) < MIN_ELSEWHERE_CHARS)}
    if mode == "global":
        reference = " ".join(lines)
        out["correct"] = _correct_marks(align(reference, hypothesis), reference, hypothesis)
        return out
    if mode != "line_matched":
        raise ValueError(mode)
    masked = list(hypothesis)
    matched: set[int] = set()
    correct = matched_lines = matched_marks = 0
    eligible = sorted((i for i, line in enumerate(lines) if len(line) >= MIN_ELSEWHERE_CHARS),
                      key=lambda i: (-len(lines[i]), i))
    for i in eligible:
        line, current = lines[i], "".join(masked)
        pairs, _, _ = align_anchored(line, current)
        if edit_distance_from(pairs, line, current) / len(line) >= max_cer:
            continue
        hyp = [h for _, h in pairs if h is not None]
        if not hyp:
            continue
        correct += _correct_marks(pairs, line, current)
        matched.add(i)
        matched_lines += 1
        matched_marks += _marks(line)
        for h in range(min(hyp), max(hyp) + 1):
            masked[h] = MASK
    if residual:
        rest_reference = " ".join(line for i, line in enumerate(lines) if i not in matched)
        rest_output = "".join(c for c in masked if c != MASK)
        if rest_reference:
            correct += _correct_marks(align(rest_reference, rest_output),
                                      rest_reference, rest_output)
    out.update(correct=correct, lines=len(lines), eligible_lines=len(eligible),
               matched_lines=matched_lines, matched_reference_marks=matched_marks)
    return out


def prf(counts: list[dict[str, Any]]) -> dict[str, Any]:
    """Micro-averaged precision/recall/F1 over observations' `mark_counts`."""
    total = {k: sum(c.get(k, 0) for c in counts)
             for k in ("correct", "reference_marks", "output_marks", "short_line_marks",
                       "lines", "eligible_lines", "matched_lines", "matched_reference_marks")}
    out = {**_prf(total["correct"], total["reference_marks"], total["output_marks"]),
           "n": len(counts), **total}
    if total["reference_marks"]:
        out["short_line_mark_share"] = total["short_line_marks"] / total["reference_marks"]
    return out
