"""Thin CLI for the frozen Qwen3.5 measurement-contract pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from labbs2026.kaggle import _check_remote_ref, atomic_write_json, atomic_write_text, build_submit_command, load_runtime, render_worker, sha256_file, utc_now
from labbs2026.stage0.measurement_contract_pilot_run import analyze
from labbs2026.stage0.measurement_diagnostic import query_status

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/qwen35_measurement_contract_pilot.yaml"
RUNTIME = ROOT / "configs/runtime/kaggle_t4_qwen35.yaml"
WORKER = ROOT / "infra/kaggle/qwen35_measurement_contract_pilot_worker.py"
KERNEL = {"id": "thanakritsamoena/labbs2026-qwen3-5-contract-pilot", "title": "LabBS2026 Qwen3.5 Contract Pilot", "code_file": "worker.py", "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [], "kernel_sources": [], "model_sources": []}


def _yaml(path: Path):
    import yaml
    return yaml.safe_load(path.read_text("utf-8"))


def _clean() -> bool:
    return subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0 and subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0


def _git_blob_sha256(relative: str, revision: str = "HEAD") -> str:
    payload = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(payload).hexdigest()


def preflight() -> dict:
    config, runtime = _yaml(CONFIG), load_runtime(RUNTIME)
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    remote, error = _check_remote_ref(ROOT, runtime["source"]["repository_url"], runtime["source"]["remote_ref"])
    selected = [p for ps in config["selection"]["selected_pairs"].values() for p in ps]
    a = config["conditions"]["A_forced_choice"]
    checks = {
        "tracked_tree_clean": _clean(), "remote_exact_sha": error is None and remote == git_sha,
        "authorized_frozen_status": config["status"] == "FROZEN_AUTHORIZED_FOR_PILOT_INFERENCE" and config["prohibitions"]["inference_authorized"] is True,
        "all_other_prohibitions": all(v is False for k, v in config["prohibitions"].items() if k != "inference_authorized"),
        "selected_25_unique": len(selected) == len(set(selected)) == 25,
        "source_bundle_hash": sha256_file(ROOT / config["source_bundle"]) == config["source_bundle_sha256"],
        "A_reference_hash": _git_blob_sha256(a["frozen_reference"]) == a["frozen_reference_sha256"],
    }
    return {"schema_version": 1, "valid": all(checks.values()), "git_sha": git_sha, "remote_sha": remote, "remote_error": error, "checks": checks}


def prepare() -> dict:
    check = preflight()
    if not check["valid"]:
        raise RuntimeError("pilot preflight failed")
    config, runtime, git_sha = _yaml(CONFIG), load_runtime(RUNTIME), check["git_sha"]
    paths = [CONFIG.relative_to(ROOT).as_posix(), RUNTIME.relative_to(ROOT).as_posix(), WORKER.relative_to(ROOT).as_posix(), config["protocol"], config["source_bundle"], config["model"]["config"], config["conditions"]["A_forced_choice"]["frozen_reference"], config["conditions"]["A_forced_choice"]["provenance_record"], "configs/stage0/candidate_pairs.yaml", "uv.lock", runtime["uv"]["qwen35_override_lock"]]
    hashes = {p: _git_blob_sha256(p, git_sha) for p in paths}
    run_id = f"kaggle-qwen35-contract-{git_sha[:12]}-{hashes[CONFIG.relative_to(ROOT).as_posix()][:8]}"
    spec = {"schema_version": 1, "run_type": "QWEN35_FROZEN_25_PAIR_MEASUREMENT_CONTRACT_PILOT", "run_id": run_id, "git_sha": git_sha, "repository_url": runtime["source"]["repository_url"], "remote_ref": runtime["source"]["remote_ref"], "source_hashes": hashes, "config_path": CONFIG.relative_to(ROOT).as_posix(), "runtime_path": RUNTIME.relative_to(ROOT).as_posix(), "source_dir": runtime["paths"]["source_dir"], "output_root": runtime["paths"]["output_root"], "requested_accelerator": runtime["accelerator"], "environment_contract": runtime["evidence_environment_contract"], "python_version": runtime["python"]["version"], "uv_bootstrap_version": runtime["uv"]["bootstrap_version"], "uv_sync_args": runtime["uv"]["sync_args"], "qwen35_override_lock": runtime["uv"]["qwen35_override_lock"], "kernel_id": KERNEL["id"], "locked_validation_authorized": False, "compression_status": "NOT_RUN", "gate_0_status": "NOT_RUN", "created_at_utc": utc_now()}
    run_dir, staging = ROOT / "runs/kaggle" / run_id, ROOT / "runs/kaggle" / run_id / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    atomic_write_text(staging / "worker.py", render_worker(WORKER.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", KERNEL)
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", check)
    return {"run_id": run_id, "run_dir": str(run_dir), "submit_command": build_submit_command(staging)}


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight"); sub.add_parser("prepare")
    for name in ("status", "fetch", "verify", "analyze"):
        p = sub.add_parser(name); p.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight": result = preflight()
    elif args.command == "prepare": result = prepare()
    else:
        run_dir = args.run_dir.resolve(); spec = json.loads((run_dir / "submission.json").read_text("utf-8")); artifact = run_dir / "fetched/artifacts" / spec["run_id"]
        if args.command == "status": result = query_status(spec["kernel_id"], ROOT)
        elif args.command == "fetch":
            status = query_status(spec["kernel_id"], ROOT)
            if status["status"] != "COMPLETE": result = status
            else:
                temp, destination = run_dir / ".fetch.tmp", run_dir / "fetched"; temp.mkdir(parents=True, exist_ok=False)
                call = subprocess.run(["kaggle", "kernels", "output", spec["kernel_id"], "-p", str(temp)], cwd=ROOT, capture_output=True, text=True)
                if call.returncode: raise RuntimeError(call.stderr)
                shutil.move(str(temp), str(destination)); atomic_write_json(run_dir / "kaggle_status.json", status); result = {"status": "FETCHED", "destination": str(destination)}
        elif args.command == "verify":
            manifest = json.loads((artifact / "submission_manifest.json").read_text("utf-8")); checksum_ok = all((artifact / rel).is_file() and sha256_file(artifact / rel) == sha for sha, rel in (line.split("  ", 1) for line in (artifact / "checksums.sha256").read_text("utf-8").splitlines()))
            checks = {"success": (artifact / "SUCCESS.json").is_file(), "no_failure": not (artifact / "FAILURE.json").exists(), "checksums": checksum_ok, "git_sha": manifest["git_sha"] == spec["git_sha"], "rows": manifest["B_rows"] == manifest["C_rows"] == 200, "pairs": manifest["selected_pair_count"] == 25, "locked_zero": manifest["locked_validation_pair_count_exposed_to_model"] == 0, "pixel_identity": manifest["target_pixel_identity_pass_count"] == 200, "no_compression": manifest["compression_status"] == "NOT_RUN", "gate0_not_run": manifest["gate_0_status"] == "NOT_RUN"}
            result = {"verification_status": "VERIFIED" if all(checks.values()) else "INVALID", "checks": checks}; (run_dir / "verification").mkdir(exist_ok=False); atomic_write_json(run_dir / "verification/verification.json", result)
        else: result = analyze(artifact, run_dir / "analysis", CONFIG, ROOT / _yaml(CONFIG)["conditions"]["A_forced_choice"]["frozen_reference"])
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
