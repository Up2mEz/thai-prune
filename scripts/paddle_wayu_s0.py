"""Thin Kaggle lifecycle CLI for authorized Paddle/Wayu S0."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from typing import Any

from labbs2026.kaggle import _check_remote_ref, atomic_write_json, atomic_write_text, build_submit_command, load_runtime, render_worker, sha256_file, utc_now
from labbs2026.stage0.measurement_diagnostic import query_status
from labbs2026.stage0.paddle_wayu_s0 import audit_selection, build_workload, load_yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_s0_open_calibration.yaml"
RUNTIME = ROOT / "configs/runtime/kaggle_t4_paddle_wayu.yaml"
WORKER = ROOT / "infra/kaggle/paddle_wayu_s0_worker.py"
KERNEL = {"id": "thanakritsamoena/labbs2026-paddle-wayu-s0-open-calibration", "title": "LabBS2026 Paddle Wayu S0 Open Calibration", "code_file": "worker.py", "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [], "kernel_sources": [], "model_sources": []}

def _tracked_clean() -> bool:
    return subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode == 0 and subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0

def _blob_hash(relative: str, revision: str) -> str:
    payload = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=ROOT, check=True, capture_output=True).stdout
    return hashlib.sha256(payload).hexdigest()

def _load_render_rows(bundle: Path) -> list[dict[str, Any]]:
    import zipfile
    with zipfile.ZipFile(bundle) as archive: return json.loads(archive.read("render_manifest.json"))

def preflight() -> dict[str, Any]:
    config, runtime = load_yaml(CONFIG), load_runtime(RUNTIME)
    design, inventory = load_yaml(ROOT / config["source_design"]), load_yaml(ROOT / config["candidate_inventory"])
    workload = build_workload(config, design, inventory, _load_render_rows(ROOT / config["source_bundle"]))
    audit = audit_selection(config, design, workload)
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    remote, error = _check_remote_ref(ROOT, runtime["source"]["repository_url"], runtime["source"]["remote_ref"])
    per_model = {role: sum(row["model_role"] == role for row in workload) for role in ("BASE", "SPECIALIZED")}
    cross = {}
    for row in workload: cross.setdefault((row["pair_id"], row["condition_id"], row["member"]), []).append(row)
    checks = {
        "tracked_tree_clean": _tracked_clean(), "remote_exact_sha": error is None and remote == git_sha,
        "authorized_status": config["status"] == "APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY",
        "all_prohibitions_false": not any(config["prohibitions"].values()), "exact_1520_calls": len(workload) == 1520,
        "760_calls_per_model": per_model == {"BASE": 760, "SPECIALIZED": 760}, "selection_audit": audit["valid"],
        "locked_pair_count_zero": audit["locked_pair_count"] == 0,
        "identical_images_across_models": all(len(rows) == 2 and rows[0]["image_sha256"] == rows[1]["image_sha256"] for rows in cross.values()),
        "source_bundle_hash": sha256_file(ROOT / config["source_bundle"]) == config["source_bundle_sha256"],
        "prompt_exact": config["prompt"] == "OCR:", "parser_exact": config["parser"]["primary"] == "PYTHON_STRIP_LEADING_TRAILING_WHITESPACE_ONLY",
    }
    return {"schema_version": 1, "valid": all(checks.values()), "git_sha": git_sha, "remote_sha": remote, "remote_error": error, "checks": checks, "locked_set_audit": audit}

def prepare() -> dict[str, Any]:
    check = preflight()
    if not check["valid"]: raise RuntimeError(f"S0 preflight failed: {check}")
    config, runtime, git_sha = load_yaml(CONFIG), load_runtime(RUNTIME), check["git_sha"]
    paths = [CONFIG.relative_to(ROOT).as_posix(), RUNTIME.relative_to(ROOT).as_posix(), WORKER.relative_to(ROOT).as_posix(), "src/labbs2026/stage0/paddle_wayu_s0.py", "src/labbs2026/stage0/paddle_wayu_smoke.py", "configs/stage0/calibration_design.yaml", "configs/stage0/candidate_pairs.yaml", config["source_bundle"], "uv.lock", runtime["uv"]["transformers_override_lock"]]
    hashes = {path: _blob_hash(path, git_sha) for path in paths}; config_rel = CONFIG.relative_to(ROOT).as_posix(); runtime_rel = RUNTIME.relative_to(ROOT).as_posix()
    run_id = f"kaggle-paddle-wayu-s0-{git_sha[:12]}-{hashes[config_rel][:8]}"
    spec = {"schema_version": 1, "run_type": "PADDLE_WAYU_S0_OPEN_CALIBRATION_BASELINE", "run_id": run_id, "git_sha": git_sha, "repository_url": runtime["source"]["repository_url"], "remote_ref": runtime["source"]["remote_ref"], "source_hashes": hashes, "config_path": config_rel, "config_sha256": hashes[config_rel], "runtime_path": runtime_rel, "runtime_sha256": hashes[runtime_rel], "source_dir": runtime["paths"]["source_dir"], "output_root": runtime["paths"]["output_root"], "requested_accelerator": runtime["accelerator"], "python_version": runtime["python"]["version"], "uv_bootstrap_version": runtime["uv"]["bootstrap_version"], "uv_sync_args": runtime["uv"]["sync_args"], "transformers_override_lock": runtime["uv"]["transformers_override_lock"], "kernel_id": KERNEL["id"], "s0_open_calibration_authorized": True, "locked_validation_authorized": False, "compression_authorized": False, "created_at_utc": utc_now()}
    run_dir = ROOT / "runs/kaggle" / run_id; staging = run_dir / "staging"; staging.mkdir(parents=True, exist_ok=False)
    atomic_write_text(staging / "worker.py", render_worker(WORKER.read_text("utf-8"), spec)); atomic_write_json(staging / "kernel-metadata.json", KERNEL); atomic_write_json(run_dir / "submission.json", spec); atomic_write_json(run_dir / "preflight.json", check)
    return {"run_id": run_id, "run_dir": str(run_dir), "submit_command": build_submit_command(staging)}

def _artifact(run_dir: Path, spec: dict[str, Any]) -> Path: return run_dir / "fetched/artifacts" / spec["run_id"]

def verify(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    artifact = _artifact(run_dir, spec); status = json.loads((run_dir / "kaggle_status.json").read_text("utf-8"))
    checks = {"kaggle_complete": status["status"] == "COMPLETE", "success_present": (artifact / "SUCCESS.json").is_file(), "failure_absent": not (artifact / "FAILURE.json").exists()}
    if checks["success_present"]:
        manifest = json.loads((artifact / "manifest.json").read_text("utf-8")); audit = json.loads((artifact / "locked_set_audit.json").read_text("utf-8")); analysis = json.loads((artifact / "analysis.json").read_text("utf-8"))
        checksum_lines = (artifact / "checksums.sha256").read_text("utf-8").splitlines()
        checksum_ok = all(sha256_file(artifact / line.split("  ", 1)[1]) == line.split("  ", 1)[0] for line in checksum_lines)
        checks.update({"run_id_match": manifest["run_id"] == spec["run_id"], "git_sha_match": manifest["git_sha"] == spec["git_sha"], "config_hash_match": manifest["config_sha256"] == spec["config_sha256"], "exact_1520_calls": manifest["call_count"] == 1520, "exact_95_pairs": manifest["pair_count"] == 95, "locked_pair_count_zero": audit["locked_pair_count"] == 0 and audit["valid"], "terminal_stop": manifest["terminal_state"] == "HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION", "analysis_scope": analysis["analysis_scope"] == "S0_OPEN_CALIBRATION_BASELINE_ONLY"})
        checks["artifact_checksums"] = checksum_ok
    return {"schema_version": 1, "verification_status": "VERIFIED" if checks and all(checks.values()) else "FAILED", "checks": checks}

def main() -> int:
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight"); commands.add_parser("prepare")
    for name in ("status", "fetch", "verify"):
        command = commands.add_parser(name); command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = preflight(); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["valid"] else 1
    if args.command == "prepare": print(json.dumps(prepare(), ensure_ascii=False, indent=2)); return 0
    run_dir = args.run_dir.resolve(); spec = json.loads((run_dir / "submission.json").read_text("utf-8")); status = query_status(spec["kernel_id"], ROOT)
    if args.command == "status": atomic_write_json(run_dir / "kaggle_status.json", status); print(json.dumps(status, ensure_ascii=False, indent=2)); return 0 if status["returncode"] == 0 else 1
    if args.command == "fetch":
        if status["returncode"] or status["status"] != "COMPLETE": print(json.dumps(status, ensure_ascii=False, indent=2)); return 1
        temporary, destination = run_dir / ".fetch.tmp", run_dir / "fetched"
        if temporary.exists() or destination.exists(): raise FileExistsError("refusing to overwrite existing fetch")
        temporary.mkdir(parents=True); result = subprocess.run(["kaggle", "kernels", "output", spec["kernel_id"], "-p", str(temporary)], cwd=ROOT, capture_output=True, text=True)
        if result.returncode: raise RuntimeError(result.stderr)
        shutil.move(str(temporary), str(destination)); atomic_write_json(run_dir / "kaggle_status.json", status); print(json.dumps({"status": "FETCHED", "destination": str(destination)}, indent=2)); return 0
    result = verify(run_dir, spec); verification_dir = run_dir / "verification"; verification_dir.mkdir(exist_ok=False); atomic_write_json(verification_dir / "verification.json", result); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["verification_status"] == "VERIFIED" else 1

if __name__ == "__main__": raise SystemExit(main())
