"""Immutable Kaggle backend for the human-frozen Stage 0 calibration only."""

from __future__ import annotations

import argparse
import gc
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
    is_t4_class_device,
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
from labbs2026.stage0.kaggle_workload import derive_workload
from labbs2026.stage0.metrics import compare_reproducibility, compute_stage0_metrics
from labbs2026.stage0.run import calibration_readiness_issues, run_calibration
from labbs2026.step3 import environment_record


KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-stage-0-calibration",
    "title": "LabBS2026 Stage 0 Calibration",
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


def _check_runtime_contract(runtime: dict[str, Any], model: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    runtime_model = runtime.get("model_runtime", {})
    model_values = model.get("model", {})
    for key in ("device", "dtype", "attention_implementation"):
        if runtime_model.get(key) != model_values.get(key):
            issues.append(f"RUNTIME_MODEL_{key.upper()}_MISMATCH")
    generation = model.get("generation", {})
    if model.get("stage") == "stage0_calibration_repair_v2":
        output_contract = generation.get("output_contract", {})
        if (
            generation.get("do_sample") is not False
            or generation.get("max_new_tokens") != 1
            or generation.get("min_new_tokens") != 1
            or output_contract.get("mode") != "canonical_label_token_constraint_v1"
            or output_contract.get("allowed_labels") != ["A", "B"]
            or output_contract.get("expected_label_token_ids") != {"A": 32, "B": 33}
        ):
            issues.append("REPAIR_V2_DECODING_CONFIG_MISMATCH")
    elif generation != {"do_sample": False, "max_new_tokens": 4}:
        issues.append("DECODING_CONFIG_MISMATCH")
    if model.get("seed_policy", {}).get("seed") != 20260906:
        issues.append("SEED_POLICY_MISMATCH")
    return issues


def stage0_preflight(
    root: Path, config_path: Path, runtime_path: Path, model_path: Path
) -> dict[str, Any]:
    root = root.resolve()
    checks: dict[str, dict[str, Any]] = {}
    repository = inspect_repository(root)
    checks["repository"] = {
        "ok": repository.valid,
        "git_commit": repository.git_commit,
        "git_clean": repository.git_clean,
        "missing_paths": list(repository.missing_paths),
    }
    try:
        config = _load_yaml(config_path)
        review = _load_json(root / config["human_review_record"])
        readiness = calibration_readiness_issues(config, review)
        checks["human_frozen_calibration"] = {
            "ok": not readiness,
            "issues": readiness,
            "config_sha256": sha256_file(config_path),
        }
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        config, review = {}, None
        checks["human_frozen_calibration"] = {"ok": False, "error": str(exc)}
    try:
        runtime = load_runtime(runtime_path)
        model = _load_yaml(model_path)
        runtime_issues = _check_runtime_contract(runtime, model)
        checks["runtime_contract"] = {
            "ok": not runtime_issues,
            "issues": runtime_issues,
            "runtime_sha256": sha256_file(runtime_path),
            "model_config_sha256": sha256_file(model_path),
            "environment_contract": runtime.get("evidence_environment_contract"),
        }
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        runtime, model = {}, {}
        checks["runtime_contract"] = {"ok": False, "error": str(exc)}

    bundle_path = root / str(config.get("calibration_input_bundle", ""))
    try:
        with tempfile.TemporaryDirectory(prefix="labbs-stage0-preflight-") as temporary:
            extracted = Path(temporary) / "input"
            bundle_manifest = extract_and_verify_calibration_bundle(
                bundle_path,
                extracted,
                str(config["calibration_input_bundle_sha256"]),
            )
            workload = derive_workload(
                config,
                review,
                _load_json(extracted / "resolved_pairs.json"),
                _load_json(extracted / "render_manifest.json"),
                _load_yaml(root / config["prompt_parser"])["prompt_template"],
            )
            resolved_pairs = _load_json(extracted / "resolved_pairs.json")
            component_counts: dict[str, int] = {}
            for pair in resolved_pairs:
                component = pair["component_type"]
                component_counts[component] = component_counts.get(component, 0) + 1
        bundle_ok = (
            bundle_manifest["allocation_sha256"] == config["allocation"]["sha256"]
            and bundle_manifest["source_review_packet_sha256"]
            == config["source_review_packet_sha256"]
            and workload.get("exact_observation_count") == 1000
            and workload.get("total_model_calls_including_rerun") == 2000
            and workload.get("locked_validation_included") is False
            and set(component_counts.values()) == {20}
            and len(component_counts) == 5
            and sha256_file(root / config["candidate_inventory"])
            == config["candidate_inventory_sha256"]
        )
        checks["calibration_input_bundle"] = {
            "ok": bundle_ok,
            "bundle_sha256": sha256_file(bundle_path),
            "bundle_manifest": bundle_manifest,
            "workload": workload,
            "calibration_component_counts": component_counts,
        }
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        checks["calibration_input_bundle"] = {"ok": False, "error": str(exc)}

    metadata_path = root / "infra/kaggle/stage0-kernel-metadata.json"
    try:
        metadata = _load_json(metadata_path)
        checks["kernel_metadata"] = {
            "ok": metadata == KERNEL_METADATA,
            "observed": metadata,
        }
    except (OSError, ValueError) as exc:
        checks["kernel_metadata"] = {"ok": False, "error": str(exc)}
    uv_lock = root / "uv.lock"
    checks["uv_lock"] = {
        "ok": uv_lock.is_file(),
        "sha256": sha256_file(uv_lock) if uv_lock.is_file() else None,
        "versions": locked_package_versions(uv_lock) if uv_lock.is_file() else None,
    }
    kaggle_version = subprocess.run(
        ["kaggle", "--version"], cwd=root, capture_output=True, text=True
    )
    kaggle_auth = subprocess.run(
        ["kaggle", "kernels", "list", "--mine", "--page-size", "1", "-v"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    checks["kaggle_cli_and_auth"] = {
        "ok": kaggle_version.returncode == 0 and kaggle_auth.returncode == 0,
        "version": kaggle_version.stdout.strip(),
    }
    source = runtime.get("source", {})
    remote_sha, remote_error = _check_remote_ref(
        root, str(source.get("repository_url", "")), str(source.get("remote_ref", ""))
    )
    checks["remote_ref"] = {
        "ok": remote_sha is not None and remote_sha == repository.git_commit,
        "local_sha": repository.git_commit,
        "remote_sha": remote_sha,
        "remote_ref": source.get("remote_ref"),
        "error": remote_error,
    }
    return {
        "schema_version": 1,
        "valid": all(check.get("ok") is True for check in checks.values()),
        "checks": checks,
    }


def make_stage0_spec(
    root: Path,
    config_path: Path,
    runtime_path: Path,
    model_path: Path,
    git_sha: str,
) -> dict[str, Any]:
    config = _load_yaml(config_path)
    runtime = load_runtime(runtime_path)
    paths = {
        "config_path": config_path.relative_to(root).as_posix(),
        "runtime_path": runtime_path.relative_to(root).as_posix(),
        "model_config_path": model_path.relative_to(root).as_posix(),
        "prompt_config_path": str(config["prompt_parser"]),
        "human_review_path": str(config["human_review_record"]),
        "bundle_path": str(config["calibration_input_bundle"]),
    }
    hashes = {
        key.replace("_path", "_sha256"): sha256_file(root / value)
        for key, value in paths.items()
    }
    config_sha = hashes["config_sha256"]
    return {
        "schema_version": 1,
        "run_type": "STAGE0_CALIBRATION_ONLY",
        "run_id": f"kaggle-stage0-calibration-{git_sha[:12]}-{config_sha[:8]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        **paths,
        **hashes,
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "worker_template_path": "infra/kaggle/stage0_worker.py",
        "model_id": "Qwen/Qwen2.5-VL-3B-Instruct",
        "model_revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
        "processor_revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
        "allocation_sha256": config["allocation"]["sha256"],
        "requested_accelerator": runtime["accelerator"],
        "environment_contract": runtime["evidence_environment_contract"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "exact_observations_per_run": 1000,
        "full_information_calls_per_run": 800,
        "blank_control_calls_per_run": 200,
        "exact_rerun_count": 2,
        "total_model_calls": 2000,
        "locked_validation_authorized": False,
        "kernel_id": KERNEL_METADATA["id"],
        "created_at_utc": utc_now(),
    }


def prepare_stage0_staging(
    root: Path, config_path: Path, runtime_path: Path, model_path: Path
) -> dict[str, Any]:
    preflight = stage0_preflight(root, config_path, runtime_path, model_path)
    if not preflight["valid"]:
        raise RuntimeError("Stage 0 Kaggle preflight failed")
    git_sha = preflight["checks"]["repository"]["git_commit"]
    spec = make_stage0_spec(root, config_path, runtime_path, model_path, git_sha)
    run_dir = root / "runs" / "kaggle" / spec["run_id"]
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / spec["worker_template_path"]
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(
        staging / "worker.py", render_worker(template.read_text("utf-8"), spec)
    )
    shutil.copyfile(
        root / "infra/kaggle/stage0-kernel-metadata.json",
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


def _validate_rows(spec: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    manifest = _load_json(run_dir / "manifest.json")
    rows = _jsonl(run_dir / "parsed_predictions.jsonl")
    failures = _load_json(run_dir / "execution_failures.json")
    full = [row for row in rows if row["control_type"] == "FULL_INFORMATION"]
    blank = [
        row
        for row in rows
        if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
    ]
    expected_processing = _load_yaml(Path(spec["model_config_path"]))[
        "expected_full_information_processing"
    ]
    metadata_ok = True
    for row in rows:
        metadata = row["visual_stage_metadata"]
        for key, expected in expected_processing.items():
            if metadata.get(key) != expected:
                metadata_ok = False
    metrics = compute_stage0_metrics(
        rows,
        bootstrap_seed=20260906,
        bootstrap_resamples=2000,
        confidence_level=0.95,
    )
    stored_metrics = _load_json(run_dir / "metrics.json")
    json_normalized_metrics = json.loads(json.dumps(metrics))
    return {
        "ok": all(
            (
                manifest.get("run_status") == "VALID",
                manifest.get("git_commit") == spec["git_sha"],
                manifest.get("allocation_sha256") == spec["allocation_sha256"],
                manifest.get("observation_count")
                == spec["exact_observations_per_run"],
                manifest.get("failure_count") == 0,
                manifest.get("locked_validation_pair_count_exposed_to_model") == 0,
                len(rows) == spec["exact_observations_per_run"],
                len(full) == spec["full_information_calls_per_run"],
                len(blank) == spec["blank_control_calls_per_run"],
                not failures,
                all(row.get("expected_label") is None for row in blank),
                all(row.get("is_correct") is None for row in blank),
                metadata_ok,
                json_normalized_metrics == stored_metrics,
            )
        ),
        "manifest": manifest,
        "rows": rows,
        "metrics_recomputed": metrics,
        "metadata_contract_ok": metadata_ok,
    }


def _checksums(artifact_dir: Path) -> str:
    excluded = {"checksums.sha256", "SUCCESS.json", "FAILURE.json"}
    paths = sorted(
        path
        for path in artifact_dir.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    return "".join(
        f"{sha256_file(path)}  {path.relative_to(artifact_dir).as_posix()}\n"
        for path in paths
    )


def execute_remote_stage0(spec_path: Path) -> None:
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
        input_dir = Path("/tmp/labbs2026-stage0-input")
        bundle_manifest = extract_and_verify_calibration_bundle(
            source / spec["bundle_path"], input_dir, spec["bundle_sha256"]
        )
        if bundle_manifest["allocation_sha256"] != spec["allocation_sha256"]:
            raise RuntimeError("bundle allocation hash does not match submission")
        phase = "calibration_execution"
        run_dirs: list[Path] = []
        for rerun_index in range(1, spec["exact_rerun_count"] + 1):
            run_dir = run_calibration(
                source / spec["config_path"],
                input_dir,
                source / spec["model_config_path"],
                runtime=runtime,
                output_dir=artifact_dir / f"exact_run_{rerun_index}",
                expected_git_sha=spec["git_sha"],
            )
            run_dirs.append(run_dir)
            gc.collect()
            import torch

            torch.cuda.empty_cache()
        phase = "calibration_validation"
        validations = [_validate_rows(spec, run_dir) for run_dir in run_dirs]
        if not all(validation["ok"] for validation in validations):
            raise RuntimeError("one or more calibration runs failed artifact validation")
        reproducibility = compare_reproducibility(
            validations[0]["rows"], validations[1]["rows"]
        )
        atomic_write_json(artifact_dir / "reproducibility.json", reproducibility)
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
                "run_status": "VALID_CALIBRATION",
                "scientific_scope": "STAGE0_CALIBRATION_ONLY",
                "git_sha": spec["git_sha"],
                "config_sha256": spec["config_sha256"],
                "runtime_sha256": spec["runtime_sha256"],
                "model_config_sha256": spec["model_config_sha256"],
                "bundle_sha256": spec["bundle_sha256"],
                "allocation_sha256": spec["allocation_sha256"],
                "exact_rerun_count": len(run_dirs),
                "total_model_calls": sum(
                    validation["manifest"]["observation_count"]
                    for validation in validations
                ),
                "locked_validation_pair_count_exposed_to_model": 0,
                "gate_0_status": "NOT_RUN",
                "stage_1a_status": "BLOCKED",
            },
        )
        phase = "artifact_finalization"
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


def verify_stage0_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def record(name: str, ok: bool, observed: Any = None, expected: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "observed": observed, "expected": expected}

    record("kaggle_status", kaggle_status == "COMPLETE", kaggle_status, "COMPLETE")
    record("failure_marker_absent", not (artifact_dir / "FAILURE.json").exists())
    success_path = artifact_dir / "SUCCESS.json"
    checksum_path = artifact_dir / "checksums.sha256"
    record("success_marker", success_path.is_file())
    record("checksums_file", checksum_path.is_file())
    if not success_path.is_file() or not checksum_path.is_file():
        return {
            "schema_version": 1,
            "verification_status": "INVALID",
            "hard_checks": checks,
        }
    success = _load_json(success_path)
    record("success_run_id", success.get("run_id") == submission["run_id"])
    record(
        "checksums_identity",
        success.get("checksums_sha256") == sha256_file(checksum_path),
    )
    checksum_ok = True
    for line in checksum_path.read_text("utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = artifact_dir / relative
        if not path.is_file() or sha256_file(path) != expected:
            checksum_ok = False
    record("artifact_checksums", checksum_ok)
    manifest = _load_json(artifact_dir / "submission_manifest.json")
    for key in (
        "run_id",
        "git_sha",
        "config_sha256",
        "runtime_sha256",
        "model_config_sha256",
        "bundle_sha256",
        "allocation_sha256",
    ):
        record(
            key,
            manifest.get(key) == submission.get(key),
            manifest.get(key),
            submission.get(key),
        )
    record(
        "scientific_scope",
        manifest.get("scientific_scope") == "STAGE0_CALIBRATION_ONLY",
    )
    record("model_call_count", manifest.get("total_model_calls") == 2000)
    record(
        "locked_pairs_unexposed",
        manifest.get("locked_validation_pair_count_exposed_to_model") == 0,
    )
    run_validations = [
        _validate_rows(submission, artifact_dir / f"exact_run_{index}")
        for index in (1, 2)
    ]
    record("exact_runs_valid", all(item["ok"] for item in run_validations))
    observed_reproducibility = _load_json(artifact_dir / "reproducibility.json")
    recomputed_reproducibility = compare_reproducibility(
        run_validations[0]["rows"], run_validations[1]["rows"]
    )
    record(
        "reproducibility_recompute",
        observed_reproducibility == recomputed_reproducibility,
    )
    runtime = _load_json(artifact_dir / "runtime.json")
    environment = runtime.get("environment", {})
    contract = submission["environment_contract"]
    record(
        "gpu_t4",
        is_t4_class_device(
            runtime.get("gpu_preflight", {}).get("observed_gpu_name", "")
        ),
    )
    record(
        "torch",
        environment.get("torch") == contract["torch"],
        environment.get("torch"),
        contract["torch"],
    )
    record(
        "transformers",
        environment.get("transformers") == contract["transformers"],
    )
    record(
        "cuda_runtime",
        environment.get("torch_cuda_runtime") == contract["cuda_runtime"],
    )
    valid = all(check["ok"] for check in checks.values())
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
    execute_remote_stage0(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
