"""Thin CLI for the pre-registered Qwen3.5 Stage 0 backbone audit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from labbs2026.kaggle import atomic_write_json, build_submit_command
from labbs2026.stage0.backbone_calibration import (
    analyze_backbone_artifacts,
    backbone_preflight,
    prepare_backbone_staging,
    query_kaggle_status,
    verify_backbone_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "configs/stage0/qwen35_backbone_calibration.yaml"
RUNTIME = ROOT / "configs/runtime/kaggle_t4_qwen35.yaml"


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight")
    commands.add_parser("prepare")
    for name in ("submit-command", "status", "fetch", "verify", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        result = backbone_preflight(ROOT, AUDIT, RUNTIME)
        _print(result)
        return 0 if result["valid"] else 1
    if args.command == "prepare":
        result = prepare_backbone_staging(ROOT, AUDIT, RUNTIME)
        _print(result)
        return 0
    run_dir = args.run_dir.resolve()
    submission = json.loads((run_dir / "submission.json").read_text("utf-8"))
    if args.command == "submit-command":
        _print({"command": build_submit_command(run_dir / "staging")})
        return 0
    if args.command == "analyze":
        artifact_dir = run_dir / "fetched/artifacts" / submission["run_id"]
        result = analyze_backbone_artifacts(artifact_dir, run_dir / "analysis", AUDIT)
        _print(result)
        return 0
    status = query_kaggle_status(submission["kernel_id"], ROOT)
    if args.command == "status":
        atomic_write_json(run_dir / "kaggle_status.json", status)
        _print(status)
        return 0 if status["returncode"] == 0 else 1
    if args.command == "fetch":
        if status["returncode"] or status["status"] != "COMPLETE":
            _print(status)
            return 1
        destination = run_dir / "fetched"
        temporary = run_dir / ".fetch.tmp"
        if destination.exists() or temporary.exists():
            raise FileExistsError("refusing to overwrite an existing fetch")
        temporary.mkdir(parents=True)
        result = subprocess.run(
            ["kaggle", "kernels", "output", submission["kernel_id"], "-p", str(temporary)],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode:
            _print({"returncode": result.returncode, "error": result.stderr})
            return 1
        shutil.move(str(temporary), str(destination))
        atomic_write_json(run_dir / "kaggle_status.json", status)
        _print({"status": "FETCHED", "destination": str(destination)})
        return 0
    status_record = json.loads((run_dir / "kaggle_status.json").read_text("utf-8"))
    artifact_dir = run_dir / "fetched/artifacts" / submission["run_id"]
    result = verify_backbone_artifacts(artifact_dir, submission, status_record["status"])
    verification = run_dir / "verification"
    verification.mkdir(exist_ok=False)
    atomic_write_json(verification / "verification.json", result)
    _print(result)
    return 0 if result["verification_status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
