"""E4b readings (`docs/stage0/E4B_EQUAL_READS_DRAFT.md`): the same number of different reads, whole page or masked bands.

Offline. Inputs are per-view page scores from `p_zoom2_analysis.score_view`; `masked_bands` scores
the union of its three tile outputs, as E4a did.
"""

from __future__ import annotations

import itertools

from labbs2026.thai_marks import e4a_analysis as e4
from labbs2026.thai_marks import p_zoom2_analysis as pz2

W3 = ("repeat", "pad", "scale90")
W5 = ("repeat", "pad", "scale90", "pad12", "scale75")
MASKED = "masked_bands"
MATERIAL = e4.MATERIAL
CONTROL_FLOOR = pz2.CONTROL_FLOOR


def union_rows(score_lists: list[list[dict]]) -> list[dict]:
    """Per page: absent marks, and those whose line is `text` in at least one of the reads."""
    rows = []
    for pages in zip(*score_lists):
        absent = text = 0
        for lines in zip(*(p["lines"] for p in pages)):
            if lines[0]["group"] != "absent":
                continue
            absent += lines[0]["marks"]
            text += lines[0]["marks"] * any(line["outcome"] == "text" for line in lines)
        rows.append({"absent": absent, "text": text})
    return rows


def k_read_curve(scores: dict[str, list[dict]], views: tuple[str, ...]) -> dict[int, float]:
    """Mean over all subsets of k of `views` of the union text share (k = 1 .. len(views))."""
    curve = {}
    for k in range(1, len(views) + 1):
        shares = [pz2._share(union_rows([scores[v] for v in subset]), "text")
                  for subset in itertools.combinations(views, k)]
        curve[k] = sum(shares) / len(shares)
    return curve


def reading(d1: dict, qualified: bool) -> str:
    """The registered label for D1 = M3 - W3 (section 4 of the draft)."""
    if d1["material"]:
        label = "masking_adds_beyond_read_count"
    elif d1["ci95"][1] < 0 and d1["estimate"] <= -MATERIAL:
        label = "whole_page_reads_recover_more"
    else:
        label = "read_count_accounts_for_gain"
    return label + ("_qualified" if qualified else "")


def analyze(scores: dict[str, list[dict]]) -> dict:
    controls = {name: pz2.control_text_share(s) for name, s in scores.items()}
    w3 = union_rows([scores[v] for v in W3])
    w5 = union_rows([scores[v] for v in W5])
    m3 = pz2.page_text_rows(scores[MASKED])
    d1 = e4.contrast(m3, w3)
    d2 = e4.contrast(m3, w5)
    qualified = any(controls[v] < CONTROL_FLOOR for v in (*W3, MASKED))
    single = {v: pz2._share(pz2.page_text_rows(scores[v]), "text") for v in (*W5, MASKED)}
    return {"text_share_single": single, "control_text_share": controls,
            "W3_union": pz2._share(w3, "text"), "W5_union": pz2._share(w5, "text"),
            "M3_union": pz2._share(m3, "text"),
            "D1_M3_minus_W3": d1, "D2_M3_minus_W5": d2,
            "whole_page_k_read_curve": k_read_curve(scores, W5),
            "reading": reading(d1, qualified),
            "extra_whole_views_below_control_floor": [v for v in W5 if controls[v] < CONTROL_FLOOR],
            "pages": len(m3)}
