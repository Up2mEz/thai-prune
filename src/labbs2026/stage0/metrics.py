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
    scored = [row for row in rows if row.get("expected_label") is not None]
    parsed_scored = [row for row in scored if row.get("parse_status") == "PARSED"]
    return {
        "observation_count": len(rows),
        "pair_count": len({row["pair_id"] for row in rows}),
        "parsed_count": len(parsed),
        "parser_failure_count": len(rows) - len(parsed),
        "parser_failure_rate": (len(rows) - len(parsed)) / len(rows) if rows else None,
        "scored_observation_count": len(scored),
        "accuracy_all_scored_observations": _accuracy(scored),
        "accuracy_conditional_parsed": _accuracy(parsed_scored),
    }


def _blank_bias_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [row for row in rows if row.get("parse_status") == "PARSED"]
    selected_status = Counter()
    canonical_member = Counter()
    for row in parsed:
        choice = row["parsed_output"]
        selected_status[row[f"candidate_{choice.lower()}_lexical_status"]] += 1
        if (choice == "A" and row["orientation"] == "A_THEN_B") or (
            choice == "B" and row["orientation"] == "B_THEN_A"
        ):
            canonical_member["text_a"] += 1
        else:
            canonical_member["text_b"] += 1
    return {
        "control_type": "LANGUAGE_CANDIDATE_BIAS_BLANK",
        "has_visual_ground_truth": False,
        "accuracy": None,
        "observation_count": len(rows),
        "pair_count": len({row["pair_id"] for row in rows}),
        "parsed_count": len(parsed),
        "parser_failure_count": len(rows) - len(parsed),
        "parser_failure_rate": (len(rows) - len(parsed)) / len(rows) if rows else None,
        "choice_a_rate": (
            sum(row["parsed_output"] == "A" for row in parsed) / len(parsed)
            if parsed
            else None
        ),
        "canonical_member_choice_counts": dict(sorted(canonical_member.items())),
        "selected_lexical_status_counts": dict(sorted(selected_status.items())),
    }


def _pair_heterogeneity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_id"]].append(row)
    values = np.asarray(
        [_accuracy(by_pair[pair_id]) for pair_id in sorted(by_pair)], dtype=np.float64
    )
    if not len(values):
        return {
            "pair_count": 0,
            "minimum_pair_accuracy": None,
            "q25_pair_accuracy": None,
            "median_pair_accuracy": None,
            "q75_pair_accuracy": None,
            "maximum_pair_accuracy": None,
            "standard_deviation_pair_accuracy": None,
            "perfect_pair_count": 0,
            "zero_accuracy_pair_count": 0,
        }
    return {
        "pair_count": int(len(values)),
        "minimum_pair_accuracy": float(np.min(values)),
        "q25_pair_accuracy": float(np.quantile(values, 0.25)),
        "median_pair_accuracy": float(np.median(values)),
        "q75_pair_accuracy": float(np.quantile(values, 0.75)),
        "maximum_pair_accuracy": float(np.max(values)),
        "standard_deviation_pair_accuracy": float(np.std(values, ddof=1))
        if len(values) > 1
        else 0.0,
        "perfect_pair_count": int(np.sum(values == 1.0)),
        "zero_accuracy_pair_count": int(np.sum(values == 0.0)),
    }


def _latency_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = sorted(float(row[field]) for row in rows if row.get(field) is not None)
    return {
        "count": len(values),
        "median": median(values) if values else None,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "total": sum(values) if values else None,
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
    blank = [
        row
        for row in rows
        if row.get("control_type") == "LANGUAGE_CANDIDATE_BIAS_BLANK"
    ]
    per_component = {
        component: _group_summary([row for row in full if row["component_type"] == component])
        for component in sorted({row["component_type"] for row in full})
    }
    per_condition = {
        condition: _group_summary(
            [row for row in full if row["condition_id"] == condition]
        )
        for condition in sorted({row["condition_id"] for row in full})
    }
    by_lexical_status = {
        status: _group_summary(
            [row for row in full if row.get("displayed_lexical_status") == status]
        )
        for status in ("REAL", "CONSTRUCTED", "UNCERTAIN")
    }
    by_expected = {
        label: _group_summary([row for row in full if row["expected_label"] == label])
        for label in ("A", "B")
    }
    accuracy_a = by_expected["A"]["accuracy_all_scored_observations"]
    accuracy_b = by_expected["B"]["accuracy_all_scored_observations"]
    order_gap = abs(accuracy_a - accuracy_b) if accuracy_a is not None and accuracy_b is not None else None
    visual_counts = Counter(
        int(row["llm_visual_token_count"])
        for row in rows
        if row.get("llm_visual_token_count") is not None
    )
    per_component_intervals = {
        component: cluster_bootstrap_accuracy(
            [row for row in full if row["component_type"] == component],
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
        for component in per_component
    }
    per_condition_intervals = {
        condition: cluster_bootstrap_accuracy(
            [row for row in full if row["condition_id"] == condition],
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
        for condition in per_condition
    }
    overall_interval = cluster_bootstrap_accuracy(
        full,
        seed=bootstrap_seed,
        resamples=bootstrap_resamples,
        confidence_level=confidence_level,
    )
    baseline_accuracy = _accuracy(full)
    token_counts_by_condition = {
        condition: dict(
            sorted(
                Counter(
                    int(row["llm_visual_token_count"])
                    for row in full
                    if row["condition_id"] == condition
                    and row.get("llm_visual_token_count") is not None
                ).items()
            )
        )
        for condition in per_condition
    }
    return {
        "all": _group_summary(rows),
        "full_information": _group_summary(full),
        "language_candidate_bias_blank": _blank_bias_summary(blank),
        "per_component": per_component,
        "per_condition": per_condition,
        "by_displayed_lexical_status": by_lexical_status,
        "by_expected_label": by_expected,
        "candidate_order_gap": order_gap,
        "candidate_order_behavior": {
            "parsed_choice_a_rate": (
                sum(row.get("parsed_output") == "A" for row in full)
                / sum(row.get("parse_status") == "PARSED" for row in full)
                if any(row.get("parse_status") == "PARSED" for row in full)
                else None
            ),
            "by_expected_label": by_expected,
            "by_pair_orientation": {
                orientation: _group_summary(
                    [row for row in full if row["orientation"] == orientation]
                )
                for orientation in ("A_THEN_B", "B_THEN_A")
            },
        },
        "pair_clustered_accuracy_interval": overall_interval,
        "per_component_pair_clustered_accuracy_interval": per_component_intervals,
        "per_condition_pair_clustered_accuracy_interval": per_condition_intervals,
        "pair_level_heterogeneity": {
            "overall": _pair_heterogeneity(full),
            "per_component": {
                component: _pair_heterogeneity(
                    [row for row in full if row["component_type"] == component]
                )
                for component in per_component
            },
        },
        "achieved_measurement_precision": {
            "overall_interval_width": (
                overall_interval["upper"] - overall_interval["lower"]
                if overall_interval["upper"] is not None
                else None
            ),
            "per_component_interval_width": {
                component: interval["upper"] - interval["lower"]
                if interval["upper"] is not None
                else None
                for component, interval in per_component_intervals.items()
            },
        },
        "ceiling_headroom": {
            "full_information_accuracy": baseline_accuracy,
            "distance_below_perfect_accuracy": 1.0 - baseline_accuracy
            if baseline_accuracy is not None
            else None,
            "distance_above_binary_chance": baseline_accuracy - 0.5
            if baseline_accuracy is not None
            else None,
            "interpretation_scope": "descriptive calibration only",
        },
        "preprocess_seconds": _latency_summary(rows, "preprocess_seconds"),
        "generation_seconds": _latency_summary(rows, "generation_seconds"),
        "llm_visual_token_count_distribution": dict(sorted(visual_counts.items())),
        "llm_visual_token_count_by_condition": token_counts_by_condition,
        "blank_bias_per_component": {
            component: _blank_bias_summary(
                [row for row in blank if row["component_type"] == component]
            )
            for component in sorted({row["component_type"] for row in blank})
        },
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
