"""Offline analysis of REMEDIES_R1, exactly as registered (§4).

Every arm is compared with FULL paired by item. Mark-specific error is computed
only on items where both FULL's and the arm's output are `misread` or
`reading_order` (`output_diagnostics`), because in looped or over-generated
outputs nearly every mark counts as deleted and the rate would measure the loop
rate. The cause transition table shows what the arm does to the other items.
"""

from __future__ import annotations

import collections
import math
import statistics
from typing import Any, Iterable, Sequence

from labbs2026.output_diagnostics.structure import deloop, structural_normalize
from labbs2026.output_diagnostics.taxonomy import diagnose
from labbs2026.thai_marks.analysis import bootstrap
from labbs2026.thai_marks.decompose import mark_decomposition

READABLE = frozenset({"misread", "reading_order"})
KINDS = ("TONE", "UPPER", "LOWER")


def _marks(reference: str, raw: str) -> dict[str, int]:
    marks = mark_decomposition(structural_normalize(reference), structural_normalize(deloop(raw)))
    out = {"consonant_n": marks["CONSONANT"]["n"], "consonant_error": marks["CONSONANT"]["error"]}
    for k in KINDS:
        out[f"{k}_base_n"] = marks[k].get("base_correct_n", 0)
        out[f"{k}_base_error"] = marks[k].get("base_correct_error", 0)
    return out


def item_rows(records: Iterable[dict]) -> list[dict]:
    """One row per item: per arm the diagnosis, CERs, mark counts and seconds."""
    rows = []
    for rec in records:
        row: dict[str, Any] = {"id": rec["id"], "task": rec["task"], "arms": {}}
        for name, a in rec["arms"].items():
            if a.get("failed"):
                row["arms"][name] = {"failed": True}
                continue
            d = diagnose(rec["reference"], a["raw_output"])
            row["arms"][name] = {
                "cause": d["primary_cause"], "cer_t1": d["cer_t1"],
                "cer_structural": d["cer_structural"], "cer_structural_delooped": d["cer_structural_delooped"],
                "edits_t1": d["t1_edits"], "ref_chars": d["ref_chars"],
                "seconds": a["seconds_generate"], "generated_tokens": a["generated_tokens"],
                "reached_max": a["reached_max_new_tokens"],
                **_marks(rec["reference"], a["raw_output"]),
            }
        rows.append(row)
    return rows


def _ratio(xs, num, den):
    n = sum(x[num] for x in xs)
    d = sum(x[den] for x in xs)
    return n / d if d else None


def _paired(rows: Sequence[dict], arm: str, num: str, den: str, resamples: int) -> dict:
    """Pooled rate for FULL and the arm on the same items, and arm − FULL with an interval."""
    pairs = [{"task": r["task"], "full": r["arms"]["FULL"], "arm": r["arms"][arm]} for r in rows]

    def diff(xs):
        f = _ratio([x["full"] for x in xs], num, den)
        a = _ratio([x["arm"] for x in xs], num, den)
        return None if f is None or a is None else a - f

    return {
        "FULL": _ratio([p["full"] for p in pairs], num, den),
        "arm": _ratio([p["arm"] for p in pairs], num, den),
        "arm_minus_FULL": bootstrap(pairs, diff, resamples=resamples),
    }


def summarize(rows: Sequence[dict], *, resamples: int = 10_000) -> dict[str, Any]:
    arms = sorted({a for r in rows for a in r["arms"]} - {"FULL"})
    out: dict[str, Any] = {"items": len(rows), "FULL_causes": dict(collections.Counter(
        r["arms"]["FULL"].get("cause", "failed") for r in rows if "FULL" in r["arms"]))}
    for arm in arms:
        both = [r for r in rows if "FULL" in r["arms"] and arm in r["arms"]
                and not r["arms"]["FULL"].get("failed") and not r["arms"][arm].get("failed")]
        kept = [r for r in both if r["arms"]["FULL"]["cause"] in READABLE and r["arms"][arm]["cause"] in READABLE]
        transitions = collections.Counter((r["arms"]["FULL"]["cause"], r["arms"][arm]["cause"]) for r in both)
        entry: dict[str, Any] = {
            "items_compared": len(both), "items_failed": len(rows) - len(both), "items_kept_for_marks": len(kept),
            "cause_transitions": {f"{a}->{b}": n for (a, b), n in sorted(transitions.items())},
            "micro_cer_t1": _paired(both, arm, "edits_t1", "ref_chars", resamples),
            "macro_cer_structural_delooped": {
                "FULL": statistics.fmean(r["arms"]["FULL"]["cer_structural_delooped"] for r in both) if both else None,
                "arm": statistics.fmean(r["arms"][arm]["cer_structural_delooped"] for r in both) if both else None,
            },
            "consonant_error_kept": _paired(kept, arm, "consonant_error", "consonant_n", resamples) if kept else None,
            "latency_ratio_geomean": math.exp(statistics.fmean(
                math.log(r["arms"][arm]["seconds"] / r["arms"]["FULL"]["seconds"]) for r in both)) if both else None,
        }
        for k in KINDS:
            entry[f"{k}_mark_specific_error_kept"] = (
                _paired(kept, arm, f"{k}_base_error", f"{k}_base_n", resamples) if kept else None)
        out[arm] = entry
    return out
