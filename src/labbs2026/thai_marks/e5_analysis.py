"""E5 readings (`docs/stage0/E5_SYNTHETIC_OMISSION_DRAFT.md`): omission against line count and size.

Offline. Records are the worker's e5 records (`kind` page, line_tight, line_masked). Lines are
scored with `p_zoom_analysis.score_page`, the same locator P-ZOOM used (`READ_ELSEWHERE_CER` 0.2).
"""

from __future__ import annotations

import random
from collections import defaultdict

from labbs2026.thai_marks.attribution import reference_lines
from labbs2026.thai_marks.p_zoom_analysis import score_page

SEED = 20261012
RESAMPLES = 2000
MATERIAL = 0.05  # judgement, registered
MIN_OMITTED = 10  # fewer omitted sampled lines than this: no reading of mechanism


def page_lines(record: dict) -> list[dict]:
    """Per reference line of a page read: marks, found (as text), marks read correctly."""
    n = len(reference_lines(record["reference"]))
    scored = score_page(record["reference"], [record["raw_output"]], [], list(range(n)))
    return [{"line": r["line"], "marks": r["marks"], "found": r["outcome"] == "text",
             "marks_correct": r["marks_correct"]} for r in scored["lines"]]


def line_read(record: dict) -> dict:
    scored = score_page(record["reference"], [record["raw_output"]], [], [0])["lines"][0]
    return {"marks": scored["marks"], "found": scored["outcome"] == "text",
            "marks_correct": scored["marks_correct"]}


def _share(rows: list[dict], key: str, idx=None) -> float:
    chosen = rows if idx is None else [rows[i] for i in idx]
    total = sum(r["marks"] for r in chosen)
    return sum(r[key] for r in chosen) / total if total else 0.0


def _boot(stat, n: int) -> list[float]:
    rng = random.Random(SEED)
    draws = sorted(stat([rng.randrange(n) for _ in range(n)]) for _ in range(RESAMPLES))
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]]


def omitted_share_by_page(pages: list[dict]) -> list[dict]:
    """Per page: reference marks, marks in lines not found, marks read correctly in found lines."""
    out = []
    for page in pages:
        lines = page_lines(page)
        out.append({"marks": sum(r["marks"] for r in lines),
                    "absent": sum(r["marks"] for r in lines if not r["found"]),
                    "found_marks": sum(r["marks"] for r in lines if r["found"]),
                    "found_correct": sum(r["marks_correct"] for r in lines if r["found"])})
    return out


def cell_summary(page_records: list[dict]) -> dict:
    """Omission and misread shares per (lines, font_px) cell, with a page bootstrap."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in page_records:
        cells[(r["lines"], r["font_px"])].append(r)
    out = {}
    for key, recs in sorted(cells.items()):
        rows = omitted_share_by_page(recs)
        omitted = [{"marks": r["marks"], "x": r["absent"]} for r in rows]
        misread = [{"marks": r["found_marks"], "x": r["found_marks"] - r["found_correct"]} for r in rows]
        out[f"L{key[0]}-S{key[1]}"] = {
            "pages": len(rows),
            "omitted_share": _share(omitted, "x"),
            "omitted_ci95": _boot(lambda idx, o=omitted: _share(o, "x", idx), len(rows)),
            "misread_share_in_found_lines": _share(misread, "x"),
            "misread_ci95": _boot(lambda idx, m=misread: _share(m, "x", idx), len(rows))}
    return out


def pooled_contrast(page_records: list[dict], hi: dict, lo: dict) -> dict:
    """Omission share of the pages matching `hi` minus that of the pages matching `lo` (e.g. {'lines': 18})."""
    def rows_for(spec):
        sel = [r for r in page_records if all(r[k] == v for k, v in spec.items())]
        return omitted_share_by_page(sel)

    a, b = rows_for(hi), rows_for(lo)
    if not a or not b:
        return {"estimate": None, "ci95": None, "material": False, "pages": [len(a), len(b)]}

    def stat(ia, ib):
        ra = [{"marks": a[i]["marks"], "x": a[i]["absent"]} for i in ia]
        rb = [{"marks": b[i]["marks"], "x": b[i]["absent"]} for i in ib]
        return _share(ra, "x") - _share(rb, "x")

    est = stat(range(len(a)), range(len(b)))
    rng = random.Random(SEED)
    draws = sorted(stat([rng.randrange(len(a)) for _ in a], [rng.randrange(len(b)) for _ in b])
                   for _ in range(RESAMPLES))
    ci = [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]]
    return {"estimate": est, "ci95": ci, "material": bool(ci[0] > 0 and est >= MATERIAL),
            "pages": [len(a), len(b)]}


def line_arms(records: list[dict]) -> dict:
    """Sampled lines read in the page, tight, and masked: how many omitted in the page are found alone."""
    by_page = {r["page"]: r for r in records if r["kind"] == "page"}
    arms: dict[tuple, dict] = defaultdict(dict)
    for r in records:
        if r["kind"] in ("line_tight", "line_masked"):
            arms[(r["page"], r["line_index"])][r["kind"]] = line_read(r)
    rows = []
    for (page, idx), got in sorted(arms.items()):
        if page not in by_page or {"line_tight", "line_masked"} - got.keys():
            continue
        in_page = page_lines(by_page[page])[idx]
        rows.append({"page": page, "line": idx, "page_found": in_page["found"],
                     "masked_found": got["line_masked"]["found"],
                     "tight_found": got["line_tight"]["found"]})
    omitted = [r for r in rows if not r["page_found"]]
    return {"sampled_lines": len(rows), "omitted_in_page": len(omitted),
            "omitted_found_masked": sum(r["masked_found"] for r in omitted),
            "omitted_found_tight": sum(r["tight_found"] for r in omitted),
            "found_in_page_but_not_masked": sum(r["page_found"] and not r["masked_found"] for r in rows),
            "rows": rows}


def reading(arms: dict) -> str:
    """The registered label (section 4 of the draft)."""
    n = arms["omitted_in_page"]
    if n < MIN_OMITTED:
        return "too_few_omissions"
    masked, tight = arms["omitted_found_masked"] / n, arms["omitted_found_tight"] / n
    if masked >= 0.5:
        return "competing_content"
    if tight >= 0.5:
        return "image_size_or_zoom"
    return "not_readable_alone"
