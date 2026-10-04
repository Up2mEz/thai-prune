"""Offline analysis of SPEC_DECODE_S1, exactly as registered.

`docs/stage0/SPEC_DECODE_S1_REGISTRATION.md` §4 (identity), §5 (speed and
populations) and addendum 2 (loop-aware sensitivity headline). Runs on fetched
records on CPU. Intervals: item-level bootstrap within task
(`labbs2026.thai_marks.analysis.bootstrap`, 10,000 resamples, seed 20260927).
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Iterable, Sequence

from labbs2026.output_diagnostics.structure import loop_period
from labbs2026.spec_decode.identity import compare_outputs, truncate_new_tokens
from labbs2026.thai_marks.analysis import bootstrap
from labbs2026.thai_marks.decompose import is_repetitive

NEAR_TIE = 0.1
SPEC_ARMS = ("PLD5", "PLD10")


def item_rows(records: Iterable[dict], max_new_tokens: int) -> list[dict]:
    """One row per timed item: populations, and per-arm speed and identity."""
    rows = []
    for rec in records:
        if rec["warmup"]:
            continue
        ref = rec["arms"]["REF"]
        ref_ids = truncate_new_tokens(ref["new_token_ids"], 0, max_new_tokens)
        headline = not ref["reached_max_new_tokens"] and not is_repetitive(ref["text"])
        row: dict[str, Any] = {
            "id": rec["id"], "task": rec["task"],
            "headline": headline,
            "headline_loop_aware": headline and loop_period(ref["text"]) is None,
            "ttft": rec["ref_extra"]["seconds_to_first_token"],
            "ref_seconds": ref["seconds_generate"],
        }
        for arm in SPEC_ARMS:
            if arm not in rec["arms"]:
                continue
            a = rec["arms"][arm]
            cmp = compare_outputs(ref_ids, truncate_new_tokens(a["new_token_ids"], 0, max_new_tokens))
            ident = rec["identity"].get(arm, {})
            margin = (ident.get("ref_margin") or {}).get("margin_logits")
            row[arm] = {
                "identical": cmp.identical,
                "first_divergence": cmp.first_divergence,
                "margin": margin,
                "divergence_class": None if cmp.identical else (
                    "near_tie" if margin is not None and margin <= NEAR_TIE else
                    "large_margin" if margin is not None else "length_only"),
                "speedup": ref["seconds_generate"] / a["seconds_generate"],
                "acceptance": a["generated_tokens"] / max(1, a["target_forwards"]),
                "decode_ms_per_token": 1000 * max(0.0, a["seconds_generate"] - rec["ref_extra"]["seconds_to_first_token"])
                / max(1, a["generated_tokens"] - 1),
            }
        row["REF_decode_ms_per_token"] = 1000 * max(0.0, ref["seconds_generate"] - row["ttft"]) / max(1, ref["generated_tokens"] - 1)
        rows.append(row)
    return rows


def _geomean(values: Sequence[float]) -> float | None:
    values = [v for v in values if v > 0]
    return math.exp(statistics.fmean(math.log(v) for v in values)) if values else None


def summarize(rows: Sequence[dict], *, resamples: int = 10_000) -> dict[str, Any]:
    populations = {
        "all": list(rows),
        "headline": [r for r in rows if r["headline"]],
        "headline_loop_aware": [r for r in rows if r["headline_loop_aware"]],
        "degenerate": [r for r in rows if not r["headline"]],
    }
    out: dict[str, Any] = {"items": len(rows), "populations": {k: len(v) for k, v in populations.items()}}
    for arm in SPEC_ARMS:
        have = [r for r in rows if arm in r]
        if not have:
            continue
        mismatches = [{"id": r["id"], "first_divergence": r[arm]["first_divergence"],
                       "margin": r[arm]["margin"], "class": r[arm]["divergence_class"]}
                      for r in have if not r[arm]["identical"]]
        entry: dict[str, Any] = {
            "identity_rate": sum(r[arm]["identical"] for r in have) / len(have),
            "mismatches": mismatches,
            "mismatch_classes": {c: sum(m["class"] == c for m in mismatches)
                                 for c in ("near_tie", "large_margin", "length_only")},
        }
        for name, pop in populations.items():
            pop = [r for r in pop if arm in r]
            if not pop:
                entry[name] = None
                continue
            entry[name] = {
                "geomean_speedup": bootstrap(pop, lambda xs, a=arm: _geomean([x[a]["speedup"] for x in xs]),
                                             resamples=resamples),
                "median_acceptance": bootstrap(pop, lambda xs, a=arm: statistics.median(x[a]["acceptance"] for x in xs),
                                               resamples=resamples),
                "median_decode_ms_per_token": statistics.median(r[arm]["decode_ms_per_token"] for r in pop),
                "median_ref_decode_ms_per_token": statistics.median(r["REF_decode_ms_per_token"] for r in pop),
            }
        out[arm] = entry
    return out


def t1_cross_check(records: Iterable[dict], t1_records: Iterable[dict]) -> dict[str, Any]:
    """Registration §6: share of `REF` outputs textually identical to T1's raw
    `TYPHOON_CARD` output for the same item and model (timed items only)."""
    t1 = {r["id"]: r for r in t1_records if r.get("prompt_kind") == "TYPHOON_CARD"}
    matched = identical = same_tokens = 0
    missing, differing = [], []
    for rec in records:
        if rec["warmup"]:
            continue
        other = t1.get(rec["id"])
        if other is None:
            missing.append(rec["id"])
            continue
        ref = rec["arms"]["REF"]
        matched += 1
        same_tokens += ref["generated_tokens"] == other["generated_tokens"]
        if ref["text"] == other["raw_output"]:
            identical += 1
        else:
            differing.append(rec["id"])
    return {"matched": matched, "identical": identical,
            "identity_rate": identical / matched if matched else None,
            "same_generated_tokens": same_tokens, "missing": missing, "differing": differing}
