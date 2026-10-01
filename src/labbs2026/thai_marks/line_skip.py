"""T3 population: line boundaries in Typhoon's own output (draft, not authorized).

`docs/stage0/T3_LINE_SKIP_DIAGNOSTIC_DRAFT.md`. A *skip* boundary is where the
output, having just read reference line `k-1`, does not continue with line
`k` (which is absent from the whole output). A *control* boundary is where it
reads line `k-1` and then line `k`. At each, two continuations of equal
character length are scored from the model's own prefix: what it wrote next
(`actual`) and the reference line it should have started (`expected`); at a
control boundary `expected` is line `k+1`, the skip it did not make.

Offline and CPU-only: this module only builds the cases.
"""

from __future__ import annotations

import random
from typing import Any

from labbs2026.thai_marks.attribution import MARKS, WHOLE_LINE, reference_lines
from labbs2026.thai_marks.decompose import _fates_from, align_anchored
from labbs2026.thai_marks.extract import extract_text

CONTINUATION_CHARS = 12


def _line_status(reference: str, hypothesis: str, lines: list[str]):
    pairs, _, _ = align_anchored(reference, hypothesis)
    fates, _ = _fates_from(pairs, reference, hypothesis)
    hyp_of = {r: h for r, h in pairs if r is not None and h is not None}
    status, start = [], 0
    for line in lines:
        span = range(start, start + len(line))
        start += len(line) + 1
        deleted = sum(fates.get(j) == "deleted" for j in span) / len(line)
        missing = deleted >= WHOLE_LINE and line not in hypothesis
        ends = [hyp_of[j] for j in span if j in hyp_of]
        status.append({"line": line, "missing": missing,
                       "hyp_end": max(ends) + 1 if ends else None})
    return status


def boundaries(record: dict, *, controls_per_page: int = 2, seed: int = 20261001,
               chars: int = CONTINUATION_CHARS) -> list[dict[str, Any]]:
    """Skip and control boundaries of one T1 record, on extracted text.

    `prefix` is the extracted output up to the boundary; `actual` and
    `expected` are the next `chars` characters each would continue with.
    """
    lines = reference_lines(record["reference"])
    reference = " ".join(lines)
    hypothesis = extract_text(record["raw_output"])
    status = _line_status(reference, hypothesis, lines)
    out: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    for k in range(1, len(status)):
        prev, cur = status[k - 1], status[k]
        if prev["missing"] or prev["hyp_end"] is None:
            continue
        cut = prev["hyp_end"]
        # A line ends at whitespace; the aligner can hand its last character to
        # the missing next line, so snap to the next space within a few chars.
        space = hypothesis.find(" ", cut)
        if space != -1 and space - cut <= 4:
            cut = space
        prefix = hypothesis[:cut]
        actual = hypothesis[cut:].lstrip()[:chars]
        if len(actual) < chars:
            continue
        case = {"id": record["id"], "line": k, "prefix": prefix, "actual": actual,
                "marked": any(c in MARKS for c in cur["line"])}
        if cur["missing"]:
            out.append({**case, "kind": "skip", "expected": cur["line"][:chars]})
        elif k + 1 < len(status) and actual.startswith(cur["line"][:4]):
            controls.append({**case, "kind": "control",
                             "expected": status[k + 1]["line"][:chars]})
    rng = random.Random(f"{seed}:{record['id']}")
    out += rng.sample(controls, min(controls_per_page, len(controls)))
    return out
