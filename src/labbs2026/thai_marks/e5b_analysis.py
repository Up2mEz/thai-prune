"""E5b readings (`docs/stage0/E5B_MEANINGFUL_TEXT_DRAFT.md`): meaningful text against E5's random words.

Offline. Page records are the worker's e5 records (`kind` page). The E5 records come from the
registered E5 run; the layout grid (line counts, sizes, page index) is the same, only the text differs.
"""

from __future__ import annotations

import random

from labbs2026.thai_marks import e5_analysis as e5

SEED = e5.SEED
RESAMPLES = e5.RESAMPLES
MISREAD_MATERIAL = 0.01  # one point of the misread share (E5's shares are 1-5%), a judgement
OMITTED_FLOOR = 0.02


def _misread_rows(pages: list[dict]) -> list[dict]:
    rows = e5.omitted_share_by_page(pages)
    return [{"marks": r["found_marks"], "x": r["found_marks"] - r["found_correct"]} for r in rows]


def misread_contrast(new_pages: list[dict], old_pages: list[dict]) -> dict:
    """Misread share in found lines, `new_pages` minus `old_pages`, with a page bootstrap (unpaired)."""
    a, b = _misread_rows(new_pages), _misread_rows(old_pages)
    if not a or not b:
        return {"estimate": None, "ci95": None, "material": False, "pages": [len(a), len(b)]}

    def stat(ia, ib):
        return e5._share(a, "x", ia) - e5._share(b, "x", ib)

    est = stat(range(len(a)), range(len(b)))
    rng = random.Random(SEED)
    draws = sorted(stat([rng.randrange(len(a)) for _ in a], [rng.randrange(len(b)) for _ in b])
                   for _ in range(RESAMPLES))
    ci = [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]]
    material = bool((ci[0] > 0 or ci[1] < 0) and abs(est) >= MISREAD_MATERIAL)
    return {"estimate": est, "ci95": ci, "material": material, "pages": [len(a), len(b)],
            "new_share": e5._share(a, "x"), "old_share": e5._share(b, "x")}


def misread_reading(contrast: dict) -> str:
    if not contrast["material"]:
        return "no_difference_shown"
    return "meaningful_text_more_misreads" if contrast["estimate"] > 0 else "meaningful_text_fewer_misreads"


def by_size(new_pages: list[dict], old_pages: list[dict]) -> dict:
    out = {}
    for px in sorted({r["font_px"] for r in new_pages}):
        out[f"S{px}"] = misread_contrast([r for r in new_pages if r["font_px"] == px],
                                         [r for r in old_pages if r["font_px"] == px])
    return out


def analyze(new_pages: list[dict], old_pages: list[dict]) -> dict:
    rows = e5.omitted_share_by_page(new_pages)
    reference = sum(r["marks"] for r in rows)
    omitted = sum(r["absent"] for r in rows) / reference if reference else 0.0
    overall = misread_contrast(new_pages, old_pages)
    out = {"omitted_share_overall": omitted, "cells": e5.cell_summary(new_pages),
           "D1_density_18_minus_4": e5.pooled_contrast(new_pages, {"lines": 18}, {"lines": 4}),
           "D2_size_24_minus_44": e5.pooled_contrast(new_pages, {"font_px": 24}, {"font_px": 44}),
           "D3_misread_meaningful_minus_words": overall,
           "D3_reading": misread_reading(overall), "D3_by_size": by_size(new_pages, old_pages),
           "pages": [len(new_pages), len(old_pages)]}
    out["reading_omission"] = ("clean_meaningful_text_almost_never_omitted" if omitted < OMITTED_FLOOR
                               else "omission_present_see_D1_D2")
    return out
