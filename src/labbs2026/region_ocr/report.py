"""Assembly of the full registered report from a completed run's observations."""

from __future__ import annotations

import collections
import statistics
from typing import Any, Iterable, Sequence

from labbs2026.region_ocr.analysis import (
    FULL,
    analyse_contrast,
    analyse_marginal,
    analyse_population,
    per_region_cer,
)
from labbs2026.region_ocr.text_metrics import cer_summary, component_error_counts


def generation_health(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Truncation, empty and degenerate rates, reported per condition.

    Kept out of CER deliberately. If pruning mainly increases truncation, a CER
    table alone would read as recognition loss when the real finding is that
    generation stopped behaving, so the two are never merged.
    """
    per_condition: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"observations": 0, "truncated": 0, "empty": 0, "cer_over_one": 0}
    )
    for record in records:
        bucket = per_condition[record["condition_id"]]
        bucket["observations"] += 1
        if record.get("reached_max_new_tokens"):
            bucket["truncated"] += 1
        if not record.get("parsed_output"):
            bucket["empty"] += 1
    return {k: dict(v) for k, v in sorted(per_condition.items())}


def component_breakdown(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Per-component error tallies by condition.

    Diagnostic only: alignment-dependent, non-causal, and outside every
    multiplicity family.
    """
    totals: dict[str, dict[str, dict[str, int]]] = {}
    for record in records:
        counts = component_error_counts(record["reference"], record["parsed_output"])
        condition = totals.setdefault(record["condition_id"], {})
        for name, entry in counts["components"].items():
            target = condition.setdefault(
                name,
                {"reference_total": 0, "hypothesis_total": 0,
                 "substitution": 0, "deletion": 0, "insertion": 0},
            )
            for field, value in entry.items():
                target[field] += value
    return {
        "status": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
        "note": "alignment-dependent; not causal; outside every multiplicity family",
        "by_condition": {k: totals[k] for k in sorted(totals)},
    }


def absolute_cer(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Macro and micro CER per condition, both declared in the protocol."""
    grouped: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for record in records:
        grouped[record["condition_id"]].append(
            (record["reference"], record["parsed_output"])
        )
    return {k: cer_summary(v) for k, v in sorted(grouped.items())}



_STAGES = ("processor", "vision", "select", "embed", "prefill", "generate")


def _median(values: Sequence[float]) -> float | None:
    numeric = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(numeric) if numeric else None


def efficiency_profile(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Cost per condition, resolved into stages rather than one wall time.

    Reported separately from accuracy and never combined with it: this run
    registers no exchange rate between characters and seconds, and inventing one
    afterwards would be choosing the conclusion.

    Two cautions travel with the numbers. Wall clock on a shared accelerator is
    not reproducible, so the analytic counters beside it - which are exact - are
    what any claim should rest on. And `seconds_generate` includes decode, whose
    length is an outcome of the intervention, so a condition that gives up early
    looks cheap; `seconds_prefill` is the part an intervention can actually
    shorten.
    """
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        grouped[record["condition_id"]].append(record)

    by_condition: dict[str, Any] = {}
    for condition, rows in sorted(grouped.items()):
        entry: dict[str, Any] = {"observations": len(rows)}
        for stage in _STAGES:
            entry[f"median_seconds_{stage}"] = _median(
                [r.get(f"seconds_{stage}") for r in rows]
            )
        entry["median_seconds_decode"] = _median([r.get("seconds_decode") for r in rows])
        entry["median_peak_bytes"] = _median([r.get("peak_bytes_observation") for r in rows])
        entry["memory_measured"] = bool(rows[0].get("memory_measured"))
        entry["median_vision_patches"] = _median([r.get("vision_patches") for r in rows])
        entry["median_llm_visual_positions"] = _median(
            [r.get("llm_visual_positions") for r in rows]
        )
        entry["median_generated_tokens"] = _median([r.get("generated_tokens") for r in rows])
        by_condition[condition] = entry

    # Records written before stage accounting existed carry no patch counts, and
    # an absent counter must read as unverified rather than as a satisfied
    # invariant.
    post_encoder = [
        r
        for condition, rows in grouped.items()
        if condition != FULL and not condition.startswith("RR_")
        for r in rows
    ]
    counted = [r["vision_patches"] for r in post_encoder if r.get("vision_patches") is not None]
    invariant: bool | str = "UNKNOWN_NOT_RECORDED"
    if post_encoder and len(counted) == len(post_encoder):
        per_region = collections.defaultdict(set)
        for record in post_encoder:
            per_region[record["image_id"]].add(record["vision_patches"])
        invariant = all(len(v) == 1 for v in per_region.values())
    return {
        "status": "DESCRIPTIVE_COST_ACCOUNTING",
        "note": (
            "wall clock is hardware- and contention-dependent; the analytic "
            "counters are exact and should carry any efficiency claim"
        ),
        "post_encoder_vision_cost_invariant": invariant,
        "by_condition": by_condition,
    }


def processor_geometry(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """What the processor did to the image before the encoder saw it.

    Needed because a reduced budget scoring better than FULL has a mundane
    alternative explanation: the processor upsamples a small crop to reach its
    pixel floor, and a lower budget upsamples it less. That is an interpolation
    artefact being removed, not evidence that compression helps, and the two are
    indistinguishable without these numbers.
    """
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        grouped[record["condition_id"]].append(record)
    return {
        "status": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
        "by_condition": {
            condition: {
                "observations": len(rows),
                "upsampled_fraction": (
                    sum(1 for r in rows if r.get("native_processor_upsampled")) / len(rows)
                ),
                "median_processor_scale": _median(
                    [r.get("native_processor_scale") for r in rows]
                ),
                "median_source_pixels": _median(
                    [
                        (r.get("native_source_height") or 0) * (r.get("native_source_width") or 0)
                        for r in rows
                    ]
                ),
                "median_processed_pixels": _median(
                    [
                        (r.get("native_processed_height") or 0)
                        * (r.get("native_processed_width") or 0)
                        for r in rows
                    ]
                ),
            }
            for condition, rows in sorted(grouped.items())
        },
    }


def build_report(
    records: Sequence[dict[str, Any]],
    *,
    budgets: Sequence[str],
    resamples: int,
    seed: int,
    execution_failures: int,
) -> dict[str, Any]:
    table = per_region_cer(records)
    clusters = {r["image_id"]: r["source_photo_id"] for r in records}
    primary = analyse_population(
        table, clusters, budgets, resamples=resamples, seed=seed, full_correct_only=False
    )
    secondary = analyse_population(
        table, clusters, budgets, resamples=resamples, seed=seed, full_correct_only=True
    )
    full_rows = [r for r in records if r["condition_id"] == FULL]
    return {
        "status": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "claim_scope": "text-region recognition on Thai document images",
        "observations": len(records),
        "execution_failures": execution_failures,
        "failures_scored_as_cer_one": False,
        "regions_at_full": len(full_rows),
        "primary": primary,
        "secondary": secondary,
        "absolute_cer": absolute_cer(records),
        "generation_health": generation_health(records),
        "component_diagnostic": component_breakdown(records),
        "contrast_families": {
            # Registered before the run; each corrected within itself only.
            "B_merge_vs_prune": analyse_contrast(
                table, clusters, budgets, treatment="MERGE_GRID",
                reference="PRUNE_GRID", resamples=resamples, seed=seed,
            ),
            "C_coverage_vs_prune": analyse_contrast(
                table, clusters, budgets, treatment="PRUNE_COVERAGE",
                reference="PRUNE_GRID", resamples=resamples, seed=seed,
            ),
            # D is family A with pixel detail matched: both arms carry the same
            # information and end at the same token count, so what remains is
            # where the reduction happened. A is not interpretable as an
            # insertion-point result without it.
            "D_restored_prune_vs_rr": analyse_contrast(
                table, clusters, budgets, treatment="PRUNE_GRID_RESTORED",
                reference="RR", resamples=resamples, seed=seed,
            ),
            # E isolates the detail reduction on its own, at FULL's token count
            # and FULL's magnification.
            "E_restored_vs_full": analyse_marginal(
                table, clusters, budgets, condition="RR_RESTORED",
                resamples=resamples, seed=seed,
            ),
        },
        "efficiency_profile": efficiency_profile(records),
        "processor_geometry": processor_geometry(records),
        "limitations": [
            "A median crop carries far fewer tokens of native detail than it is "
            "presented with, so most visual tokens are interpolated redundancy. "
            "That biases the design towards finding pruning harmless: a positive "
            "result is strong, a null is weak.",
            "Budget labels are nominal; achieved fractions vary by region and are "
            "recorded per observation.",
            "Within the secondary population each arm's marginal delta-CER is "
            "non-negative by construction, so no absolute degradation rate and no "
            "generalisation to Thai region OCR as a whole may be claimed from it.",
            "Scene text against document-trained models; single model family.",
            "Post-encoder conditions cannot reduce vision-encoder cost by "
            "construction, so any end-to-end speed-up they show is bounded by the "
            "language model's share of the total and must not be quoted as a "
            "whole-pipeline saving.",
            "Timings come from a shared accelerator and are not reproducible; the "
            "analytic token and patch counts recorded beside them are.",
        ],
    }
