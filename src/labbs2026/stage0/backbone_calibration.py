"""Pre-registered Qwen3.5 Stage 0 backbone-capacity audit.

This workflow is deliberately limited to the already exposed calibration split.
It never reads locked-validation stimuli and it contains no compression path.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import shutil
import statistics
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml

from labbs2026.adapters.factory import validate_model_config
from labbs2026.kaggle import (
    _check_remote_ref,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    cuda_preflight,
    load_runtime,
    parse_kaggle_status,
    render_worker,
    sha256_file,
    utc_now,
    write_failure,
)
from labbs2026.preflight import inspect_repository
from labbs2026.stage0.bundle import extract_and_verify_calibration_bundle
from labbs2026.stage0.kaggle_backend import _checksums
from labbs2026.stage0.margin_diagnostic import (
    _cluster_bootstrap,
    _enrich_image_gain,
    _mean,
    _paired_pair_contrast,
    _positive_rate,
    _run_pass,
)
from labbs2026.stage0.metrics import compute_stage0_metrics
from labbs2026.stage0.run import calibration_readiness_issues, make_observation_plan
from labbs2026.step3 import environment_record


KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-qwen3-5-stage-0-backbone-audit",
    "title": "LabBS2026 Qwen3.5 Stage 0 Backbone Audit",
    "code_file": "worker.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": [],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def backbone_preflight(root: Path, audit_path: Path, runtime_path: Path) -> dict[str, Any]:
    root = root.resolve()
    audit = _load_yaml(audit_path)
    frozen = audit["frozen_inputs"]
    checks: dict[str, dict[str, Any]] = {}
    repository = inspect_repository(root)
    checks["repository"] = {
        "ok": repository.valid,
        "git_commit": repository.git_commit,
        "git_clean": repository.git_clean,
        "missing_paths": list(repository.missing_paths),
    }
    design_path = root / frozen["calibration_design"]
    design = _load_yaml(design_path)
    review = _load_json(root / design["human_review_record"])
    readiness = calibration_readiness_issues(design, review)
    checks["human_frozen_calibration"] = {"ok": not readiness, "issues": readiness}
    expected_hashes = {
        frozen["calibration_input_bundle"]: frozen["calibration_input_bundle_sha256"],
        frozen["prompt_parser"]: frozen["prompt_parser_sha256"],
    }
    observed_hashes = {
        path: sha256_file(root / path) if (root / path).is_file() else None
        for path in expected_hashes
    }
    checks["frozen_input_hashes"] = {
        "ok": observed_hashes == expected_hashes,
        "expected": expected_hashes,
        "observed": observed_hashes,
    }
    runtime = load_runtime(runtime_path)
    model = _load_yaml(root / frozen["model_config"])
    try:
        adapter = validate_model_config(model)
        runtime_issues = []
    except (KeyError, TypeError, ValueError) as exc:
        adapter, runtime_issues = None, [str(exc)]
    contract = runtime.get("evidence_environment_contract", {})
    model_runtime = runtime.get("model_runtime", {})
    for key in ("device", "dtype", "attention_implementation"):
        if model_runtime.get(key) != model["model"].get(key):
            runtime_issues.append(f"RUNTIME_MODEL_{key.upper()}_MISMATCH")
    if contract.get("transformers") != model["model"].get("required_transformers_version"):
        runtime_issues.append("TRANSFORMERS_VERSION_MISMATCH")
    override = root / runtime["uv"]["qwen35_override_lock"]
    if "transformers==5.12.0" not in override.read_text("utf-8"):
        runtime_issues.append("QWEN35_OVERRIDE_NOT_PINNED")
    checks["model_and_runtime_contract"] = {
        "ok": adapter == "qwen35" and not runtime_issues,
        "adapter": adapter,
        "issues": runtime_issues,
    }
    with tempfile.TemporaryDirectory(prefix="labbs-qwen35-preflight-") as temporary:
        extracted = Path(temporary) / "input"
        manifest = extract_and_verify_calibration_bundle(
            root / frozen["calibration_input_bundle"],
            extracted,
            frozen["calibration_input_bundle_sha256"],
        )
        pairs = _load_json(extracted / "resolved_pairs.json")
        renders = _load_json(extracted / "render_manifest.json")
        prompt = _load_yaml(root / frozen["prompt_parser"])["prompt_template"]
        observations = make_observation_plan(design, pairs, renders, prompt)
    calibration_ids = set(design["allocation"]["calibration_pair_ids"])
    locked_ids = set(design["allocation"]["locked_validation_pair_ids"])
    component_counts = Counter(pair["component_type"] for pair in pairs)
    checks["calibration_bundle_and_workload"] = {
        "ok": manifest["allocation_sha256"] == frozen["pair_allocation_sha256"]
        and len(observations) == 1000
        and {row["pair_id"] for row in observations} == calibration_ids
        and not ({row["pair_id"] for row in observations} & locked_ids)
        and sorted(component_counts.values()) == [20, 20, 20, 20, 20],
        "observation_count": len(observations),
        "component_pair_counts": dict(sorted(component_counts.items())),
        "locked_pair_count": len({row["pair_id"] for row in observations} & locked_ids),
    }
    smoke, full = audit["engineering_smoke"], audit["calibration"]
    prohibitions = audit["prohibitions"]
    checks["authorization_and_workload"] = {
        "ok": audit.get("status") == "FROZEN_QWEN35_BACKBONE_CALIBRATION_AUTHORIZED"
        and audit.get("authorization_scope") == "ALREADY_EXPOSED_CALIBRATION_PAIRS_ONLY"
        and all(value is False for value in prohibitions.values())
        and smoke.get("total_calls") == 40
        and full.get("total_calls") == 2000
        and full.get("exact_run_count") == 2,
        "prohibitions": prohibitions,
    }
    checks["kernel_metadata"] = {
        "ok": _load_json(root / "infra/kaggle/stage0-qwen35-kernel-metadata.json")
        == KERNEL_METADATA
    }
    source = runtime["source"]
    remote_sha, remote_error = _check_remote_ref(
        root, source["repository_url"], source["remote_ref"]
    )
    checks["remote_ref"] = {
        "ok": remote_sha is not None and remote_sha == repository.git_commit,
        "local_sha": repository.git_commit,
        "remote_sha": remote_sha,
        "remote_ref": source["remote_ref"],
        "error": remote_error,
    }
    kaggle_version = subprocess.run(
        ["kaggle", "--version"], cwd=root, capture_output=True, text=True
    )
    kaggle_auth = subprocess.run(
        ["kaggle", "kernels", "list", "--mine", "--page-size", "1", "-v"],
        cwd=root, capture_output=True, text=True,
    )
    checks["kaggle_cli_and_auth"] = {
        "ok": kaggle_version.returncode == 0 and kaggle_auth.returncode == 0,
        "version": kaggle_version.stdout.strip(),
    }
    return {
        "schema_version": 1,
        "valid": all(check.get("ok") is True for check in checks.values()),
        "checks": checks,
    }


def make_backbone_spec(
    root: Path, audit_path: Path, runtime_path: Path, git_sha: str
) -> dict[str, Any]:
    audit = _load_yaml(audit_path)
    frozen = audit["frozen_inputs"]
    runtime = load_runtime(runtime_path)
    paths = {
        "audit_config_path": audit_path.relative_to(root).as_posix(),
        "config_path": frozen["calibration_design"],
        "runtime_path": runtime_path.relative_to(root).as_posix(),
        "model_config_path": frozen["model_config"],
        "prompt_config_path": frozen["prompt_parser"],
        "bundle_path": frozen["calibration_input_bundle"],
        "rationale_path": frozen["rationale"],
        "override_lock_path": frozen["dependency_override_lock"],
    }
    hashes = {
        key.replace("_path", "_sha256"): sha256_file(root / value)
        for key, value in paths.items()
    }
    return {
        "schema_version": 1,
        "run_type": "STAGE0_QWEN35_BACKBONE_CALIBRATION",
        "run_id": f"kaggle-qwen35-stage0-{git_sha[:12]}-{hashes['audit_config_sha256'][:8]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        **paths,
        **hashes,
        "bundle_sha256": frozen["calibration_input_bundle_sha256"],
        "allocation_sha256": frozen["pair_allocation_sha256"],
        "smoke": audit["engineering_smoke"],
        "calibration": audit["calibration"],
        "adequacy": audit["measurement_adequacy"],
        "requested_accelerator": runtime["accelerator"],
        "environment_contract": runtime["evidence_environment_contract"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "qwen35_override_lock": runtime["uv"]["qwen35_override_lock"],
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "worker_template_path": "infra/kaggle/qwen35_backbone_worker.py",
        "kernel_id": KERNEL_METADATA["id"],
        "locked_validation_authorized": False,
        "gate_0_status": "NOT_RUN",
        "stage_1a_status": "BLOCKED",
        "compression_status": "NOT_RUN",
        "created_at_utc": utc_now(),
    }


def prepare_backbone_staging(
    root: Path, audit_path: Path, runtime_path: Path
) -> dict[str, Any]:
    preflight = backbone_preflight(root, audit_path, runtime_path)
    if not preflight["valid"]:
        raise RuntimeError("Qwen3.5 backbone preflight failed")
    git_sha = preflight["checks"]["repository"]["git_commit"]
    spec = make_backbone_spec(root, audit_path, runtime_path, git_sha)
    run_dir = root / "runs" / "kaggle" / spec["run_id"]
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / spec["worker_template_path"]
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    shutil.copyfile(
        root / "infra/kaggle/stage0-qwen35-kernel-metadata.json",
        staging / "kernel-metadata.json",
    )
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", preflight)
    return {
        "run_id": spec["run_id"], "run_dir": str(run_dir),
        "staging_dir": str(staging), "submit_command": build_submit_command(staging),
    }


def _visual_contract(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    metadata = row["visual_stage_metadata"]
    fields = (
        "original_image_shape", "preprocessed_image_shape", "image_grid_thw",
        "premerge_patch_count", "runtime_premerge_patch_count",
        "llm_visual_token_count", "input_image_token_count",
        "runtime_vision_output_count", "runtime_llm_input_position_count",
    )
    return all(metadata.get(field) == expected.get(field) for field in fields)


def select_smoke_observations(
    observations: list[dict[str, Any]], smoke: dict[str, Any]
) -> list[dict[str, Any]]:
    """Apply only the predeclared IDs/condition; ordering stays deterministic."""

    smoke_ids = set(smoke["pair_ids"])
    selected = [
        row for row in observations
        if row["pair_id"] in smoke_ids
        and (
            row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
            or row["condition_id"] == smoke["condition_id"]
        )
    ]
    return sorted(selected, key=lambda row: row["observation_id"])


def _smoke_acceptance(
    first: list[dict[str, Any]], second: list[dict[str, Any]], expected: dict[str, Any]
) -> dict[str, Any]:
    one = {row["observation_id"]: row for row in first}
    two = {row["observation_id"]: row for row in second}
    paired = [(one[key], two[key]) for key in sorted(one)] if set(one) == set(two) else []
    rows = first + second
    criteria = {
        "call_completion": len(first) == len(second) == 20,
        "one_exact_canonical_token": all(
            len(row["generated_token_ids"]) == 1
            and row["generated_token_ids"][0] in (32, 33)
            and row["parse_status"] == "PARSED"
            and row["output_contract_conformance"] is True
            for row in rows
        ),
        "generate_direct_logits_exact": all(row["generate_direct_exact"] is True for row in rows),
        "binary_argmax_matches_generation": all(
            row["binary_prediction"] == ("A" if row["logit_A"] >= row["logit_B"] else "B")
            for row in rows
        ),
        "visual_accounting_exact": all(_visual_contract(row, expected) for row in rows),
        "exact_rerun_reproducibility": bool(paired) and len(paired) == 20 and all(
            a["raw_output"] == b["raw_output"]
            and a["generated_token_ids"] == b["generated_token_ids"]
            and a["logit_A"] == b["logit_A"]
            and a["logit_B"] == b["logit_B"]
            and a["visual_stage_metadata"] == b["visual_stage_metadata"]
            for a, b in paired
        ),
    }
    return {
        "schema_version": 1,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "scientific_use": "FORBIDDEN_ENGINEERING_SMOKE_ONLY",
        "criteria": criteria,
        "completed_calls": len(rows),
        "planned_calls": 40,
    }


def _exact_rerun(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> dict[str, Any]:
    one = {row["observation_id"]: row for row in first}
    two = {row["observation_id"]: row for row in second}
    same_ids = set(one) == set(two) and len(one) == 1000
    mismatches: list[str] = []
    if same_ids:
        for key in sorted(one):
            a, b = one[key], two[key]
            if not (
                a["raw_output"] == b["raw_output"]
                and a["generated_token_ids"] == b["generated_token_ids"]
                and a["logit_A"] == b["logit_A"]
                and a["logit_B"] == b["logit_B"]
                and a["visual_stage_metadata"] == b["visual_stage_metadata"]
            ):
                mismatches.append(key)
    return {
        "schema_version": 1,
        "status": "EXACT" if same_ids and not mismatches else "MISMATCH",
        "exact_reruns_pooled": False,
        "observation_count_each": [len(first), len(second)],
        "mismatch_count": len(mismatches),
        "first_mismatch_ids": mismatches[:20],
    }


def execute_remote_backbone(spec_path: Path) -> None:
    spec = _load_json(spec_path)
    source = Path.cwd()
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    phase = "cuda_preflight"
    started = time.perf_counter()
    try:
        runtime = load_runtime(source / spec["runtime_path"])
        gpu = cuda_preflight(spec["requested_accelerator"])
        phase = "bundle_verification"
        input_dir = Path("/tmp/labbs2026-qwen35-stage0-input")
        bundle = extract_and_verify_calibration_bundle(
            source / spec["bundle_path"], input_dir, spec["bundle_sha256"]
        )
        if bundle["allocation_sha256"] != spec["allocation_sha256"]:
            raise RuntimeError("bundle allocation differs from frozen calibration")
        design = _load_yaml(source / spec["config_path"])
        prompt = _load_yaml(source / spec["prompt_config_path"])["prompt_template"]
        pairs = _load_json(input_dir / "resolved_pairs.json")
        renders = _load_json(input_dir / "render_manifest.json")
        observations = make_observation_plan(design, pairs, renders, prompt)
        calibration_ids = set(design["allocation"]["calibration_pair_ids"])
        locked_ids = set(design["allocation"]["locked_validation_pair_ids"])
        observed_ids = {row["pair_id"] for row in observations}
        if len(observations) != 1000 or observed_ids != calibration_ids or observed_ids & locked_ids:
            raise RuntimeError("remote plan is not the exact isolated 100-pair calibration plan")
        render_by_key = {(row["pair_id"], row["condition_id"]): row for row in renders}
        smoke = spec["smoke"]
        smoke_obs = select_smoke_observations(observations, smoke)
        if len(smoke_obs) != 20:
            raise RuntimeError("engineering smoke must contain exactly 20 observations")
        model_config = _load_yaml(source / spec["model_config_path"])
        expected_visual = model_config["expected_full_information_processing"]
        phase = "engineering_smoke"
        smoke_root = artifact_dir / "engineering_smoke"
        smoke_runs: list[list[dict[str, Any]]] = []
        for index in (1, 2):
            run = _run_pass(
                spec=spec, source=source, input_dir=input_dir, runtime=runtime,
                output_dir=smoke_root / f"exact_run_{index}", observations=smoke_obs,
                render_by_key=render_by_key, verify_direct_forward=True,
                role="QWEN35_ENGINEERING_SMOKE_NOT_SCIENTIFIC_EVIDENCE",
            )
            smoke_runs.append(_jsonl(run / "decision_margins.jsonl"))
            gc.collect()
            import torch
            torch.cuda.empty_cache()
        acceptance = _smoke_acceptance(smoke_runs[0], smoke_runs[1], expected_visual)
        atomic_write_json(smoke_root / "acceptance.json", acceptance)
        if acceptance["status"] != "PASS":
            raise RuntimeError("engineering smoke failed; full calibration was not started")
        phase = "open_calibration_exact_runs"
        calibration_root = artifact_dir / "open_calibration"
        full_runs: list[list[dict[str, Any]]] = []
        for index in (1, 2):
            run = _run_pass(
                spec=spec, source=source, input_dir=input_dir, runtime=runtime,
                output_dir=calibration_root / f"exact_run_{index}", observations=observations,
                render_by_key=render_by_key, verify_direct_forward=False,
                role="QWEN35_STAGE0_OPEN_CALIBRATION_FULL_INFORMATION",
            )
            enriched = _enrich_image_gain(_jsonl(run / "decision_margins.jsonl"))
            _write_jsonl(run / "image_gain_records.jsonl", enriched)
            full_runs.append(enriched)
            gc.collect()
            import torch
            torch.cuda.empty_cache()
        rerun = _exact_rerun(full_runs[0], full_runs[1])
        atomic_write_json(calibration_root / "exact_rerun.json", rerun)
        if rerun["status"] != "EXACT":
            raise RuntimeError("exact full calibration rerun mismatch")
        atomic_write_json(artifact_dir / "runtime.json", {
            "schema_version": 1, "run_id": spec["run_id"], "gpu_preflight": gpu,
            "environment": environment_record(),
            "frozen_environment_contract": spec["environment_contract"],
            "total_submission_seconds": time.perf_counter() - started,
        })
        atomic_write_json(artifact_dir / "submission_manifest.json", {
            "schema_version": 1, "run_id": spec["run_id"],
            "run_status": "VALID_QWEN35_OPEN_CALIBRATION",
            "git_sha": spec["git_sha"], "audit_config_sha256": spec["audit_config_sha256"],
            "model_config_sha256": spec["model_config_sha256"],
            "dependency_override_sha256": spec["override_lock_sha256"],
            "engineering_smoke_status": "PASS", "engineering_smoke_calls": 40,
            "open_calibration_calls": 2000, "exact_rerun_status": "EXACT",
            "locked_validation_pair_count_exposed_to_model": 0,
            "gate_0_status": "NOT_RUN", "stage_1a_status": "BLOCKED",
            "compression_status": "NOT_RUN",
        })
        atomic_write_text(artifact_dir / "checksums.sha256", _checksums(artifact_dir))
        atomic_write_json(artifact_dir / "SUCCESS.json", {
            "schema_version": 1, "run_id": spec["run_id"],
            "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
        })
    except BaseException as exc:
        message = str(exc).lower()
        classification = (
            "QWEN35_4B_T4_INFEASIBLE"
            if "out of memory" in message or "cuda error: out of memory" in message
            else "QWEN35_EXECUTION_FAILURE"
        )
        atomic_write_json(artifact_dir / "capacity_classification.json", {
            "schema_version": 1, "classification": classification, "phase": phase,
        })
        write_failure(artifact_dir, spec["run_id"], phase, exc)
        if (artifact_dir / "SUCCESS.json").exists():
            (artifact_dir / "SUCCESS.json").unlink()
        raise


def _estimate(
    rows: list[dict[str, Any]], statistic: Callable[[list[dict[str, Any]]], float],
    *, seed: int, resamples: int, confidence: float,
) -> dict[str, Any]:
    return _cluster_bootstrap(
        rows, statistic, seed=seed, resamples=resamples, confidence=confidence
    )


def _group_estimates(
    rows: list[dict[str, Any]], key: str, outcome: str,
    *, seed: int, resamples: int, confidence: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for value in sorted({str(row.get(key)) for row in rows}):
        subset = [row for row in rows if str(row.get(key)) == value]
        statistic = (
            (lambda data: sum(bool(row[outcome]) for row in data) / len(data))
            if outcome == "binary_correct"
            else _mean(outcome)
        )
        result[value] = _estimate(
            subset, statistic, seed=seed, resamples=resamples, confidence=confidence
        )
    return result


def analyze_backbone_artifacts(
    artifact_dir: Path, output_dir: Path, audit_path: Path
) -> dict[str, Any]:
    audit = _load_yaml(audit_path)
    primary = _jsonl(artifact_dir / "open_calibration/exact_run_1/image_gain_records.jsonl")
    rerun_rows = _jsonl(artifact_dir / "open_calibration/exact_run_2/image_gain_records.jsonl")
    rerun = _load_json(artifact_dir / "open_calibration/exact_rerun.json")
    if len(primary) != 1000 or len(rerun_rows) != 1000:
        raise RuntimeError("unexpected Qwen3.5 calibration grain")
    full = [row for row in primary if row["control_type"] == "FULL_INFORMATION"]
    blanks = [row for row in primary if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"]
    if len(full) != 800 or len(blanks) != 200:
        raise RuntimeError("expected 800 full and 200 matched blank observations")
    calibration = audit["calibration"]
    seed = int(calibration["cluster_bootstrap_seed"])
    resamples = int(calibration["cluster_bootstrap_resamples"])
    confidence = float(calibration["confidence_level"])
    metric_rows = [{**row, "is_correct": row["binary_correct"]} for row in primary]
    registered = compute_stage0_metrics(
        metric_rows, bootstrap_seed=seed,
        bootstrap_resamples=resamples, confidence_level=confidence,
    )
    by_component: dict[str, Any] = {}
    member_rows: list[dict[str, Any]] = []
    condition_rows: list[dict[str, Any]] = []
    rules = audit["measurement_adequacy"]
    for component in sorted({row["component_type"] for row in full}):
        subset = [row for row in full if row["component_type"] == component]
        accuracy = _estimate(
            subset, lambda data: sum(bool(row["binary_correct"]) for row in data) / len(data),
            seed=seed, resamples=resamples, confidence=confidence,
        )
        image_gain = _estimate(
            subset, _mean("image_gain"), seed=seed, resamples=resamples, confidence=confidence
        )
        members = _group_estimates(
            subset, "displayed_member", "binary_correct",
            seed=seed, resamples=resamples, confidence=confidence,
        )
        reasons: list[str] = []
        if accuracy["estimate"] <= float(rules["component_inadequate_if_accuracy_at_or_below"]):
            reasons.append("ACCURACY_HEADROOM_AT_OR_BELOW_SESOI")
        if rules["component_inadequate_if_ci_low_at_or_below_chance"] and accuracy["ci_low"] <= float(rules["chance_accuracy"]):
            reasons.append("ACCURACY_CI_REACHES_CHANCE")
        if reasons:
            status = "INADEQUATE"
        elif (
            min(value["estimate"] for value in members.values())
            > float(rules["adequate_requires_both_member_accuracies_above"])
            and (not rules["adequate_requires_image_gain_ci_low_above_zero"] or image_gain["ci_low"] > 0)
            and rerun["status"] == "EXACT"
        ):
            status = "ADEQUATE"
        else:
            status = "BORDERLINE"
            if min(value["estimate"] for value in members.values()) <= float(rules["adequate_requires_both_member_accuracies_above"]):
                reasons.append("MEMBER_ASYMMETRY_OR_LOW_MEMBER_ACCURACY")
            if image_gain["ci_low"] <= 0:
                reasons.append("IMAGE_GAIN_NOT_CLEARED_ABOVE_ZERO")
        by_component[component] = {
            "accuracy": accuracy,
            "image_gain": image_gain,
            "image_gain_positive_rate": _estimate(
                subset, _positive_rate("image_gain"), seed=seed,
                resamples=resamples, confidence=confidence,
            ),
            "member_accuracy": members,
            "adequacy_status": status,
            "reasons": reasons,
            "paired_effects": {
                "size_96_minus_72_accuracy": _paired_pair_contrast(
                    subset, outcome="binary_correct", grouping="font_size", positive=96,
                    negative=72, seed=seed, resamples=resamples, confidence=confidence,
                ),
                "serif_minus_sans_accuracy": _paired_pair_contrast(
                    subset, outcome="binary_correct", grouping="font_id",
                    positive="noto_serif_thai_regular", negative="noto_sans_thai_regular",
                    seed=seed, resamples=resamples, confidence=confidence,
                ),
                "member_a_minus_b_image_gain": _paired_pair_contrast(
                    subset, outcome="image_gain", grouping="displayed_member",
                    positive="a", negative="b", seed=seed, resamples=resamples,
                    confidence=confidence,
                ),
            },
        }
        for member, estimate in members.items():
            member_rows.append({"component": component, "member": member, "accuracy": estimate})
        for condition in sorted({row["condition_id"] for row in subset}):
            condition_subset = [row for row in subset if row["condition_id"] == condition]
            condition_rows.append({
                "component": component, "condition_id": condition,
                "accuracy": _estimate(
                    condition_subset,
                    lambda data: sum(bool(row["binary_correct"]) for row in data) / len(data),
                    seed=seed, resamples=resamples, confidence=confidence,
                ),
                "image_gain": _estimate(
                    condition_subset, _mean("image_gain"), seed=seed,
                    resamples=resamples, confidence=confidence,
                ),
            })
    blank_prior = {
        "overall": {
            "position_A_minus_B_margin": _estimate(
                blanks, _mean("position_margin"), seed=seed,
                resamples=resamples, confidence=confidence,
            ),
            "position_A_choice_rate": _estimate(
                blanks, lambda data: sum(row["binary_prediction"] == "A" for row in data) / len(data),
                seed=seed, resamples=resamples, confidence=confidence,
            ),
        },
        "by_orientation": _group_estimates(
            blanks, "orientation", "position_margin", seed=seed,
            resamples=resamples, confidence=confidence,
        ),
        "by_candidate_a_lexical_status": _group_estimates(
            blanks, "candidate_a_lexical_status", "position_margin", seed=seed,
            resamples=resamples, confidence=confidence,
        ),
        "by_component": _group_estimates(
            blanks, "component_type", "position_margin", seed=seed,
            resamples=resamples, confidence=confidence,
        ),
    }
    statuses = [value["adequacy_status"] for value in by_component.values()]
    decision = (
        "SWITCH_TO_QWEN35_PRIMARY_BACKBONE"
        if statuses and all(value == "ADEQUATE" for value in statuses)
        else "BORDERLINE_REQUIRES_HUMAN_REVIEW"
        if "INADEQUATE" not in statuses
        else "MEASUREMENT_REDESIGN_REQUIRED"
    )
    report = {
        "schema_version": 1,
        "evidence_status": "OPEN_CALIBRATION_ONLY_NOT_LOCKED_VALIDATION",
        "independent_unit": "pair_id",
        "pair_count": 100,
        "locked_pair_count": 0,
        "exact_reruns_pooled": False,
        "primary_run": "exact_run_1",
        "reproducibility": rerun,
        "registered_metrics": registered,
        "overall": {
            "accuracy": _estimate(
                full, lambda data: sum(bool(row["binary_correct"]) for row in data) / len(data),
                seed=seed, resamples=resamples, confidence=confidence,
            ),
            "image_gain": _estimate(
                full, _mean("image_gain"), seed=seed,
                resamples=resamples, confidence=confidence,
            ),
            "image_gain_median": statistics.median(row["image_gain"] for row in full),
        },
        "per_component": by_component,
        "blank_position_prior": blank_prior,
        "member_results": member_rows,
        "condition_results": condition_rows,
        "parser_failure_count": sum(row["parse_status"] != "PARSED" for row in primary),
        "visual_token_counts": dict(Counter(row["llm_visual_token_count"] for row in primary)),
        "planning_recommendation": decision,
        "gate_0_status": "NOT_RUN",
        "stage_1a_status": "BLOCKED",
        "compression_status": "NOT_RUN",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(output_dir / "qwen35_calibration_analysis.json", report)
    return report


def query_kaggle_status(kernel_id: str, root: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["kaggle", "kernels", "status", kernel_id], cwd=root,
        capture_output=True, text=True,
    )
    return {
        "schema_version": 1, "kernel_id": kernel_id,
        "status": parse_kaggle_status(result.stdout, result.stderr),
        "returncode": result.returncode, "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(), "queried_at_utc": utc_now(),
    }


def verify_backbone_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    def record(name: str, ok: bool, observed: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "observed": observed}
    record("kaggle_status", kaggle_status == "COMPLETE", kaggle_status)
    record("failure_absent", not (artifact_dir / "FAILURE.json").exists())
    record("success_marker", (artifact_dir / "SUCCESS.json").is_file())
    if (artifact_dir / "SUCCESS.json").is_file():
        checksum_ok = True
        for line in (artifact_dir / "checksums.sha256").read_text("utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            target = artifact_dir / relative
            checksum_ok = checksum_ok and target.is_file() and sha256_file(target) == expected
        record("artifact_checksums", checksum_ok)
        manifest = _load_json(artifact_dir / "submission_manifest.json")
        record("git_sha", manifest.get("git_sha") == submission["git_sha"], manifest.get("git_sha"))
        record("smoke_pass", _load_json(artifact_dir / "engineering_smoke/acceptance.json").get("status") == "PASS")
        record("exact_rerun", _load_json(artifact_dir / "open_calibration/exact_rerun.json").get("status") == "EXACT")
        rows_one = _jsonl(artifact_dir / "open_calibration/exact_run_1/image_gain_records.jsonl")
        rows_two = _jsonl(artifact_dir / "open_calibration/exact_run_2/image_gain_records.jsonl")
        record("calibration_call_count", len(rows_one) == len(rows_two) == 1000, [len(rows_one), len(rows_two)])
        record("locked_validation_not_exposed", manifest.get("locked_validation_pair_count_exposed_to_model") == 0)
        record("no_compression", manifest.get("compression_status") == "NOT_RUN")
    valid = all(check["ok"] for check in checks.values())
    return {"schema_version": 1, "verification_status": "VERIFIED" if valid else "INVALID", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    execute_remote_backbone(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
