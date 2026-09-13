"""Kaggle lifecycle CLI for the authorized frozen Paddle/Wayu locked panel."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import yaml

from labbs2026.kaggle import (
    _check_remote_ref,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    load_runtime,
    render_worker,
    sha256_file,
    utc_now,
)
from labbs2026.stage0.locked_panel_bundle import verify_locked_source_bundle
from labbs2026.stage0.locked_panel_analysis import finalize_analysis, write_analysis_inputs
from labbs2026.stage0.measurement_diagnostic import query_status


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_locked_panel_execution.yaml"
TRANSPORT_CONFIG = ROOT / "configs/runtime/kaggle_locked_panel_attempt3_transport.yaml"
WORKER = ROOT / "infra/kaggle/paddle_wayu_locked_panel_worker.py"
DESIGN_PLACEHOLDER = "__LABBS_FROZEN_DESIGN_B64__"
DATASET_METADATA_FILENAME = "dataset-metadata.json"
KERNEL = {
    "id": "thanakritsamoena/labbs2026-paddle-wayu-locked-model-budget-panel",
    "title": "LabBS2026 Paddle Wayu Locked Model Budget Panel",
    "code_file": "worker.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": ["thanakritsamoena/labbs2026-paddle-wayu-locked-source"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _tracked_clean() -> bool:
    return (
        subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0
        and subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0
    )


def _git_bytes(revision: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{relative}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout


def _blob_hash(relative: str, revision: str) -> str:
    return hashlib.sha256(_git_bytes(revision, relative)).hexdigest()


def _locked_dataset_files(dataset_root: Path, transport: dict[str, Any]) -> tuple[Path, Path]:
    archive = dataset_root / transport["archive_filename"]
    manifest = dataset_root / transport["external_manifest_filename"]
    return archive, manifest


def _validate_locked_dataset(dataset_root: Path, transport: dict[str, Any]) -> dict[str, Any]:
    archive, manifest_path = _locked_dataset_files(dataset_root, transport)
    expected_names = {transport["archive_filename"], transport["external_manifest_filename"]}
    observed_names = {path.name for path in dataset_root.iterdir() if path.is_file() and path.name != DATASET_METADATA_FILENAME}
    manifest = json.loads(manifest_path.read_text("utf-8"))
    bundle = verify_locked_source_bundle(archive, transport["archive_sha256"])
    with zipfile.ZipFile(archive) as locked_zip:
        observed_archive_manifest_sha256 = hashlib.sha256(
            locked_zip.read("bundle_manifest.json")
        ).hexdigest()
    checks = {
        "minimum_file_allowlist": observed_names == expected_names,
        "archive_bytes": archive.stat().st_size == transport["archive_bytes"],
        "archive_sha256": sha256_file(archive) == transport["archive_sha256"],
        "external_manifest_sha256": sha256_file(manifest_path) == transport["external_manifest_sha256"],
        "external_manifest_content": manifest == {
            "schema_version": 1,
            "scientific_scope": "AUTHORIZED_LOCKED_PANEL_SOURCE_448_RGB",
            "archive_filename": transport["archive_filename"],
            "archive_bytes": transport["archive_bytes"],
            "archive_sha256": transport["archive_sha256"],
            "archive_manifest_sha256": transport["archive_manifest_sha256"],
        },
        "archive_manifest_sha256": observed_archive_manifest_sha256 == transport["archive_manifest_sha256"],
        "registered_locked_pairs": bundle["registered_locked_pair_count"] == 100,
        "source_pngs": bundle["source_png_count"] == 800,
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "bundle": {
            "bundle_sha256": transport["archive_sha256"],
            "allocation_sha256": bundle["allocation_sha256"],
            "registered_locked_pair_count": bundle["registered_locked_pair_count"],
            "source_png_count": bundle["source_png_count"],
        },
    }


def prepare_dataset(source_archive: Path, output_dir: Path) -> dict[str, Any]:
    transport = _yaml(TRANSPORT_CONFIG)
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite dataset staging: {output_dir}")
    if source_archive.stat().st_size != transport["archive_bytes"] or sha256_file(source_archive) != transport["archive_sha256"]:
        raise RuntimeError("source archive identity mismatch")
    output_dir.mkdir(parents=True)
    archive, manifest_path = _locked_dataset_files(output_dir, transport)
    shutil.copyfile(source_archive, archive)
    external_manifest = {
        "schema_version": 1,
        "scientific_scope": "AUTHORIZED_LOCKED_PANEL_SOURCE_448_RGB",
        "archive_filename": transport["archive_filename"],
        "archive_bytes": transport["archive_bytes"],
        "archive_sha256": transport["archive_sha256"],
        "archive_manifest_sha256": transport["archive_manifest_sha256"],
    }
    atomic_write_json(manifest_path, external_manifest)
    atomic_write_json(output_dir / DATASET_METADATA_FILENAME, {
        "title": transport["dataset_title"],
        "id": transport["dataset_id"],
        "licenses": [{"name": "other"}],
    })
    validation = _validate_locked_dataset(output_dir, transport)
    if not validation["valid"]:
        raise RuntimeError(f"locked dataset staging failed validation: {validation}")
    return {
        "dataset_id": transport["dataset_id"],
        "private_required": transport["dataset_private"],
        "staging": str(output_dir.resolve()),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256_file(archive),
        "manifest_sha256": sha256_file(manifest_path),
        "data_file_count": 2,
        "validation": validation,
    }


def preflight(dataset_root: Path | None = None) -> dict[str, Any]:
    config = _yaml(CONFIG)
    transport = _yaml(TRANSPORT_CONFIG)
    runtime = load_runtime(ROOT / config["runtime_config"])
    frozen_sha = config["frozen_design_git_sha"]
    design_bytes = _git_bytes(frozen_sha, config["frozen_design_path"])
    design = yaml.safe_load(design_bytes)
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    remote, remote_error = _check_remote_ref(
        ROOT, runtime["source"]["repository_url"], runtime["source"]["remote_ref"]
    )
    review = ROOT / config["source_review_dir"]
    checks = {
        "tracked_tree_clean": _tracked_clean(),
        "remote_exact_sha": remote_error is None and remote == git_sha,
        "human_authorization": transport["status"] == "HUMAN_APPROVED_PACKAGE_LIMIT_REPAIR_AND_ATTEMPT_3",
        "attempt_3": transport["attempt"] == 3,
        "private_dataset": transport["dataset_private"] is True,
        "dataset_source_exact": KERNEL["dataset_sources"] == [transport["dataset_id"]],
        "frozen_design_sha": hashlib.sha256(design_bytes).hexdigest() == config["frozen_design_sha256"],
        "frozen_pipeline_sha": _blob_hash(config["frozen_resolution_pipeline_path"], frozen_sha) == config["frozen_resolution_pipeline_sha256"],
        "current_pipeline_unchanged": sha256_file(ROOT / config["frozen_resolution_pipeline_path"]) == config["frozen_resolution_pipeline_sha256"],
        "review_packet_sha": sha256_file(review / "review_packet.json") == config["source_review_packet_sha256"],
        "exact_models": len(design["models"]) == 2,
        "exact_budgets": [row["llm_image_placeholders"] for row in design["intervention"]["budgets"]] == [256, 196, 121, 64],
        "exact_workload": design["execution"]["total_calls"] == config["expected_calls"] == 6400,
        "one_shot": design["execution"]["mode"] == "ONE_SHOT_LOCKED_CONFIRMATORY_PANEL",
        "no_retry": not config["automatic_retry"] and not design["decoding"]["per_example_retry"],
        "prompt_exact": design["prompt"] == "OCR:",
        "parser_exact": design["primary_parser"]["operation"] == "PYTHON_STRIP_LEADING_TRAILING_WHITESPACE_ONLY",
    }
    dataset_validation = None
    if dataset_root is not None:
        dataset_validation = _validate_locked_dataset(dataset_root, transport)
        checks["locked_dataset_local_validation"] = dataset_validation["valid"]
    return {
        "schema_version": 1,
        "valid": all(checks.values()),
        "git_sha": git_sha,
        "remote_sha": remote,
        "remote_error": remote_error,
        "frozen_design_git_sha": frozen_sha,
        "dataset_validation": dataset_validation,
        "checks": checks,
    }


def prepare(dataset_root: Path) -> dict[str, Any]:
    check = preflight(dataset_root)
    if not check["valid"]:
        raise RuntimeError(f"locked-panel preflight failed: {check}")
    config = _yaml(CONFIG)
    transport = _yaml(TRANSPORT_CONFIG)
    runtime = load_runtime(ROOT / config["runtime_config"])
    git_sha = check["git_sha"]
    frozen_bytes = _git_bytes(config["frozen_design_git_sha"], config["frozen_design_path"])
    run_id = f"kaggle-paddle-wayu-locked-panel-attempt3-{git_sha[:12]}"
    run_dir = ROOT / "runs/kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    bundle_path, dataset_manifest_path = _locked_dataset_files(dataset_root, transport)
    bundle = check["dataset_validation"]["bundle"]
    runtime_hash = sha256_file(ROOT / config["runtime_config"])
    allocation = _yaml(ROOT / "configs/stage0/calibration_design.yaml")["allocation"]
    paths = [
        CONFIG.relative_to(ROOT).as_posix(),
        TRANSPORT_CONFIG.relative_to(ROOT).as_posix(),
        config["runtime_config"],
        WORKER.relative_to(ROOT).as_posix(),
        "src/labbs2026/stage0/paddle_wayu_locked_panel.py",
        "src/labbs2026/stage0/locked_panel_bundle.py",
        "src/labbs2026/stage0/resolution_pipeline.py",
        "src/labbs2026/stage0/paddle_wayu_smoke.py",
        "src/labbs2026/stage0/bundle.py",
        "src/labbs2026/kaggle.py",
        "configs/stage0/calibration_design.yaml",
        "uv.lock",
        runtime["uv"]["transformers_override_lock"],
    ]
    hashes = {path: _blob_hash(path, git_sha) for path in paths}
    spec = {
        "schema_version": 1,
        "run_type": "PADDLE_WAYU_FROZEN_ONE_SHOT_LOCKED_MODEL_BUDGET_PANEL",
        "run_id": run_id,
        "git_sha": git_sha,
        "SCIENTIFIC_DESIGN_COMMIT": config["frozen_design_git_sha"],
        "EXECUTION_REPAIR_COMMIT": git_sha,
        "frozen_design_git_sha": config["frozen_design_git_sha"],
        "frozen_design_sha256": config["frozen_design_sha256"],
        "runtime_config_sha256": runtime_hash,
        "locked_allocation_sha256": allocation["sha256"],
        "model_revision_hashes": {
            row["role"]: row["revision"] for row in yaml.safe_load(frozen_bytes)["models"]
        },
        "locked_panel_authorized": True,
        "scientific_output_unseal_during_execution": False,
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "source_hashes": hashes,
        "locked_source_bundle_sha256": bundle["bundle_sha256"],
        "locked_source_bundle_bytes": transport["archive_bytes"],
        "locked_source_archive_filename": transport["archive_filename"],
        "locked_source_archive_manifest_sha256": transport["archive_manifest_sha256"],
        "locked_source_dataset_id": transport["dataset_id"],
        "locked_source_dataset_manifest_filename": transport["external_manifest_filename"],
        "locked_source_dataset_manifest_sha256": transport["external_manifest_sha256"],
        "staged_frozen_design_path": "/tmp/labbs-paddle-wayu-locked-package/frozen_design.yaml",
        "staged_locked_bundle_path": "KAGGLE_DATASET_DISCOVERY_REQUIRED",
        "packaged_artifacts": {
            "frozen_design": {
                "source_path": f"git:{config['frozen_design_git_sha']}:{config['frozen_design_path']}",
                "packaged_path": "worker.py:FROZEN_DESIGN_B64 -> /tmp/labbs-paddle-wayu-locked-package/frozen_design.yaml",
                "file_size": len(frozen_bytes),
                "sha256": hashlib.sha256(frozen_bytes).hexdigest(),
                "expected_sha256": config["frozen_design_sha256"],
            },
            "locked_source_bundle": {
                "source_path": str(bundle_path.resolve()),
                "packaged_path": f"Kaggle Dataset {transport['dataset_id']}:{transport['archive_filename']}",
                "file_size": bundle_path.stat().st_size,
                "sha256": bundle["bundle_sha256"],
                "expected_sha256": bundle["bundle_sha256"],
            },
            "locked_source_dataset_manifest": {
                "source_path": str(dataset_manifest_path.resolve()),
                "packaged_path": f"Kaggle Dataset {transport['dataset_id']}:{transport['external_manifest_filename']}",
                "file_size": dataset_manifest_path.stat().st_size,
                "sha256": sha256_file(dataset_manifest_path),
                "expected_sha256": transport["external_manifest_sha256"],
            },
        },
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "requested_accelerator": runtime["accelerator"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "transformers_override_lock": runtime["uv"]["transformers_override_lock"],
        "kernel_id": KERNEL["id"],
        "created_at_utc": utc_now(),
    }
    rendered = render_worker(WORKER.read_text("utf-8"), spec)
    if rendered.count(DESIGN_PLACEHOLDER) != 1:
        raise RuntimeError("worker frozen-design placeholder is not unique")
    rendered = rendered.replace(DESIGN_PLACEHOLDER, base64.b64encode(frozen_bytes).decode("ascii"))
    atomic_write_text(staging / "worker.py", rendered)
    atomic_write_json(staging / "kernel-metadata.json", KERNEL)
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", check)
    atomic_write_json(run_dir / "locked_source_bundle_manifest.json", bundle)
    validation_root = run_dir / "authorization_validation"
    environment = dict(os.environ)
    environment["LABBS_AUTHORIZATION_ONLY"] = "1"
    environment["LABBS_AUTH_VALIDATION_OUTPUT_ROOT"] = str(validation_root.resolve())
    environment["LABBS_AUTH_VALIDATION_DATASET_ROOT"] = str(dataset_root.resolve())
    validation = subprocess.run(
        [sys.executable, str(staging / "worker.py")], cwd=ROOT,
        env=environment, capture_output=True, text=True,
    )
    record_path = validation_root / run_id / "engineering/AUTHORIZATION_VALIDATED.json"
    if validation.returncode or not record_path.is_file():
        raise RuntimeError(f"authorization-only staging validation failed: {validation.stderr[-4000:]}")
    record = json.loads(record_path.read_text("utf-8"))
    if record["status"] != "AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION":
        raise RuntimeError("authorization-only staging validation did not reach the required stop")
    atomic_write_json(run_dir / "authorization_staging_validation.json", record)
    staging_files = sorted(path for path in staging.iterdir() if path.is_file())
    package_audit = {
        "schema_version": 1,
        "allowlist": ["kernel-metadata.json", "worker.py"],
        "file_count": len(staging_files),
        "files": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in staging_files],
        "submission_directory_bytes": sum(path.stat().st_size for path in staging_files),
        "largest_file": max(staging_files, key=lambda path: path.stat().st_size).name,
        "locked_source_archive_in_submission": any(path.name == transport["archive_filename"] for path in staging_files),
    }
    if {path.name for path in staging_files} != set(package_audit["allowlist"]) or package_audit["locked_source_archive_in_submission"]:
        raise RuntimeError(f"Attempt 3 staging allowlist failed: {package_audit}")
    atomic_write_json(run_dir / "package_audit.json", package_audit)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "authorization_staging_validation": record["status"],
        "package_audit": package_audit,
        "submit_command": build_submit_command(staging),
    }


def _artifact(run_dir: Path, spec: dict[str, Any]) -> Path:
    return run_dir / "fetched/artifacts" / spec["run_id"]


def _count_newlines(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return count


def verify(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    artifact = _artifact(run_dir, spec)
    status = json.loads((run_dir / "kaggle_status.json").read_text("utf-8"))
    checks = {
        "kaggle_complete": status["status"] == "COMPLETE",
        "success_present": (artifact / "SUCCESS.json").is_file(),
        "failure_absent": not (artifact / "engineering/FAILURE.json").exists(),
    }
    if checks["success_present"]:
        success = json.loads((artifact / "SUCCESS.json").read_text("utf-8"))
        manifest = json.loads((artifact / "engineering/execution_manifest.json").read_text("utf-8"))
        model_manifest = json.loads((artifact / "engineering/model_revision_manifest.json").read_text("utf-8"))
        ledger = [
            json.loads(line)
            for line in (artifact / "engineering/call_ledger.jsonl").read_text("utf-8").splitlines()
        ]
        checksum_path = artifact / "checksums.sha256"
        checksum_lines = checksum_path.read_text("utf-8").splitlines()
        checksum_ok = all(
            (artifact / relative).is_file() and sha256_file(artifact / relative) == expected
            for expected, relative in (line.split("  ", 1) for line in checksum_lines)
        )
        expected_models = {
            ("BASE", "PaddlePaddle/PaddleOCR-VL-1.6", "c5630abae1d940eafe0697512a0325494b02ab42"),
            ("SPECIALIZED", "wayu-ai/wayu-paxa-ocr-zero", "af0204b4f334a6d5068b6bac2b3738932d6e289b"),
        }
        observed_models = {
            (row["role"], row["model_id"], row["requested_revision"])
            for row in model_manifest["models"]
        }
        raw_base = artifact / "sealed/raw_outputs_base.jsonl"
        raw_specialized = artifact / "sealed/raw_outputs_specialized.jsonl"
        checks.update({
            "run_id_match": manifest["run_id"] == spec["run_id"],
            "execution_git_sha_match": manifest["execution_git_sha"] == spec["git_sha"],
            "separate_scientific_identity": manifest["SCIENTIFIC_DESIGN_COMMIT"] == spec["SCIENTIFIC_DESIGN_COMMIT"] == "871996221a36a56a401fa040c239f55768561210",
            "separate_execution_identity": manifest["EXECUTION_REPAIR_COMMIT"] == spec["EXECUTION_REPAIR_COMMIT"] == spec["git_sha"],
            "frozen_design_sha_match": manifest["frozen_design_git_sha"] == spec["frozen_design_git_sha"],
            "frozen_design_hash_match": manifest["frozen_design_sha256"] == spec["frozen_design_sha256"],
            "runtime_config_hash_match": manifest["runtime_config_sha256"] == spec["runtime_config_sha256"],
            "locked_allocation_hash_match": manifest["locked_allocation_sha256"] == spec["locked_allocation_sha256"],
            "source_bundle_hash_match": manifest["locked_source_bundle_sha256"] == spec["locked_source_bundle_sha256"],
            "model_revision_hashes_match": manifest["model_revision_hashes"] == spec["model_revision_hashes"],
            "exact_models_and_revisions": observed_models == expected_models,
            "exact_6400_calls": manifest["call_count"] == manifest["unique_call_count"] == len(ledger) == 6400,
            "unique_ledger_ids": len({row["call_id"] for row in ledger}) == 6400,
            "exact_token_distribution": manifest["token_count_distribution"] == {"64": 1600, "121": 1600, "196": 1600, "256": 1600},
            "all_engineering_boundaries_valid": all(row["input_prefix_identity"] and row["finite_processor_tensor"] for row in ledger),
            "registered_locked_pairs": manifest["registered_locked_pair_count"] == 100,
            "unauthorized_locked_zero": manifest["unauthorized_or_out_of_workload_locked_pair_count"] == 0,
            "exact_stimuli": manifest["source_png_count"] == 800 and manifest["materialized_stimulus_count"] == 3200,
            "raw_files_present": raw_base.is_file() and raw_specialized.is_file(),
            "raw_line_counts": raw_base.is_file() and raw_specialized.is_file() and _count_newlines(raw_base) == _count_newlines(raw_specialized) == 3200,
            "sealed_before_verification": manifest["scientific_outputs_sealed"] is True and manifest["scientific_analysis_run"] is False,
            "success_checksum_identity": success["checksums_sha256"] == sha256_file(checksum_path),
            "artifact_checksums": checksum_ok,
        })
    result = {
        "schema_version": 1,
        "verification_status": "VERIFIED" if checks and all(checks.values()) else "FAILED",
        "scientific_outputs_opened": False,
        "checks": checks,
    }
    return result


def analyze(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    artifact = _artifact(run_dir, spec)
    analysis_dir = run_dir / "analysis"
    image = "labbs2026-locked-panel-r:4.5.2-lme4-1.1-38"
    docker_dir = ROOT / "infra/analysis/paddle_wayu_locked_panel"
    build = subprocess.run(
        ["docker", "build", "--pull", "-t", image, str(docker_dir)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if build.returncode:
        raise RuntimeError(f"registered R environment build failed: {build.stderr[-4000:]}")
    state = write_analysis_inputs(artifact, analysis_dir)
    if not state["primary_analysis_interpretable"]:
        return finalize_analysis(analysis_dir, None)
    mount = f"{analysis_dir.resolve()}:/analysis"
    execution = subprocess.run(
        ["docker", "run", "--rm", "-v", mount, image,
         "/analysis/analysis_rows.csv", "/analysis/glmm_result.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if execution.returncode:
        raise RuntimeError(f"registered GLMM execution failed: {execution.stderr[-4000:]}")
    return finalize_analysis(analysis_dir, analysis_dir / "glmm_result.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    preflight_command = commands.add_parser("preflight")
    preflight_command.add_argument("--dataset-root", type=Path, required=True)
    prepare_dataset_command = commands.add_parser("prepare-dataset")
    prepare_dataset_command.add_argument("--source-archive", type=Path, required=True)
    prepare_dataset_command.add_argument("--output-dir", type=Path, required=True)
    prepare_command = commands.add_parser("prepare")
    prepare_command.add_argument("--dataset-root", type=Path, required=True)
    for name in ("status", "fetch", "verify", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight(args.dataset_root.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if args.command == "prepare-dataset":
        print(json.dumps(prepare_dataset(args.source_archive.resolve(), args.output_dir.resolve()), ensure_ascii=False, indent=2))
        return 0
    if args.command == "prepare":
        print(json.dumps(prepare(args.dataset_root.resolve()), ensure_ascii=False, indent=2))
        return 0
    run_dir = args.run_dir.resolve()
    spec = json.loads((run_dir / "submission.json").read_text("utf-8"))
    status = query_status(spec["kernel_id"], ROOT)
    if args.command == "status":
        atomic_write_json(run_dir / "kaggle_status.json", status)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["returncode"] == 0 else 1
    if args.command == "fetch":
        if status["returncode"] or status["status"] != "COMPLETE":
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return 1
        temporary, destination = run_dir / ".fetch.tmp", run_dir / "fetched"
        if temporary.exists() or destination.exists():
            raise FileExistsError("refusing to overwrite existing fetch")
        temporary.mkdir(parents=True)
        result = subprocess.run(
            ["kaggle", "kernels", "output", spec["kernel_id"], "-p", str(temporary)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        shutil.move(str(temporary), str(destination))
        atomic_write_json(run_dir / "kaggle_status.json", status)
        print(json.dumps({"status": "FETCHED", "destination": str(destination)}, indent=2))
        return 0
    if args.command == "verify":
        result = verify(run_dir, spec)
        verification_dir = run_dir / "verification"
        verification_dir.mkdir(exist_ok=False)
        atomic_write_json(verification_dir / "verification.json", result)
        if result["verification_status"] == "VERIFIED":
            for path in _artifact(run_dir, spec).rglob("*"):
                if path.is_file():
                    path.chmod(0o444)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["verification_status"] == "VERIFIED" else 1
    result = analyze(run_dir, spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
