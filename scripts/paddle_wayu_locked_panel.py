"""Kaggle lifecycle CLI for the authorized frozen Paddle/Wayu locked panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
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
from labbs2026.stage0.locked_panel_bundle import build_locked_source_bundle
from labbs2026.stage0.locked_panel_analysis import finalize_analysis, write_analysis_inputs
from labbs2026.stage0.measurement_diagnostic import query_status


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_locked_panel_execution.yaml"
WORKER = ROOT / "infra/kaggle/paddle_wayu_locked_panel_worker.py"
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
    "dataset_sources": [],
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


def preflight() -> dict[str, Any]:
    config = _yaml(CONFIG)
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
        "human_authorization": config["status"] == "HUMAN_APPROVED_FOR_FROZEN_LOCKED_PANEL_EXECUTION",
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
    return {
        "schema_version": 1,
        "valid": all(checks.values()),
        "git_sha": git_sha,
        "remote_sha": remote,
        "remote_error": remote_error,
        "frozen_design_git_sha": frozen_sha,
        "checks": checks,
    }


def prepare() -> dict[str, Any]:
    check = preflight()
    if not check["valid"]:
        raise RuntimeError(f"locked-panel preflight failed: {check}")
    config = _yaml(CONFIG)
    runtime = load_runtime(ROOT / config["runtime_config"])
    git_sha = check["git_sha"]
    frozen_bytes = _git_bytes(config["frozen_design_git_sha"], config["frozen_design_path"])
    run_id = f"kaggle-paddle-wayu-locked-panel-{git_sha[:12]}"
    run_dir = ROOT / "runs/kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    atomic_write_text(staging / "frozen_design.yaml", frozen_bytes.decode("utf-8"))
    bundle = build_locked_source_bundle(
        ROOT / config["source_review_dir"],
        ROOT / "configs/stage0/calibration_design.yaml",
        staging / "locked_source_bundle.zip",
    )
    paths = [
        CONFIG.relative_to(ROOT).as_posix(),
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
        "frozen_design_git_sha": config["frozen_design_git_sha"],
        "frozen_design_sha256": config["frozen_design_sha256"],
        "locked_panel_authorized": True,
        "scientific_output_unseal_during_execution": False,
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "source_hashes": hashes,
        "locked_source_bundle_sha256": bundle["bundle_sha256"],
        "staged_frozen_design_path": "/kaggle/working/frozen_design.yaml",
        "staged_locked_bundle_path": "/kaggle/working/locked_source_bundle.zip",
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
    atomic_write_text(staging / "worker.py", render_worker(WORKER.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", KERNEL)
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", check)
    atomic_write_json(run_dir / "locked_source_bundle_manifest.json", bundle)
    return {"run_id": run_id, "run_dir": str(run_dir), "submit_command": build_submit_command(staging)}


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
            "frozen_design_sha_match": manifest["frozen_design_git_sha"] == spec["frozen_design_git_sha"],
            "frozen_design_hash_match": manifest["frozen_design_sha256"] == spec["frozen_design_sha256"],
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
    commands.add_parser("preflight")
    commands.add_parser("prepare")
    for name in ("status", "fetch", "verify", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if args.command == "prepare":
        print(json.dumps(prepare(), ensure_ascii=False, indent=2))
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
