"""Assembly of the full registered report from a completed run's observations."""

from __future__ import annotations

import collections
from typing import Any, Iterable, Sequence

from labbs2026.region_ocr.analysis import (
    FULL,
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
        ],
    }
