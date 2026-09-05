"""Threshold-free Stage 0 calibration metrics with pair-clustered uncertainty."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any, Iterable

import numpy as np


def _accuracy(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return sum(bool(row.get("is_correct")) for row in rows) / len(rows)


def _group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [row for row in rows if row.get("parse_status") == "PARSED"]
    return {
        "observation_count": len(rows),
        "pair_count": len({row["pair_id"] for row in rows}),
        "parsed_count": len(parsed),
        "parser_failure_count": len(rows) - len(parsed),
        "parser_failure_rate": (len(rows) - len(parsed)) / len(rows) if rows else None,
        "accuracy_all_observations": _accuracy(rows),
        "accuracy_conditional_parsed": _accuracy(parsed),
    }


def cluster_bootstrap_accuracy(
    rows: list[dict[str, Any]], *, seed: int, resamples: int, confidence_level: float
) -> dict[str, float | int | None]:
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one")
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_id"]].append(row)
    pair_ids = sorted(by_pair)
    if not pair_ids:
        return {"pair_count": 0, "estimate": None, "lower": None, "upper": None}
    rng = np.random.default_rng(seed)
    estimates = np.empty(resamples, dtype=np.float64)
    for index in range(resamples):
        sampled = rng.choice(pair_ids, size=len(pair_ids), replace=True)
        sampled_rows = [row for pair_id in sampled for row in by_pair[str(pair_id)]]
        estimates[index] = float(_accuracy(sampled_rows))
    alpha = (1 - confidence_level) / 2
    return {
        "pair_count": len(pair_ids),
        "estimate": _accuracy(rows),
        "lower": float(np.quantile(estimates, alpha)),
        "upper": float(np.quantile(estimates, 1 - alpha)),
    }


def compute_stage0_metrics(
    predictions: Iterable[dict[str, Any]],
    *,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    rows = list(predictions)
    full = [row for row in rows if row.get("control_type") == "FULL_INFORMATION"]
    blank = [row for row in rows if row.get("control_type") == "LANGUAGE_PRIOR_BLANK"]
    per_component = {
        component: _group_summary([row for row in full if row["component_type"] == component])
        for component in sorted({row["component_type"] for row in full})
    }
    by_expected = {
        label: _group_summary([row for row in full if row["expected_label"] == label])
        for label in ("A", "B")
    }
    accuracy_a = by_expected["A"]["accuracy_all_observations"]
    accuracy_b = by_expected["B"]["accuracy_all_observations"]
    order_gap = abs(accuracy_a - accuracy_b) if accuracy_a is not None and accuracy_b is not None else None
    full_accuracy = _accuracy(full)
    blank_accuracy = _accuracy(blank)
    latency_values = sorted(float(row["generation_seconds"]) for row in rows if row.get("generation_seconds") is not None)
    visual_counts = Counter(
        int(row["llm_visual_token_count"])
        for row in rows
        if row.get("llm_visual_token_count") is not None
    )
    return {
        "all": _group_summary(rows),
        "full_information": _group_summary(full),
        "language_prior_blank": _group_summary(blank),
        "full_minus_blank_accuracy": (
            full_accuracy - blank_accuracy
            if full_accuracy is not None and blank_accuracy is not None
            else None
        ),
        "per_component": per_component,
        "by_expected_label": by_expected,
        "candidate_order_gap": order_gap,
        "pair_clustered_accuracy_interval": cluster_bootstrap_accuracy(
            full,
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        ),
        "generation_seconds": {
            "count": len(latency_values),
            "median": median(latency_values) if latency_values else None,
            "minimum": min(latency_values) if latency_values else None,
            "maximum": max(latency_values) if latency_values else None,
        },
        "llm_visual_token_count_distribution": dict(sorted(visual_counts.items())),
    }


def compare_reproducibility(
    first: Iterable[dict[str, Any]], second: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    first_by_id = {row["observation_id"]: row for row in first}
    second_by_id = {row["observation_id"]: row for row in second}
    common = sorted(set(first_by_id) & set(second_by_id))
    fields = ("raw_output", "parsed_output", "parse_status", "llm_visual_token_count")
    agreements = {
        field: sum(first_by_id[item].get(field) == second_by_id[item].get(field) for item in common)
        for field in fields
    }
    return {
        "first_count": len(first_by_id),
        "second_count": len(second_by_id),
        "common_count": len(common),
        "same_observation_ids": set(first_by_id) == set(second_by_id),
        "agreement_counts": agreements,
        "agreement_rates": {
            field: count / len(common) if common else None
            for field, count in agreements.items()
        },
    }
