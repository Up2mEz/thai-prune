"""Registered post-verification analysis for the frozen locked panel."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import chi2

from labbs2026.kaggle import atomic_write_json, atomic_write_text, utc_now
from labbs2026.stage0.interaction_decision import DID_NAMES, classify_interaction
from labbs2026.stage0.paddle_wayu_s0 import classify_output, codepoint_edit_distance, primary_parse
from labbs2026.stage0.paddle_wayu_locked_panel import classify_decoded_output_contract


RESAMPLES = 10_000
SEED = 20260913
BUDGETS = ("B256_FULL", "B196", "B121", "B64")
MODELS = ("BASE", "SPECIALIZED")


def _read_scientific_rows(artifact: Path) -> list[dict[str, Any]]:
    rows = []
    for role in ("base", "specialized"):
        path = artifact / f"sealed/raw_outputs_{role}.jsonl"
        rows.extend(json.loads(line) for line in path.read_text("utf-8").splitlines())
    if len(rows) != 6400 or len({row["call_id"] for row in rows}) != 6400:
        raise RuntimeError("scientific row count or uniqueness mismatch")
    return rows


def derive_outcomes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    derived = []
    for row in rows:
        parsed = primary_parse(row["raw_output"])
        distance = codepoint_edit_distance(parsed, row["target"])
        contract = classify_decoded_output_contract(row["raw_output"])
        if "u_fffd_present" in row and row["u_fffd_present"] != contract["u_fffd_present"]:
            raise RuntimeError("sealed U+FFFD flag does not match decoded raw output")
        if (
            "output_contract_failure" in row
            and row["output_contract_failure"] != contract["output_contract_failure"]
        ):
            raise RuntimeError("sealed output-contract flag does not match decoded raw output")
        if (
            "output_contract_failure_reason" in row
            and row["output_contract_failure_reason"] != contract["output_contract_failure_reason"]
        ):
            raise RuntimeError("sealed output-contract reason does not match decoded raw output")
        derived.append({
            "call_id": row["call_id"],
            "pair_id": row["pair_id"],
            "target_id": f"{row['pair_id']}:{row['member']}",
            "MODEL": row["model_role"],
            "BUDGET": row["budget_id"],
            "FONT": row["font_id"],
            "FONT_SIZE": str(row["font_size"]),
            "MEMBER": row["member"],
            "member": row["member"],
            "COMPONENT": row["component_type"],
            "exact_correct": int(parsed == row["target"]),
            "codepoint_cer": distance / max(1, len(row["target"])),
            "error_category": (
                "output_contract_failure"
                if contract["output_contract_failure"]
                else classify_output(parsed, row["target"], row["opposite_member"])
            ),
            "output_contract_failure": contract["output_contract_failure"],
            "output_contract_failure_reason": contract["output_contract_failure_reason"],
            "u_fffd_present": contract["u_fffd_present"],
            "empty_output": parsed == "",
        })
    return derived


def _pair_bootstrap(values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    indices = rng.integers(0, values.shape[0], size=(RESAMPLES, values.shape[0]))
    return values[indices].mean(axis=1)


def _summary(values: np.ndarray, seed: int = SEED) -> dict[str, float]:
    draws = _pair_bootstrap(values, np.random.default_rng(seed))
    return {
        "estimate": float(values.mean()),
        "ci_low": float(np.quantile(draws, 0.025)),
        "ci_high": float(np.quantile(draws, 0.975)),
        "pair_cluster_count": int(values.shape[0]),
    }


def full_validity(rows: list[dict[str, Any]], engineering_manifest: dict[str, Any]) -> dict[str, Any]:
    full = [row for row in rows if row["BUDGET"] == "B256_FULL"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in full:
        grouped[(row["MODEL"], row["pair_id"])].append(row)
    by_model = {}
    criteria = []
    for model in MODELS:
        pair_ids = sorted(pair_id for role, pair_id in grouped if role == model)
        values = np.asarray([
            np.mean([item["exact_correct"] for item in grouped[(model, pair_id)]])
            for pair_id in pair_ids
        ])
        if len(values) != 100 or any(len(grouped[(model, pair_id)]) != 8 for pair_id in pair_ids):
            raise RuntimeError("FULL pair aggregation mismatch")
        accuracy = _summary(values)
        model_rows = [row for row in full if row["MODEL"] == model]
        contract_rate = float(np.mean([row["output_contract_failure"] for row in model_rows]))
        by_model[model] = {
            "exact_accuracy": accuracy,
            "output_contract_failure_rate": contract_rate,
        }
        criteria.extend([
            accuracy["ci_low"] >= 0.20,
            contract_rate <= 0.01,
        ])
    engineering_ok = (
        engineering_manifest["call_count"] == 6400
        and engineering_manifest["unique_call_count"] == 6400
        and engineering_manifest["unauthorized_or_out_of_workload_locked_pair_count"] == 0
        and engineering_manifest["token_count_distribution"]
        == {"64": 1600, "121": 1600, "196": 1600, "256": 1600}
    )
    criteria.append(engineering_ok)
    passed = all(criteria)
    return {
        "status": "PASS" if passed else "FAIL",
        "pass_definition": "OVERALL_PRIMARY_MODEL_BY_BUDGET_ANALYSIS_IS_MEASUREMENT_INTERPRETABLE_UNDER_REGISTERED_PLANNING_CRITERION",
        "by_model": by_model,
        "engineering_contract_valid": engineering_ok,
        "component_capacity_is_not_implied": True,
        "primary_analysis_interpretable": passed,
    }


def _pair_cells(rows: list[dict[str, Any]], metric: str) -> dict[tuple[str, str, str], float]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["pair_id"], row["MODEL"], row["BUDGET"])].append(float(row[metric]))
    result = {}
    for key, values in grouped.items():
        if len(values) != 8:
            raise RuntimeError(f"pair/model/budget cell count mismatch: {key}")
        result[key] = float(np.mean(values))
    return result


def _holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda name: p_values[name])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for index, name in enumerate(ordered):
        running = max(running, min(1.0, (total - index) * p_values[name]))
        adjusted[name] = running
    return {name: adjusted[name] for name in DID_NAMES}


def did_analysis(rows: list[dict[str, Any]], metric: str = "exact_correct") -> dict[str, Any]:
    cells = _pair_cells(rows, metric)
    pair_ids = sorted({row["pair_id"] for row in rows})
    budget_map = {"DID_196": "B196", "DID_121": "B121", "DID_64": "B64"}
    matrix = np.empty((len(pair_ids), 3), dtype=float)
    model_changes: dict[str, dict[str, np.ndarray]] = {model: {} for model in MODELS}
    for column, name in enumerate(DID_NAMES):
        budget = budget_map[name]
        for model in MODELS:
            model_changes[model][name] = np.asarray([
                cells[(pair_id, model, budget)] - cells[(pair_id, model, "B256_FULL")]
                for pair_id in pair_ids
            ])
        matrix[:, column] = model_changes["SPECIALIZED"][name] - model_changes["BASE"][name]
    rng = np.random.default_rng(SEED)
    indices = rng.integers(0, len(pair_ids), size=(RESAMPLES, len(pair_ids)))
    boot = matrix[indices].mean(axis=1)
    estimates = matrix.mean(axis=0)
    raw_p = {}
    contrasts = {}
    for index, name in enumerate(DID_NAMES):
        centered = boot[:, index] - estimates[index]
        raw_p[name] = float((1 + np.sum(np.abs(centered) >= abs(estimates[index]))) / (RESAMPLES + 1))
        contrasts[name] = {
            "estimate": float(estimates[index]),
            "ci_low": float(np.quantile(boot[:, index], 0.025)),
            "ci_high": float(np.quantile(boot[:, index], 0.975)),
            "bootstrap_p_value": raw_p[name],
            "ci_is_holm_adjusted": False,
            "model_specific_change_from_full": {
                model: _summary(model_changes[model][name], SEED + index + (model == "SPECIALIZED") * 100)
                for model in MODELS
            },
        }
    adjusted = _holm(raw_p)
    for name in DID_NAMES:
        contrasts[name]["holm_adjusted_p_value"] = adjusted[name]
    covariance = np.cov(boot, rowvar=False, ddof=1)
    fallback = {"status": "ESTIMABLE"}
    try:
        if not np.all(np.isfinite(covariance)) or np.linalg.matrix_rank(covariance) < 3:
            raise np.linalg.LinAlgError("bootstrap covariance is not invertible")
        statistic = float(estimates @ np.linalg.inv(covariance) @ estimates)
        fallback.update({"wald_statistic": statistic, "df": 3, "p_value": float(chi2.sf(statistic, 3))})
    except np.linalg.LinAlgError:
        fallback = {"status": "FALLBACK_GLOBAL_TEST_NOT_ESTIMABLE"}
    return {
        "metric": metric,
        "pair_cluster_count": len(pair_ids),
        "bootstrap_resamples": RESAMPLES,
        "bootstrap_seed": SEED,
        "contrasts": contrasts,
        "bootstrap_covariance": covariance.tolist(),
        "registered_glmm_fallback_global_test": fallback,
    }


def component_descriptives(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    components = sorted({row["COMPONENT"] for row in rows})
    for component in components:
        selected = [row for row in rows if row["COMPONENT"] == component]
        cells = _pair_cells(selected, "exact_correct")
        pair_ids = sorted({row["pair_id"] for row in selected})
        for model in MODELS:
            for budget in BUDGETS:
                values = np.asarray([cells[(pair_id, model, budget)] for pair_id in pair_ids])
                output.append({
                    "component": component,
                    "MODEL": model,
                    "BUDGET": budget,
                    "role": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
                    **_summary(values),
                })
    return output


def write_analysis_inputs(artifact: Path, output_dir: Path) -> dict[str, Any]:
    verification = json.loads((artifact.parents[2] / "verification/verification.json").read_text("utf-8"))
    if verification["verification_status"] != "VERIFIED" or verification["scientific_outputs_opened"]:
        raise RuntimeError("local sealed-artifact verification did not authorize unsealing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite analysis: {output_dir}")
    output_dir.mkdir(parents=True)
    rows = derive_outcomes(_read_scientific_rows(artifact))
    engineering = json.loads((artifact / "engineering/execution_manifest.json").read_text("utf-8"))
    validity = full_validity(rows, engineering)
    fieldnames = [
        "call_id", "pair_id", "target_id", "MODEL", "BUDGET", "FONT",
        "FONT_SIZE", "MEMBER", "member", "COMPONENT", "exact_correct", "codepoint_cer",
        "error_category", "output_contract_failure", "output_contract_failure_reason",
        "u_fffd_present", "empty_output",
    ]
    with (output_dir / "analysis_rows.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    atomic_write_json(output_dir / "full_validity.json", validity)
    state = {
        "schema_version": 1,
        "scientific_outputs_unsealed_after_local_verification": True,
        "full_validity": validity["status"],
        "primary_analysis_interpretable": validity["primary_analysis_interpretable"],
        "created_at_utc": utc_now(),
    }
    atomic_write_json(output_dir / "analysis_state.json", state)
    return state


def finalize_analysis(analysis_dir: Path, glmm_path: Path | None) -> dict[str, Any]:
    validity = json.loads((analysis_dir / "full_validity.json").read_text("utf-8"))
    with (analysis_dir / "analysis_rows.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["exact_correct"] = int(row["exact_correct"])
        row["codepoint_cer"] = float(row["codepoint_cer"])
        row["output_contract_failure"] = row["output_contract_failure"] == "True"
    if validity["status"] != "PASS":
        result = {
            "schema_version": 1,
            "status": "NOT_INTERPRETABLE_FULL_VALIDITY_FAILED",
            "full_validity": validity,
            "primary_analysis_run": False,
            "terminal_state": "HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL",
        }
        atomic_write_json(analysis_dir / "registered_analysis.json", result)
        return result
    exact = did_analysis(rows, "exact_correct")
    cer = did_analysis(rows, "codepoint_cer")
    if glmm_path is None or not glmm_path.is_file():
        raise RuntimeError("registered GLMM result is required after FULL validity PASS")
    glmm = json.loads(glmm_path.read_text("utf-8"))
    if glmm["diagnostics_pass"]:
        omnibus = glmm["omnibus"]
        estimator = "REGISTERED_BINOMIAL_LOGIT_GLMM_LRT"
    else:
        fallback = exact["registered_glmm_fallback_global_test"]
        if fallback["status"] != "ESTIMABLE":
            decision = "PRIMARY_INTERACTION_NOT_ESTIMABLE"
            omnibus = fallback
        else:
            omnibus = fallback
            decision = classify_interaction(
                fallback["p_value"],
                {name: exact["contrasts"][name]["estimate"] for name in DID_NAMES},
                {name: exact["contrasts"][name]["holm_adjusted_p_value"] for name in DID_NAMES},
            )
        estimator = "PRE_REGISTERED_PAIR_CLUSTERED_FALLBACK_AFTER_GLMM_FAILURE"
    if glmm["diagnostics_pass"]:
        decision = classify_interaction(
            omnibus["p_value"],
            {name: exact["contrasts"][name]["estimate"] for name in DID_NAMES},
            {name: exact["contrasts"][name]["holm_adjusted_p_value"] for name in DID_NAMES},
        )
    result = {
        "schema_version": 1,
        "status": decision,
        "full_validity": validity,
        "primary_global_test": omnibus,
        "primary_estimator": estimator,
        "glmm": glmm,
        "exact_transcription_dids": exact,
        "cer_sensitivity": cer,
        "component_results": component_descriptives(rows),
        "component_role": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
        "mechanism_scope": "CONTROLLED_BICUBIC_INPUT_RESOLUTION_REDUCTION",
        "not_evidence_for": [
            "POST_ENCODER_TOKEN_PRUNING", "TOKEN_MERGING",
            "COMPRESSION_ROBUSTNESS_IN_GENERAL", "CAUSAL_EFFECT_OF_WAYU_TRAINING_DATASET",
            "ATTENTION_OR_REPRESENTATION_MECHANISM", "CONFIRMATORY_COMPONENT_EFFECTS",
        ],
        "nonsignificant_is_equivalence": False,
        "terminal_state": "HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL",
    }
    atomic_write_json(analysis_dir / "registered_analysis.json", result)
    return result
