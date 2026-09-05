"""Exact workload derivation for a human-frozen Stage 0 calibration design."""

from __future__ import annotations

from typing import Any

from labbs2026.stage0.run import calibration_readiness_issues, make_observation_plan


def derive_workload(
    config: dict[str, Any],
    review: dict[str, Any] | None,
    resolved_pairs: list[dict[str, Any]],
    render_manifest: list[dict[str, Any]],
    prompt_template: str,
) -> dict[str, Any]:
    issues = calibration_readiness_issues(config, review)
    if issues:
        return {
            "status": "BLOCKED_PENDING_HUMAN_FREEZE",
            "blocking_issues": issues,
            "exact_observation_count": None,
        }
    observations = make_observation_plan(
        config, resolved_pairs, render_manifest, prompt_template
    )
    full_count = sum(
        row["control_type"] == "FULL_INFORMATION" for row in observations
    )
    blank_count = sum(
        row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
        for row in observations
    )
    return {
        "status": "READY_FOR_CALIBRATION_SUBMISSION",
        "backend": "kaggle",
        "requested_accelerator": "NvidiaTeslaT4",
        "compression_family": "FULL_INFORMATION",
        "exact_observation_count": len(observations),
        "full_information_count": full_count,
        "language_candidate_bias_blank_count": blank_count,
        "exact_rerun_count": 2 if config["reproducibility"]["exact_rerun"] else 1,
        "total_model_calls_including_rerun": len(observations)
        * (2 if config["reproducibility"]["exact_rerun"] else 1),
        "pair_ids": sorted(config["allocation"]["calibration_pair_ids"]),
        "condition_ids": sorted(
            config["render_condition_selection"]["selected_condition_ids"]
        ),
        "model_revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
        "locked_validation_included": False,
    }
