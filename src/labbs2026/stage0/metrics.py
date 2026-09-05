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
    latency_values = sorted(float(row["generation_seconds"]) for row in rows if row.get("generation_seconds") is not None)
    visual_counts = Counter(
        int(row["llm_visual_token_count"])
        for row in rows
        if row.get("llm_visual_token_count") is not None
    )
    return {
        "all": _group_summary(rows),
        "full_information": _group_summary(full),
        "language_candidate_bias_blank": _blank_bias_summary(blank),
        "per_component": per_component,
        "by_displayed_lexical_status": by_lexical_status,
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
