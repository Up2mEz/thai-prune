"""Offline analysis of FIND_VS_READ_F1, as registered.

Primary outcome (per model, Typhoon first): **paired mark-level fates** with
exact counts. For each contrast (arm vs reference arm) and each reference mark
**scored in both arms**: correct->correct,
correct->wrong, wrong->correct, wrong->wrong. Marks scored in only one arm
are counted separately. No interval, no decision rule on an interval: with
~100 tone marks in the calibration items, F1 tests direction and mechanism,
not magnitude.

A mark is *scored* in an arm when its base consonant was read correctly and,
under the primary rule of registration addendum 1, the arm's answer was
**found** (window CER <= 0.5): the smoke showed that a best window searched in
an unrelated answer can match a base consonant by chance. The rule as first
registered (base-correct only) is kept as `rule="base_only"`, a sensitivity.

Contrasts: CROP_SAME_SCALE vs WHOLE (finding), CROP_RESCALED vs
CROP_SAME_SCALE (magnification), CROP_RESCALED vs WHOLE (both), and
WHOLE_MARKED vs WHOLE (secondary). Descriptive per arm: localisation failures
(no base-correct mark although the reference has marks), found rate with its
chance baseline, exact rate, over-generation, time and visual tokens.
Primary normalization: T1's `normalize_text`; structure-aware normalization
as a sensitivity.
"""

from __future__ import annotations

import collections
import statistics
from typing import Any, Callable, Iterable, Sequence

from labbs2026.find_vs_read.scoring import best_window, chance_found_rate, score_answer
from labbs2026.output_diagnostics.structure import structural_normalize
from labbs2026.thai_marks.normalize import normalize_text

ARMS = ("WHOLE", "CROP_SAME_SCALE", "CROP_RESCALED", "WHOLE_MARKED", "WHOLE_NOCLAUSE")
CONTRASTS = (
    ("CROP_SAME_SCALE", "WHOLE"),        # finding
    ("CROP_RESCALED", "CROP_SAME_SCALE"),  # magnification
    ("CROP_RESCALED", "WHOLE"),           # both
    ("WHOLE_MARKED", "WHOLE"),            # secondary: a drawn box
    ("WHOLE_NOCLAUSE", "WHOLE"),          # addendum 2: following the coordinate-system clause
    ("CROP_SAME_SCALE", "WHOLE_NOCLAUSE"),  # addendum 2: finding, with that clause removed from both
)
KINDS = ("TONE", "UPPER", "LOWER")
NORMALIZERS: dict[str, Callable[[str], str]] = {"t1": normalize_text, "structural": structural_normalize}


def item_rows(records: Iterable[dict], normalize: Callable[[str], str] = normalize_text) -> list[dict]:
    rows = []
    for rec in records:
        ref = normalize(rec["reference"])
        row: dict[str, Any] = {"id": rec["id"], "task": rec["task"], "reference": ref, "arms": {}}
        for arm, a in rec["arms"].items():
            if a.get("failed"):
                row["arms"][arm] = {"failed": True}
                continue
            hyp = normalize(a["raw_output"])
            row["arms"][arm] = {**score_answer(ref, hyp), "hypothesis": hyp,
                                "reached_max": a["reached_max_new_tokens"],
                                "seconds": a["seconds_generate"], "visual_tokens": a["visual_tokens"]}
        rows.append(row)
    return rows


RULES = ("found_and_base", "base_only")


def _status(mark: dict, cell: dict, rule: str) -> str:
    if rule not in RULES:
        raise ValueError(f"unknown rule {rule!r}")
    if not mark["base_correct"] or (rule == "found_and_base" and not cell["found"]):
        return "unscored"
    return "correct" if mark["fate"] == "correct" else "wrong"


def paired_fates(rows: Sequence[dict], arm: str, base: str, *, rule: str = "found_and_base") -> dict[str, Any]:
    """Exact counts of paired mark statuses, per class, under a scoring rule."""
    usable = [r for r in rows if all(k in r["arms"] and not r["arms"][k].get("failed") for k in (arm, base))]
    table: dict[str, collections.Counter] = {k: collections.Counter() for k in KINDS}
    for r in usable:
        a_cell, b_cell = r["arms"][arm], r["arms"][base]
        a_marks = {m["index"]: m for m in a_cell["mark_fates"]}
        for m in b_cell["mark_fates"]:
            sb, sa = _status(m, b_cell, rule), _status(a_marks[m["index"]], a_cell, rule)
            if sb == "unscored" and sa == "unscored":
                key = "unscored_in_both"
            elif sb == "unscored":
                key = f"scored_only_in_{arm}"
            elif sa == "unscored":
                key = f"scored_only_in_{base}"
            else:
                key = f"{sb}->{sa}"
            table[m["kind"]][key] += 1
    return {"items": len(usable), "rule": rule,
            "fates": {k: dict(sorted(v.items())) for k, v in table.items()},
            "fate_changes_by_class": {
                k: {f"{base}_wrong_fixed_by_{arm}": v.get("wrong->correct", 0),
                    f"{base}_correct_broken_by_{arm}": v.get("correct->wrong", 0)}
                for k, v in table.items()}}


def _rate(xs, key):
    return statistics.fmean(1.0 if x[key] else 0.0 for x in xs) if xs else None


def summarize(rows: Sequence[dict]) -> dict[str, Any]:
    rows = [r for r in rows if r["reference"]]
    out: dict[str, Any] = {"items": len(rows)}
    for arm in ARMS:
        have = [r for r in rows if arm in r["arms"] and not r["arms"][arm].get("failed")]
        if not have:
            continue
        cells = [r["arms"][arm] for r in have]
        with_marks = [c for c in cells if c["mark_fates"]]
        out[arm] = {
            "n": len(cells),
            "failed": sum(1 for r in rows if r["arms"].get(arm, {}).get("failed")),
            "localisation_failures": sum(1 for c in with_marks if not c["has_base_correct_mark"]),
            "not_found_with_reference_marks": sum(1 for c in with_marks if not c["found"]),
            "items_with_reference_marks": len(with_marks),
            "found_rate": _rate(cells, "found"),
            "chance_found_rate": chance_found_rate([r["reference"] for r in have],
                                                   [r["arms"][arm]["hypothesis"] for r in have]),
            "exact_rate": _rate(cells, "exact"),
            "median_extra_chars": statistics.median(c["extra_chars"] for c in cells),
            "reached_max_new_tokens": sum(c["reached_max"] for c in cells),
            "median_seconds": statistics.median(c["seconds"] for c in cells),
            "median_visual_tokens": statistics.median(c["visual_tokens"] for c in cells),
        }
    for arm, base in CONTRASTS:
        out[f"{arm}_vs_{base}"] = paired_fates(rows, arm, base, rule="found_and_base")
        out[f"{arm}_vs_{base}__base_only"] = paired_fates(rows, arm, base, rule="base_only")
    out["reference_disagreements"] = reference_disagreements(rows)
    return out


def reference_disagreements(rows: Sequence[dict]) -> list[dict[str, Any]]:
    """Exploratory (addendum 1): items where both crop arms return the same text,
    found, but not equal to the reference — candidates for a reference error,
    listed for human inspection; scores are never changed because of them."""
    out = []
    for r in rows:
        cells = [r["arms"].get(k) for k in ("CROP_SAME_SCALE", "CROP_RESCALED")]
        if any(c is None or c.get("failed") or not c["found"] for c in cells):
            continue
        windows = []
        for c in cells:
            _, s, e = best_window(r["reference"], c["hypothesis"])
            windows.append(c["hypothesis"][s:e])
        if windows[0] == windows[1] and windows[0] != r["reference"]:
            out.append({"id": r["id"], "reference": r["reference"], "both_crops_read": windows[0]})
    return out
