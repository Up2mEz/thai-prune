"""Which pages and lines the P-ZOOM probe reads (`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §2-§3).

Selection is offline and deterministic: it reads Typhoon's existing T1
records, so it needs no model and no image. Lines are stored as indices into
`attribution.reference_lines(reference)`, never as text, so the committed page
list holds no benchmark reference text.
"""

from __future__ import annotations

import hashlib

from labbs2026.thai_marks.attribution import MARKS, MIN_ELSEWHERE_CHARS, reference_lines, whole_line_causes

TASK = "Full-page OCR"
PROMPT_KIND = "BENCHMARK_QUESTION"
CONTROL_PER_PAGE = 2
CONTROL_SEED = 20261003


def has_mark(line: str) -> bool:
    return any(ch in MARKS for ch in line)


def mark_count(line: str) -> int:
    return sum(ch in MARKS for ch in line)


def _rank(page_id: str, index: int, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{page_id}:{index}".encode("utf-8")).hexdigest()


def select_pages(records: list[dict], *, task: str = TASK, prompt_kind: str = PROMPT_KIND,
                 control_per_page: int = CONTROL_PER_PAGE, seed: int = CONTROL_SEED) -> list[dict]:
    """Pages where Typhoon left a Thai-mark line absent, and their control lines.

    A page is selected when `attribution.whole_line_causes` gives some
    reference line that carries a mark the cause `line_missing`. Control lines
    are lines the same output kept (cause `None`) that are long enough for
    `find_elsewhere` (`MIN_ELSEWHERE_CHARS`) and carry a mark; `control_per_page`
    of them per page, chosen by `sha256(seed:id:index)` so the choice does not
    depend on record order. A page with fewer eligible lines gets fewer.
    """
    pages = []
    for record in sorted((r for r in records if r["task"] == task and r["prompt_kind"] == prompt_kind),
                         key=lambda r: r["id"]):
        lines = reference_lines(record["reference"])
        causes = whole_line_causes(record["reference"], record["raw_output"])
        absent = [i for i, (line, cause) in enumerate(zip(lines, causes))
                  if cause == "line_missing" and has_mark(line)]
        if not absent:
            continue
        eligible = [i for i, (line, cause) in enumerate(zip(lines, causes))
                    if cause is None and len(line) >= MIN_ELSEWHERE_CHARS and has_mark(line)]
        control = sorted(sorted(eligible, key=lambda i: _rank(record["id"], i, seed))[:control_per_page])
        pages.append({
            "id": record["id"],
            "absent_lines": absent,
            "absent_marks": sum(mark_count(lines[i]) for i in absent),
            "control_lines": control,
        })
    return pages
