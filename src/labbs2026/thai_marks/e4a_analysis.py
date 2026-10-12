"""E4a readings (`docs/stage0/E4A_MASKED_BAND_DRAFT.md`): masked bands against whole page and bands.

Offline. Inputs are per-view page scores from `p_zoom2_analysis.score_view`. The reference is
`repeat` (the whole page read in the same session).
"""

from __future__ import annotations

import random

from labbs2026.thai_marks import p_zoom2_analysis as pz2

SEED = 20261012
RESAMPLES = 2000
MATERIAL = 0.05  # judgement, registered
CONTROL_FLOOR = pz2.CONTROL_FLOOR


def _boot(stat, pages: int) -> list[float]:
    rng = random.Random(SEED)
    draws = sorted(stat([rng.randrange(pages) for _ in range(pages)]) for _ in range(RESAMPLES))
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]]


def contrast(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Text share of `a` minus `b` over omitted marks, with a paired page bootstrap."""
    pages = len(rows_a)
    est = pz2._share(rows_a, "text") - pz2._share(rows_b, "text")
    ci = _boot(lambda idx: pz2._share(rows_a, "text", idx) - pz2._share(rows_b, "text", idx), pages)
    return {"estimate": est, "ci95": ci, "material": bool(ci[0] > 0 and est >= MATERIAL)}


def reading(c1: dict, c2: dict, c3: dict, masked_control: float) -> str:
    """The registered label (section 4 of the draft)."""
    if masked_control < CONTROL_FLOOR:
        return "masked_damages_ordinary_reading"
    if c1["material"] and c3["material"]:
        return "both_contribute"
    if c1["material"]:
        return "competing_content"
    if c2["material"] and c3["material"]:
        return "image_size_or_token_count"
    if not c1["material"] and not c2["material"]:
        return "crop_effect_not_reproduced"
    return "not_distinguishable"


def analyze(scores: dict[str, list[dict]]) -> dict:
    rows = {name: pz2.page_text_rows(s) for name, s in scores.items()}
    c1 = contrast(rows["masked_bands"], rows["repeat"])
    c2 = contrast(rows["bands100"], rows["repeat"])
    c3 = contrast(rows["bands100"], rows["masked_bands"])
    control = {name: pz2.control_text_share(s) for name, s in scores.items()}
    return {"text_share": {n: pz2._share(r, "text") for n, r in rows.items()},
            "control_text_share": control,
            "C1_masked_minus_repeat": c1, "C2_bands100_minus_repeat": c2,
            "C3_bands100_minus_masked": c3,
            "reading": reading(c1, c2, c3, control["masked_bands"]),
            "pages": len(rows["repeat"])}
