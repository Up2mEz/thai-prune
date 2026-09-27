"""Pre-locked repeated-target review using preserved S0 outcomes only."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


BOOTSTRAP_SEED = 20260913
BOOTSTRAP_RESAMPLES = 10_000


def _fixed_effect_residuals(rows: list[dict[str, Any]]) -> np.ndarray:
    """Residualize the binary outcome against the frozen S0 main effects."""
    columns = [np.ones(len(rows), dtype=float)]
    for key in ("model_role", "font_id", "font_size", "member", "component_type"):
        levels = sorted({str(row[key]) for row in rows})
        columns.extend(
            np.asarray([str(row[key]) == level for row in rows], dtype=float)
            for level in levels[1:]
        )
    design = np.column_stack(columns)
    outcome = np.asarray([bool(row["primary_exact"]) for row in rows], dtype=float)
    coefficients = np.linalg.lstsq(design, outcome, rcond=None)[0]
    return outcome - design @ coefficients


def _off_diagonal_product_mean(values: np.ndarray) -> float:
    if values.size < 2:
        raise ValueError("a repeated target must have at least two observations")
    numerator = values.sum() ** 2 - np.square(values).sum()
    return float(numerator / (values.size * (values.size - 1)))


def _covariance_components(
    pair_ids: list[str], grouped: dict[str, dict[str, list[float]]]
) -> tuple[float, float, float]:
    same_target = []
    cross_target = []
    for pair_id in pair_ids:
        members = grouped[pair_id]
        if set(members) != {"a", "b"}:
            raise RuntimeError(f"expected members a and b for {pair_id}")
        a = np.asarray(members["a"], dtype=float)
        b = np.asarray(members["b"], dtype=float)
        same_target.append(
            (_off_diagonal_product_mean(a) + _off_diagonal_product_mean(b)) / 2
        )
        cross_target.append(float(np.mean(a[:, None] * b[None, :])))
    within = float(np.mean(same_target))
    cross = float(np.mean(cross_target))
    return within, cross, within - cross


def review_repeated_targets(
    rows: list[dict[str, Any]],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("S0 rows are required")
    if any("budget_id" in row for row in rows):
        raise RuntimeError("review accepts full-information S0 rows only")

    residuals = _fixed_effect_residuals(rows)
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row, residual in zip(rows, residuals, strict=True):
        grouped[str(row["pair_id"])][str(row["member"])].append(float(residual))

    pair_ids = sorted(grouped)
    repeat_counts = {len(values) for members in grouped.values() for values in members.values()}
    if repeat_counts != {8}:
        raise RuntimeError(f"unexpected S0 target repeat counts: {repeat_counts}")

    within, cross, target_excess = _covariance_components(pair_ids, grouped)
    rng = np.random.default_rng(seed)
    boot = np.empty(resamples, dtype=float)
    for index in range(resamples):
        sampled = rng.choice(pair_ids, len(pair_ids), replace=True).tolist()
        boot[index] = _covariance_components(sampled, grouped)[2]

    residual_variance = float(np.mean(np.square(residuals)))
    return {
        "schema_version": 1,
        "scope": "EXISTING_S0_FULL_INFORMATION_ONLY_NO_NEW_MODEL_INFERENCE",
        "pair_count": len(pair_ids),
        "target_count": len(pair_ids) * 2,
        "observations_per_target": 8,
        "fixed_effect_residualization": [
            "MODEL",
            "FONT",
            "FONT_SIZE",
            "MEMBER",
            "COMPONENT",
        ],
        "residual_variance": residual_variance,
        "same_target_off_diagonal_residual_covariance": within,
        "cross_member_same_pair_residual_covariance": cross,
        "target_level_excess_covariance": target_excess,
        "target_level_excess_fraction_of_residual_variance": target_excess
        / residual_variance,
        "pair_cluster_bootstrap": {
            "resamples": resamples,
            "seed": seed,
            "ci_type": "PERCENTILE_95",
            "ci_low": float(np.quantile(boot, 0.025)),
            "median": float(np.quantile(boot, 0.5)),
            "ci_high": float(np.quantile(boot, 0.975)),
            "fraction_at_or_below_zero": float(np.mean(boot <= 0)),
        },
        "structure_comparison": {
            "A": {
                "formula": "(1 | pair_id)",
                "identifiability": "IDENTIFIABLE_BUT_CANNOT_REPRESENT_TARGET_EXCESS_COVARIANCE",
                "convergence_assessment": "LOWER_COMPLEXITY_NOT_A_SUFFICIENT_REASON_TO_IGNORE_OBSERVED_DEPENDENCE",
                "singular_fit_risk": "LOWER_THAN_B_BUT_METHOD_MISSPECIFICATION_RISK_IS_MATERIAL",
                "assessment": "INADEQUATE_FOR_OBSERVED_TARGET_LEVEL_DEPENDENCE",
            },
            "B": {
                "formula": "(1 | pair_id) + (1 | pair_id:member)",
                "identifiability": "SUPPORTED_BY_190_S0_TARGET_LEVELS_WITH_8_REPEATS_EACH",
                "convergence_assessment": "NOT_GUARANTEED_PRELOCKED_REGISTERED_DIAGNOSTICS_REQUIRED",
                "singular_fit_risk": "NONZERO_TWO_NESTED_VARIANCE_COMPONENTS",
                "assessment": "SELECTED_PRIMARY_TARGET_AWARE_STRUCTURE",
                "future_pair_levels": 100,
                "future_target_levels": 200,
                "future_observations_per_target": 32,
            },
        },
        "interpretation": (
            "Positive target-level excess covariance indicates that repeated renders, "
            "models, and future budgets for one target remain correlated beyond the "
            "pair-level intercept. This is a design diagnostic, not compression evidence."
        ),
        "limitations": [
            "The covariance diagnostic uses a linear-probability residual scale, not a locked GLMM fit.",
            "S0 contains FULL information only, so it cannot estimate any budget effect.",
            "A two-level random-intercept GLMM can still be singular; registered diagnostics and fallback govern that event.",
        ],
    }


def build_review(artifact_dir: Path) -> dict[str, Any]:
    manifest = json.loads((artifact_dir / "manifest.json").read_text("utf-8"))
    locked = json.loads((artifact_dir / "locked_set_audit.json").read_text("utf-8"))
    if manifest["call_count"] != 1520 or manifest["pair_count"] != 95:
        raise RuntimeError("unexpected S0 artifact scope")
    if locked["locked_pair_count"] != 0 or not locked["valid"]:
        raise RuntimeError("S0 locked-set audit is not valid")
    rows = [
        json.loads(line)
        for line in (artifact_dir / "raw_outputs.jsonl").read_text("utf-8").splitlines()
    ]
    review = review_repeated_targets(rows)
    review["source_run_id"] = manifest["run_id"]
    review["source_git_sha"] = manifest["git_sha"]
    review["locked_validation_access"] = False
    review["new_model_inference"] = False
    return review
