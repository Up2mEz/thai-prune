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
import re
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


def _line_end(hypothesis: str, line: str, aligned_end: int, tail: int = 8,
              reach: int = 40) -> int | None:
    """Where the output's copy of `line` ends, near the aligner's estimate.

    At a junction with a missing line the aligner can lend the end of the
    previous line to the missing one, so its estimate may fall short. The
    line's last `tail` characters are searched within `reach` of the
    estimate; the closest occurrence wins. None if the tail is not there,
    i.e. the previous line was not read cleanly enough to place a boundary.
    """
    tail_text = line[-tail:]
    lo = max(0, aligned_end - reach)
    best = None
    start = hypothesis.find(tail_text, lo)
    while start != -1 and start <= aligned_end + reach:
        end = start + len(tail_text)
        if best is None or abs(end - aligned_end) < abs(best - aligned_end):
            best = end
        start = hypothesis.find(tail_text, start + 1)
    return best


def raw_position(raw: str, extracted_prefix: str, tail: int = 24) -> int | None:
    """Index in the raw output where `extracted_prefix` ends, or None.

    The model decided on its raw text (newlines, markup), not on extracted
    text, so T3 must teacher-force the raw prefix. The last `tail`
    non-space characters of the extracted prefix are matched in the raw output
    allowing any whitespace between them; the occurrence used is the one with
    the same rank as in the extracted text. None if it cannot be placed
    (markup inside the tail), in which case the case is unscorable.
    """
    chars = [c for c in extracted_prefix if not c.isspace()][-tail:]
    if not chars:
        return None
    pattern = r"\s*".join(re.escape(c) for c in chars)
    flat = "".join(c for c in extracted_prefix if not c.isspace())
    rank = flat.count("".join(chars))
    matches = list(re.finditer(pattern, raw))
    if len(matches) < rank or rank == 0:
        return None
    return matches[rank - 1].end()


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
        cut = _line_end(hypothesis, prev["line"], prev["hyp_end"])
        if cut is None:
            continue
        prefix = hypothesis[:cut]
        actual = hypothesis[cut:].lstrip()[:chars]
        if len(actual) < chars:
            continue
        raw = record["raw_output"]
        at = raw_position(raw, prefix)
        separator = re.match(r"\s*", raw[at:]).group(0) if at is not None else ""
        case = {"id": record["id"], "line": k, "prefix": prefix, "actual": actual,
                "marked": any(c in MARKS for c in cur["line"]),
                # What T3 feeds: the raw prefix, then each continuation after the
                # whitespace the model itself emitted there (usually a newline).
                "raw_prefix": raw[:at] + separator if at is not None else None,
                "raw_actual": raw[at + len(separator):][:chars] if at is not None else None}
        if cur["missing"]:
            out.append({**case, "kind": "skip", "expected": cur["line"][:chars]})
        elif k + 1 < len(status) and actual.startswith(cur["line"][:4]):
            controls.append({**case, "kind": "control",
                             "expected": status[k + 1]["line"][:chars]})
    # Identical continuations would give a margin of exactly 0 by construction.
    out = [c for c in out if c["expected"] != c["actual"]]
    controls = [c for c in controls if c["expected"] != c["actual"]]
    rng = random.Random(f"{seed}:{record['id']}")
    out += rng.sample(controls, min(controls_per_page, len(controls)))
    return out
