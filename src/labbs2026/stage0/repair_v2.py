"""Fail-closed Stage 0 output-contract repair and repaired calibration."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml

from labbs2026.kaggle import (
    _check_remote_ref,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    cuda_preflight,
    load_runtime,
    locked_package_versions,
    parse_kaggle_status,
    render_worker,
    sha256_file,
    utc_now,
    write_failure,
)
from labbs2026.preflight import inspect_repository
from labbs2026.stage0.bundle import extract_and_verify_calibration_bundle
from labbs2026.stage0.kaggle_backend import (
    _check_runtime_contract,
    _checksums,
    stage0_preflight,
)
from labbs2026.stage0.metrics import compare_reproducibility, compute_stage0_metrics
from labbs2026.stage0.run import (
    ENGINEERING_SMOKE_ROLE,
    REPAIRED_CALIBRATION_ROLE,
    run_calibration,
)
from labbs2026.step3 import environment_record


KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-stage0-repair-v2",
    "title": "LabBS2026 Stage 0 Calibration Repair v2",
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
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def canonical_smoke_selection_sha256(smoke: dict[str, Any]) -> str:
    payload = {
        "strategy": smoke.get("selection_strategy"),
        "pair_ids": smoke.get("pair_ids"),
        "condition_id": smoke.get("condition_id"),
        "include_full_both_members": smoke.get("include_full_both_members"),
        "include_blank_both_orientations": smoke.get(
            "include_blank_both_orientations"
        ),
        "exact_rerun_count": smoke.get("exact_rerun_count"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def repair_preflight(
    root: Path,
    repair_path: Path,
    runtime_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    repair = _load_yaml(repair_path)
    frozen = repair["frozen_scientific_inputs"]
    contract = repair["repair_contract"]
    base_path = root / frozen["base_calibration_design"]
    model_path = root / contract["model_config"]
    base = stage0_preflight(root, base_path, runtime_path, model_path)
    checks = dict(base["checks"])
    hash_checks = {
        frozen["base_calibration_design"]: frozen["base_calibration_design_sha256"],
        frozen["calibration_input_bundle"]: frozen[
            "calibration_input_bundle_sha256"
        ],
        frozen["prompt_parser"]: frozen["prompt_parser_sha256"],
        contract["model_config"]: contract["model_config_sha256"],
        contract["tokenizer_audit"]: contract["tokenizer_audit_sha256"],
    }
    checks["repair_file_hashes"] = {
        "ok": all(sha256_file(root / path) == expected for path, expected in hash_checks.items()),
        "expected": hash_checks,
        "observed": {path: sha256_file(root / path) for path in hash_checks},
    }
    prohibitions = repair.get("prohibitions", {})
    checks["repair_authorization"] = {
        "ok": repair.get("status") == "FROZEN_REPAIR_V2_AUTHORIZED"
        and repair.get("previous_failure_classification")
        == "REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE"
        and all(value is False for value in prohibitions.values()),
        "status": repair.get("status"),
        "prohibitions": prohibitions,
    }
    smoke = repair["engineering_smoke"]
    checks["engineering_smoke_freeze"] = {
        "ok": smoke.get("scientific_evidence") is False
        and smoke.get("selection_sha256") == canonical_smoke_selection_sha256(smoke)
        and smoke.get("observations_per_exact_run") == 20
        and smoke.get("total_model_calls") == 40,
        "selection_sha256": canonical_smoke_selection_sha256(smoke),
    }
    model = _load_yaml(model_path)
    runtime = load_runtime(runtime_path)
    checks["repair_runtime_contract"] = {
        "ok": not _check_runtime_contract(runtime, model),
        "issues": _check_runtime_contract(runtime, model),
    }
    metadata_path = root / "infra/kaggle/stage0-repair-v2-kernel-metadata.json"
    checks["repair_kernel_metadata"] = {
        "ok": _load_json(metadata_path) == KERNEL_METADATA
    }
    decision_log = (root / "docs/DECISION_LOG.md").read_text(encoding="utf-8")
    checks["source_of_truth_boundary"] = {
        "ok": "REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE" in decision_log
        and "Gate 0 remains `NOT_RUN`" in decision_log
    }
    valid = all(check.get("ok") is True for check in checks.values())
    return {"schema_version": 1, "valid": valid, "checks": checks}


def make_repair_spec(
    root: Path, repair_path: Path, runtime_path: Path, git_sha: str
) -> dict[str, Any]:
    repair = _load_yaml(repair_path)
    frozen = repair["frozen_scientific_inputs"]
    contract = repair["repair_contract"]
    runtime = load_runtime(runtime_path)
    paths = {
        "repair_config_path": repair_path.relative_to(root).as_posix(),
        "config_path": frozen["base_calibration_design"],
        "runtime_path": runtime_path.relative_to(root).as_posix(),
        "model_config_path": contract["model_config"],
        "prompt_config_path": frozen["prompt_parser"],
        "bundle_path": frozen["calibration_input_bundle"],
        "tokenizer_audit_path": contract["tokenizer_audit"],
    }
    hashes = {
        key.replace("_path", "_sha256"): sha256_file(root / value)
        for key, value in paths.items()
    }
    repair_sha = hashes["repair_config_sha256"]
    smoke = repair["engineering_smoke"]
    full = repair["repaired_calibration"]
    return {
        "schema_version": 1,
        "run_type": "STAGE0_CALIBRATION_REPAIR_V2",
        "run_id": f"kaggle-stage0-repair-v2-{git_sha[:12]}-{repair_sha[:8]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        **paths,
        **hashes,
        "allocation_sha256": frozen["pair_allocation_sha256"],
        "requested_accelerator": runtime["accelerator"],
        "environment_contract": runtime["evidence_environment_contract"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "worker_template_path": "infra/kaggle/stage0_repair_v2_worker.py",
        "kernel_id": KERNEL_METADATA["id"],
        "previous_failure_classification": repair[
            "previous_failure_classification"
        ],
        "smoke": smoke,
        "repaired_calibration": full,
        "locked_validation_authorized": False,
        "gate_0_status": "NOT_RUN",
        "stage_1a_status": "BLOCKED",
        "created_at_utc": utc_now(),
    }


def prepare_repair_staging(
    root: Path, repair_path: Path, runtime_path: Path
) -> dict[str, Any]:
    preflight = repair_preflight(root, repair_path, runtime_path)
    if not preflight["valid"]:
        raise RuntimeError("Stage 0 Repair v2 preflight failed")
    git_sha = preflight["checks"]["repository"]["git_commit"]
    spec = make_repair_spec(root, repair_path, runtime_path, git_sha)
    run_dir = root / "runs" / "kaggle" / spec["run_id"]
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / spec["worker_template_path"]
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    shutil.copyfile(
        root / "infra/kaggle/stage0-repair-v2-kernel-metadata.json",
        staging / "kernel-metadata.json",
    )
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", preflight)
    return {
        "run_id": spec["run_id"],
        "run_dir": str(run_dir),
        "staging_dir": str(staging),
        "submit_command": build_submit_command(staging),
    }


def _validate_run(
    spec: dict[str, Any], run_dir: Path, *, smoke: bool
) -> dict[str, Any]:
    manifest = _load_json(run_dir / "manifest.json")
    rows = _jsonl(run_dir / "parsed_predictions.jsonl")
    failures = _load_json(run_dir / "execution_failures.json")
    expected = spec["smoke"]["observations_per_exact_run"] if smoke else spec[
        "repaired_calibration"
    ]["observations_per_exact_run"]
    full_rows = [row for row in rows if row["control_type"] == "FULL_INFORMATION"]
    blank_rows = [
        row
        for row in rows
        if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
    ]
    order_ok = True
    for pair_id in sorted({row["pair_id"] for row in rows}):
        pair_full = [row for row in full_rows if row["pair_id"] == pair_id]
        pair_blank = [row for row in blank_rows if row["pair_id"] == pair_id]
        if {row["expected_label"] for row in pair_full} != {"A", "B"}:
            order_ok = False
        if {row["orientation"] for row in pair_blank} != {"A_THEN_B", "B_THEN_A"}:
            order_ok = False
        if any(row["expected_label"] is not None for row in pair_blank):
            order_ok = False
    token_ok = all(
        row.get("llm_visual_token_count") == 256
        and row.get("visual_stage_metadata", {}).get("preprocessed_image_shape")
        == [448, 448]
        for row in rows
    )
    stored_metrics = _load_json(run_dir / "metrics.json")
    metrics_ok = True
    recomputed = None
    if not smoke:
        recomputed = compute_stage0_metrics(
            rows, bootstrap_seed=20260906, bootstrap_resamples=2000, confidence_level=0.95
        )
        metrics_ok = json.loads(json.dumps(recomputed)) == stored_metrics
    ok = all(
        (
            manifest.get("run_status") == "VALID",
            manifest.get("git_commit") == spec["git_sha"],
            manifest.get("allocation_sha256") == spec["allocation_sha256"],
            manifest.get("locked_validation_pair_count_exposed_to_model") == 0,
            len(rows) == expected,
            not failures,
            all(row.get("output_contract_conformance") is True for row in rows),
            all(row.get("parse_status") == "PARSED" for row in rows),
            all(row.get("raw_output") in {"A", "B"} for row in rows),
            all(len(row.get("generated_token_ids", [])) == 1 for row in rows),
            token_ok,
            order_ok,
            metrics_ok,
        )
    )
    return {
        "ok": ok,
        "rows": rows,
        "manifest": manifest,
        "execution_failure_count": len(failures),
        "order_ok": order_ok,
        "token_metadata_ok": token_ok,
        "metrics_recomputed": recomputed,
    }


def _smoke_acceptance(
    validations: list[dict[str, Any]], reproducibility: dict[str, Any]
) -> dict[str, Any]:
    rows = [row for validation in validations for row in validation["rows"]]
    expected_total = sum(len(validation["rows"]) for validation in validations)
    criteria = {
        "call_completion": len(rows) == 40,
        "execution_failures": sum(
            validation["execution_failure_count"] for validation in validations
        )
        == 0,
        "output_contract_conformance": all(
            row.get("output_contract_conformance") is True for row in rows
        ),
        "parser_failure": all(row.get("parse_status") == "PARSED" for row in rows),
        "parsed_choice_rerun_agreement": reproducibility["agreement_rates"][
            "parsed_output"
        ]
        == 1.0,
        "visual_token_rerun_agreement": reproducibility["agreement_rates"][
            "llm_visual_token_count"
        ]
        == 1.0,
        "candidate_order": all(validation["order_ok"] for validation in validations),
        "token_metadata": all(
            validation["token_metadata_ok"] for validation in validations
        ),
    }
    return {
        "schema_version": 1,
        "status": "PASS" if all(criteria.values()) else "FAIL",
        "scientific_use": "FORBIDDEN_ENGINEERING_SMOKE_ONLY",
        "visual_accuracy_computed": False,
        "completed_calls": len(rows),
        "planned_calls": expected_total,
        "criteria": criteria,
    }


def execute_remote_repair(spec_path: Path) -> None:
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
        input_dir = Path("/tmp/labbs2026-stage0-repair-v2-input")
        bundle = extract_and_verify_calibration_bundle(
            source / spec["bundle_path"], input_dir, spec["bundle_sha256"]
        )
        if bundle["allocation_sha256"] != spec["allocation_sha256"]:
            raise RuntimeError("bundle allocation hash does not match Repair v2")

        phase = "engineering_format_smoke"
        smoke_root = artifact_dir / "engineering_smoke"
        smoke_runs: list[Path] = []
        smoke_pairs = set(spec["smoke"]["pair_ids"])
        smoke_conditions = {spec["smoke"]["condition_id"]}
        for index in (1, 2):
            run = run_calibration(
                source / spec["config_path"],
                input_dir,
                source / spec["model_config_path"],
                runtime=runtime,
                output_dir=smoke_root / f"exact_run_{index}",
                expected_git_sha=spec["git_sha"],
                run_role=ENGINEERING_SMOKE_ROLE,
                selected_pair_ids=smoke_pairs,
                selected_condition_ids=smoke_conditions,
                compute_scientific_metrics=False,
            )
            smoke_runs.append(run)
            gc.collect()
            import torch

            torch.cuda.empty_cache()
        smoke_validations = [
            _validate_run(spec, run, smoke=True) for run in smoke_runs
        ]
        smoke_reproducibility = compare_reproducibility(
            smoke_validations[0]["rows"], smoke_validations[1]["rows"]
        )
        smoke_acceptance = _smoke_acceptance(
            smoke_validations, smoke_reproducibility
        )
        atomic_write_json(smoke_root / "reproducibility.json", smoke_reproducibility)
        atomic_write_json(smoke_root / "acceptance.json", smoke_acceptance)
        if smoke_acceptance["status"] != "PASS" or not all(
            validation["ok"] for validation in smoke_validations
        ):
            raise RuntimeError("engineering format smoke did not pass")

        phase = "repaired_calibration"
        calibration_root = artifact_dir / "repaired_calibration"
        calibration_runs: list[Path] = []
        for index in (1, 2):
            run = run_calibration(
                source / spec["config_path"],
                input_dir,
                source / spec["model_config_path"],
                runtime=runtime,
                output_dir=calibration_root / f"exact_run_{index}",
                expected_git_sha=spec["git_sha"],
                run_role=REPAIRED_CALIBRATION_ROLE,
                compute_scientific_metrics=True,
            )
            calibration_runs.append(run)
            gc.collect()
            import torch

            torch.cuda.empty_cache()
        validations = [
            _validate_run(spec, run, smoke=False) for run in calibration_runs
        ]
        if not all(validation["ok"] for validation in validations):
            raise RuntimeError("repaired calibration artifact validation failed")
        reproducibility = compare_reproducibility(
            validations[0]["rows"], validations[1]["rows"]
        )
        atomic_write_json(calibration_root / "reproducibility.json", reproducibility)
        atomic_write_json(
            artifact_dir / "runtime.json",
            {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "gpu_preflight": gpu,
                "environment": environment_record(),
                "frozen_environment_contract": spec["environment_contract"],
                "total_submission_seconds": time.perf_counter() - started,
            },
        )
        atomic_write_json(
            artifact_dir / "submission_manifest.json",
            {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "run_status": "VALID_REPAIRED_CALIBRATION",
                "git_sha": spec["git_sha"],
                "repair_config_sha256": spec["repair_config_sha256"],
                "bundle_sha256": spec["bundle_sha256"],
                "allocation_sha256": spec["allocation_sha256"],
                "engineering_smoke_status": "PASS",
                "engineering_smoke_model_calls": 40,
                "repaired_calibration_model_calls": 2000,
                "locked_validation_pair_count_exposed_to_model": 0,
                "gate_0_status": "NOT_RUN",
                "stage_1a_status": "BLOCKED",
            },
        )
        atomic_write_text(artifact_dir / "checksums.sha256", _checksums(artifact_dir))
        atomic_write_json(
            artifact_dir / "SUCCESS.json",
            {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
            },
        )
    except BaseException as exc:
        write_failure(artifact_dir, spec["run_id"], phase, exc)
        success = artifact_dir / "SUCCESS.json"
        if success.exists():
            success.unlink()
        raise


def verify_repair_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def record(name: str, ok: bool, observed: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "observed": observed}

    record("kaggle_status", kaggle_status == "COMPLETE", kaggle_status)
    record("failure_marker_absent", not (artifact_dir / "FAILURE.json").exists())
    success = artifact_dir / "SUCCESS.json"
    checksums = artifact_dir / "checksums.sha256"
    record("success_marker", success.is_file())
    record("checksums_file", checksums.is_file())
    if success.is_file() and checksums.is_file():
        checksum_ok = True
        for line in checksums.read_text("utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            path = artifact_dir / relative
            if not path.is_file() or sha256_file(path) != expected:
                checksum_ok = False
        record("artifact_checksums", checksum_ok)
        manifest = _load_json(artifact_dir / "submission_manifest.json")
        record("git_sha", manifest.get("git_sha") == submission["git_sha"])
        record(
            "repair_config_sha256",
            manifest.get("repair_config_sha256")
            == submission["repair_config_sha256"],
        )
        record("engineering_smoke", manifest.get("engineering_smoke_status") == "PASS")
        smoke_runs = [
            _validate_run(
                submission,
                artifact_dir / "engineering_smoke" / f"exact_run_{index}",
                smoke=True,
            )
            for index in (1, 2)
        ]
        full_runs = [
            _validate_run(
                submission,
                artifact_dir / "repaired_calibration" / f"exact_run_{index}",
                smoke=False,
            )
            for index in (1, 2)
        ]
        record("smoke_runs", all(item["ok"] for item in smoke_runs))
        record("repaired_calibration_runs", all(item["ok"] for item in full_runs))
        record(
            "locked_pairs_unexposed",
            manifest.get("locked_validation_pair_count_exposed_to_model") == 0,
        )
        runtime = _load_json(artifact_dir / "runtime.json")
        gpu = runtime.get("gpu_preflight", {})
        nvidia_smi = gpu.get("nvidia_smi", {})
        record(
            "gpu_provenance",
            bool(gpu.get("observed_gpu_name"))
            and nvidia_smi.get("available") is True
            and bool(nvidia_smi.get("parsed", {}).get("driver_version")),
        )
    valid = checks and all(check["ok"] for check in checks.values())
    return {
        "schema_version": 1,
        "verification_status": "VERIFIED" if valid else "INVALID",
        "hard_checks": checks,
    }


def query_kaggle_status(kernel_id: str, root: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["kaggle", "kernels", "status", kernel_id],
        cwd=root,
        capture_output=True,
        text=True,
    )
    raw = (result.stdout or result.stderr).strip()
    return {
        "returncode": result.returncode,
        "status": parse_kaggle_status(raw),
        "raw_output": raw,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    execute_remote_repair(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
