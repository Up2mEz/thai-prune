"""Offline scoring of P-ZOOM-2 (`docs/stage0/P_ZOOM2_VIEWS_PROBE_DRAFT.md` §4-§5).

Scores each view of each page with `p_zoom_analysis.score_page`, compares it with the
zoom-free whole-page read (T1 `TYPHOON_CARD`), and applies the reading fixed before the run:

- `N`, the *perturbation gain*: mean over the whole-page perturbation views (`pad`,
  `scale90`) of the share of absent marks they recover as text and the baseline read did
  not. It is what changing the input a little, without zooming, already buys.
- `Z`, the *zoom gain*: the same for `bands`.
- `instrument_fails_control`: bands find under `CONTROL_FLOOR` of the control marks, so the
  zoom view loses ordinary lines and says nothing about zoom;
- `zoom_adds_beyond_perturbation`: `Z >= GAIN` and `Z - N >= GAIN`;
- `perturbation_explains_gain`: otherwise, `N >= GAIN` (the gain is read-to-read variability);
- `no_gain_from_views`: otherwise.
"""

from __future__ import annotations

import collections
import random

from labbs2026.thai_marks.p_zoom_analysis import score_page

GAIN = 0.10
CONTROL_FLOOR = 0.80
PERTURBATION_VIEWS = ("pad", "scale90")
ZOOM_VIEW = "bands"
BOOTSTRAP_SEED = 20261004
BOOTSTRAP_RESAMPLES = 2000


def assemble_views(records: list[dict], pages: list[dict], views: list[dict]) -> dict[str, list[dict]]:
    """`{view name: pages}` with tile outputs in tile order; raises on any missing read.

    Each page dict is as `p_zoom_analysis.assemble_pages` gives (`reference`, `tile_outputs`,
    `absent`, `control`). A view's tile count is `rows * cols` for `grid`, else 1.
    """
    by_key: dict[tuple, dict] = {}
    for r in records:
        key = (r["id"], r["view"], r["tile"])
        if key in by_key:
            raise ValueError(f"duplicate record {key}")
        by_key[key] = r
    names = {v["name"] for v in views}
    frozen = {p["id"] for p in pages}
    extra = {(i, v) for i, v, _ in by_key if i not in frozen or v not in names}
    if extra:
        raise ValueError(f"records outside the registered pages/views: {sorted(extra)[:5]}")
    out: dict[str, list[dict]] = {}
    for view in views:
        tiles = int(view["rows"]) * int(view["cols"]) if view["kind"] == "grid" else 1
        assembled = []
        for page in pages:
            got = [by_key.get((page["id"], view["name"], t)) for t in range(tiles)]
            if any(g is None for g in got):
                raise ValueError(f"page {page['id']} view {view['name']}: missing tiles")
            assembled.append({"id": page["id"], "reference": got[0]["reference"],
                              "tile_outputs": [g["raw_output"] for g in got],
                              "absent": page["absent_lines"], "control": page["control_lines"]})
        out[view["name"]] = assembled
    return out


def score_view(assembled: list[dict]) -> list[dict]:
    return [score_page(p["reference"], p["tile_outputs"], p["absent"], p["control"]) for p in assembled]


def page_gains(view_scores: list[dict], baseline_scores: list[dict]) -> list[dict]:
    """Per page: absent marks, marks the view recovers as text that the baseline does not, and the reverse."""
    if len(view_scores) != len(baseline_scores):
        raise ValueError("view and baseline cover different pages")
    rows = []
    for view, base in zip(view_scores, baseline_scores):
        if len(view["lines"]) != len(base["lines"]):
            raise ValueError("view and baseline score different lines")
        row = collections.Counter()
        for v, b in zip(view["lines"], base["lines"]):
            if (v["line"], v["group"]) != (b["line"], b["group"]):
                raise ValueError("view and baseline score different lines")
            if v["group"] != "absent":
                continue
            row["absent"] += v["marks"]
            row["text"] += v["marks"] * (v["outcome"] == "text")
            row["gain"] += v["marks"] * (v["outcome"] == "text" and b["outcome"] != "text")
            row["loss"] += v["marks"] * (v["outcome"] != "text" and b["outcome"] == "text")
        rows.append({k: row[k] for k in ("absent", "text", "gain", "loss")})
    return rows


def _share(rows: list[dict], key: str, indices=None) -> float:
    chosen = rows if indices is None else [rows[i] for i in indices]
    total = sum(r["absent"] for r in chosen)
    return sum(r[key] for r in chosen) / total if total else 0.0


def union_share(score_lists: list[list[dict]]) -> float:
    """Share of absent marks recovered as text by at least one of the given reads of each page."""
    total = found = 0
    for pages in zip(*score_lists):
        for lines in zip(*(p["lines"] for p in pages)):
            if lines[0]["group"] != "absent":
                continue
            total += lines[0]["marks"]
            found += lines[0]["marks"] * any(line["outcome"] == "text" for line in lines)
    return found / total if total else 0.0


def control_text_share(view_scores: list[dict]) -> float:
    rows = [r for p in view_scores for r in p["lines"] if r["group"] == "control"]
    total = sum(r["marks"] for r in rows)
    return sum(r["marks"] for r in rows if r["outcome"] == "text") / total if total else 0.0


def reading(zoom_gain: float, perturbation_gain: float, bands_control: float) -> str:
    if bands_control < CONTROL_FLOOR:
        return "instrument_fails_control"
    if zoom_gain >= GAIN and zoom_gain - perturbation_gain >= GAIN:
        return "zoom_adds_beyond_perturbation"
    if perturbation_gain >= GAIN:
        return "perturbation_explains_gain"
    return "no_gain_from_views"


def analyze(baseline_scores: list[dict], scores: dict[str, list[dict]]) -> dict:
    """Everything the draft registers, from the whole-page baseline and each view's scores."""
    gains = {name: page_gains(s, baseline_scores) for name, s in scores.items()}

    def statistic(indices=None) -> tuple[float, float]:
        z = _share(gains[ZOOM_VIEW], "gain", indices)
        n = sum(_share(gains[v], "gain", indices) for v in PERTURBATION_VIEWS) / len(PERTURBATION_VIEWS)
        return z, n

    z, n = statistic()
    rng = random.Random(BOOTSTRAP_SEED)
    pages = len(baseline_scores)
    diffs = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        zb, nb = statistic([rng.randrange(pages) for _ in range(pages)])
        diffs.append(zb - nb)
    diffs.sort()
    bands_control = control_text_share(scores[ZOOM_VIEW])
    return {
        "per_view": {name: {
            "absent_text_share": _share(gains[name], "text"),
            "gain_over_baseline": _share(gains[name], "gain"),
            "loss_vs_baseline": _share(gains[name], "loss"),
            "control_text_share": control_text_share(scores[name]),
        } for name in scores},
        "perturbation_gain_N": n, "zoom_gain_Z": z, "Z_minus_N": z - n,
        "Z_minus_N_ci95": [diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]],
        "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "unit": "page"},
        "union_absent_text_share": {
            "baseline": union_share([baseline_scores]),
            "baseline+perturbation_views": union_share(
                [baseline_scores] + [scores[v] for v in PERTURBATION_VIEWS]),
            "baseline+bands": union_share([baseline_scores, scores[ZOOM_VIEW]]),
            "all": union_share([baseline_scores] + list(scores.values())),
        },
        "thresholds": {"gain": GAIN, "control_floor": CONTROL_FLOOR},
        "reading": reading(z, n, bands_control),
    }


# --- P-ZOOM-3 controls (`docs/stage0/P_ZOOM3_CONTROLS_DRAFT.md` §3-§4) ---------------------------
# Registered 2026-10-04, after an independent review found that the P-ZOOM-2 rule compares a
# decorrelated crop view with near-copy perturbation views, and before any P-ZOOM-2 or -3 output
# was read. `reading()` above stays as registered and is reported; statements about zoom use the
# controlled label below.

REPEAT_VIEW = "repeat"
CROP_VIEW = "bands100"
ZOOM_EFFECT = 0.10
MIN_IDENTICAL_PAGES = 18


def page_text_rows(view_scores: list[dict]) -> list[dict]:
    """Per page: absent marks and absent marks recovered as text."""
    rows = []
    for page in view_scores:
        absent = [r for r in page["lines"] if r["group"] == "absent"]
        rows.append({"absent": sum(r["marks"] for r in absent),
                     "text": sum(r["marks"] for r in absent if r["outcome"] == "text")})
    return rows


def churn_share(view_scores: list[dict], baseline_scores: list[dict]) -> float:
    """Share of absent marks whose line is `text` in exactly one of the view and the baseline."""
    total = changed = 0
    for view, base in zip(view_scores, baseline_scores):
        for v, b in zip(view["lines"], base["lines"]):
            if v["group"] != "absent":
                continue
            total += v["marks"]
            changed += v["marks"] * ((v["outcome"] == "text") != (b["outcome"] == "text"))
    return changed / total if total else 0.0


def identical_pages(repeat_outputs: dict[str, str], baseline_outputs: dict[str, str]) -> tuple[int, int]:
    """(pages whose repeat output equals the stored T1 output byte for byte, pages compared)."""
    if set(repeat_outputs) != set(baseline_outputs):
        raise ValueError("repeat and baseline cover different pages")
    return sum(repeat_outputs[i] == baseline_outputs[i] for i in repeat_outputs), len(repeat_outputs)


def controlled_reading(effect: float, ci: list[float], crop_control: float) -> str:
    """Zoom effect D = text share (bands, 1.85x) - text share (bands100, 1.0x), same crops."""
    if crop_control < CONTROL_FLOOR:
        return "instrument_fails_control"
    if effect >= ZOOM_EFFECT and ci[0] > 0:
        return "zoom_helps"
    if effect <= -ZOOM_EFFECT and ci[1] < 0:
        return "zoom_hurts"
    return "zoom_not_distinguishable"


def _bootstrap(stat, pages: int) -> list[float]:
    rng = random.Random(BOOTSTRAP_SEED)
    draws = sorted(stat([rng.randrange(pages) for _ in range(pages)]) for _ in range(BOOTSTRAP_RESAMPLES))
    return [draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]]


def analyze_controlled(baseline_scores: list[dict], scores: dict[str, list[dict]],
                       repeat_identical: tuple[int, int]) -> dict:
    """The P-ZOOM-3 readings, from the baseline, every view's scores and the exact-repeat check."""
    rows = {name: page_text_rows(s) for name, s in scores.items()}
    base_rows = page_text_rows(baseline_scores)
    pages = len(baseline_scores)

    def share(r, idx=None):
        chosen = r if idx is None else [r[i] for i in idx]
        total = sum(x["absent"] for x in chosen)
        return sum(x["text"] for x in chosen) / total if total else 0.0

    effect = share(rows[ZOOM_VIEW]) - share(rows[CROP_VIEW])
    ci = _bootstrap(lambda idx: share(rows[ZOOM_VIEW], idx) - share(rows[CROP_VIEW], idx), pages)
    crop_control = control_text_share(scores[CROP_VIEW])
    per_view = {}
    for name, r in rows.items():
        per_view[name] = {
            "absent_text_share": share(r),
            "net_vs_baseline": share(r) - share(base_rows),
            "net_vs_baseline_ci95": _bootstrap(lambda idx, r=r: share(r, idx) - share(base_rows, idx), pages),
            "churn_vs_baseline": churn_share(scores[name], baseline_scores),
            "control_text_share": control_text_share(scores[name]),
        }
    identical, compared = repeat_identical
    return {
        "baseline_absent_text_share": share(base_rows),
        "per_view": per_view,
        "zoom_effect_D": effect, "zoom_effect_ci95": ci, "crop_control_text_share": crop_control,
        "crop_effect_bands100_minus_baseline": share(rows[CROP_VIEW]) - share(base_rows),
        "repeat_identical_pages": [identical, compared],
        "stack": "baseline_reproduced" if identical >= MIN_IDENTICAL_PAGES else "stack_drift",
        "thresholds": {"zoom_effect": ZOOM_EFFECT, "control_floor": CONTROL_FLOOR,
                       "min_identical_pages": MIN_IDENTICAL_PAGES},
        "controlled_reading": controlled_reading(effect, ci, crop_control),
    }
