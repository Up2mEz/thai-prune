"""Thin Kaggle lifecycle CLI for the authorized Paddle/Wayu smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

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
from labbs2026.stage0.measurement_diagnostic import query_status
from labbs2026.stage0.paddle_wayu_smoke import (
    audit_locked_set,
    build_workload,
    verify_fetched_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_engineering_smoke.yaml"
RUNTIME = ROOT / "configs/runtime/kaggle_t4_paddle_wayu.yaml"
WORKER = ROOT / "infra/kaggle/paddle_wayu_engineering_smoke_worker.py"
KERNEL = {
    "id": "thanakritsamoena/labbs2026-paddle-wayu-smoke",
    "title": "LabBS2026 Paddle Wayu Engineering Smoke",
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
    import yaml

    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _clean_tracked_tree() -> bool:
    return (
        subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0
        and subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=ROOT
        ).returncode
        == 0
    )


def _git_blob_sha256(relative: str, revision: str = "HEAD") -> str:
    payload = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(payload).hexdigest()


def preflight() -> dict[str, Any]:
    config = _yaml(CONFIG)
    runtime = load_runtime(RUNTIME)
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    remote, remote_error = _check_remote_ref(
        ROOT, runtime["source"]["repository_url"], runtime["source"]["remote_ref"]
    )
    locked = audit_locked_set(config, _yaml(ROOT / config["source_design"]))
    workload = build_workload(config)
    checks = {
        "tracked_tree_clean": _clean_tracked_tree(),
        "remote_exact_sha": remote_error is None and remote == git_sha,
        "authorized_status": config["status"]
        == "APPROVED_FOR_ENGINEERING_SMOKE_ONLY",
        "scientific_use_forbidden": config["scientific_use"] == "FORBIDDEN",
        "all_prohibitions_false": not any(config["prohibitions"].values()),
        "exact_40_calls": len(workload) == 40,
        "two_models": len(config["models"]) == 2,
        "five_pairs": len(set(config["selection"]["pair_ids"])) == 5,
        "locked_pair_count_zero": locked["locked_pair_count"] == 0
        and locked["valid"],
        "source_bundle_hash": sha256_file(ROOT / config["source_bundle"])
        == config["source_bundle_sha256"],
        "prompt_exact": config["prompt"] == "OCR:",
    }
    return {
        "schema_version": 1,
        "valid": all(checks.values()),
        "git_sha": git_sha,
        "remote_sha": remote,
        "remote_error": remote_error,
        "checks": checks,
        "locked_set_audit": locked,
    }


def prepare() -> dict[str, Any]:
    check = preflight()
    if not check["valid"]:
        raise RuntimeError(f"engineering smoke preflight failed: {check}")
    config = _yaml(CONFIG)
    runtime = load_runtime(RUNTIME)
    git_sha = check["git_sha"]
    paths = [
        CONFIG.relative_to(ROOT).as_posix(),
        RUNTIME.relative_to(ROOT).as_posix(),
        WORKER.relative_to(ROOT).as_posix(),
        "src/labbs2026/stage0/paddle_wayu_smoke.py",
        "configs/stage0/calibration_design.yaml",
        config["source_bundle"],
        "uv.lock",
        runtime["uv"]["transformers_override_lock"],
    ]
    hashes = {path: _git_blob_sha256(path, git_sha) for path in paths}
    config_relative = CONFIG.relative_to(ROOT).as_posix()
    runtime_relative = RUNTIME.relative_to(ROOT).as_posix()
    run_id = (
        f"kaggle-paddle-wayu-smoke-{git_sha[:12]}-"
        f"{hashes[config_relative][:8]}"
    )
    spec = {
        "schema_version": 1,
        "run_type": "PADDLE_WAYU_NON_SCIENTIFIC_40_CALL_ENGINEERING_SMOKE",
        "run_id": run_id,
        "git_sha": git_sha,
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "source_hashes": hashes,
        "config_path": config_relative,
        "config_sha256": hashes[config_relative],
        "runtime_path": runtime_relative,
        "runtime_sha256": hashes[runtime_relative],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "requested_accelerator": runtime["accelerator"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "transformers_override_lock": runtime["uv"][
            "transformers_override_lock"
        ],
        "kernel_id": KERNEL["id"],
        "stage_s0_authorized": False,
        "locked_validation_authorized": False,
        "compression_authorized": False,
        "created_at_utc": utc_now(),
    }
    run_dir = ROOT / "runs/kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    atomic_write_text(staging / "worker.py", render_worker(WORKER.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", KERNEL)
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", check)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "submit_command": build_submit_command(staging),
    }


def _artifact_dir(run_dir: Path, spec: dict[str, Any]) -> Path:
    return run_dir / "fetched/artifacts" / spec["run_id"]


def _write_report(run_dir: Path, spec: dict[str, Any]) -> Path:
    artifact = _artifact_dir(run_dir, spec)
    manifest = json.loads((artifact / "manifest.json").read_text("utf-8"))
    runtime = json.loads((artifact / "runtime_vram_report.json").read_text("utf-8"))
    locked = json.loads((artifact / "locked_set_audit.json").read_text("utf-8"))
    repeats = json.loads(
        (artifact / "repeat_consistency_report.json").read_text("utf-8")
    )
    models = json.loads(
        (artifact / "model_revision_manifest.json").read_text("utf-8")
    )["models"]
    report = run_dir / "analysis/ENGINEERING_SMOKE_REPORT.md"
    report.parent.mkdir(parents=True, exist_ok=False)
    lines = [
        "# Paddle/Wayu Engineering Smoke Report",
        "",
        "> NON-SCIENTIFIC ENGINEERING OBSERVATIONS ONLY. No accuracy or model ranking was calculated.",
        "",
        f"- Run: `{manifest['run_id']}`",
        f"- Status: `{manifest['status']}`",
        f"- Calls: `{manifest['call_count']}`",
        f"- Locked pairs exposed: `{locked['locked_pair_count']}`",
        f"- Exact repeats consistent: `{repeats['all_exact_repeats_consistent']}`",
        f"- GPU: `{runtime['gpu']['observed_gpu_name']}`",
        f"- Total runtime seconds: `{runtime['total_seconds']}`",
        "",
        "## Exact model revisions",
        "",
    ]
    for model in models:
        lines.append(
            f"- {model['role']}: `{model['model_id']}@{model['resolved_revision']}`; "
            f"class `{model['model_class']}`; processor `{model['processor_class']}`"
        )
    lines.extend(["", "## Peak VRAM and runtime", ""])
    for model_runtime in runtime["models"]:
        lines.append(
            f"- {model_runtime['role']}: load `{model_runtime['model_load_seconds']:.3f}s`; "
            f"20 calls `{model_runtime['inference_seconds_total']:.3f}s`; "
            f"peak allocated `{model_runtime['peak_cuda_allocated_bytes']}` bytes; "
            f"peak reserved `{model_runtime['peak_cuda_reserved_bytes']}` bytes"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"`{manifest['recommendation']}`",
            "",
            "This is a proposal for human review, not automatic Stage S0 authorization.",
            "",
            "Terminal state: `HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE`",
            "",
        ]
    )
    atomic_write_text(report, "\n".join(lines))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight")
    commands.add_parser("prepare")
    for name in ("status", "fetch", "verify", "report"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if args.command == "prepare":
        result = prepare()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    run_dir = args.run_dir.resolve()
    spec = json.loads((run_dir / "submission.json").read_text("utf-8"))
    if args.command == "report":
        path = _write_report(run_dir, spec)
        print(json.dumps({"report": str(path)}, ensure_ascii=False, indent=2))
        return 0
    status = query_status(spec["kernel_id"], ROOT)
    if args.command == "status":
        atomic_write_json(run_dir / "kaggle_status.json", status)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["returncode"] == 0 else 1
    if args.command == "fetch":
        if status["returncode"] or status["status"] != "COMPLETE":
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return 1
        temporary = run_dir / ".fetch.tmp"
        destination = run_dir / "fetched"
        if temporary.exists() or destination.exists():
            raise FileExistsError("refusing to overwrite existing fetch")
        temporary.mkdir(parents=True)
        result = subprocess.run(
            ["kaggle", "kernels", "output", spec["kernel_id"], "-p", str(temporary)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        shutil.move(str(temporary), str(destination))
        atomic_write_json(run_dir / "kaggle_status.json", status)
        print(json.dumps({"status": "FETCHED", "destination": str(destination)}, indent=2))
        return 0
    status_record = json.loads((run_dir / "kaggle_status.json").read_text("utf-8"))
    result = verify_fetched_artifacts(
        _artifact_dir(run_dir, spec), spec, status_record["status"]
    )
    verification_dir = run_dir / "verification"
    verification_dir.mkdir(exist_ok=False)
    atomic_write_json(verification_dir / "verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verification_status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
