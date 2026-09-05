"""Thin CLI for the minimal Step 3 Kaggle backend proof."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from labbs2026.kaggle import (
    atomic_write_json,
    build_submit_command,
    parse_kaggle_status,
    phase1_preflight,
    prepare_staging,
    verify_artifacts,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/step3/qwen25_vl_3b.yaml"
DEFAULT_RUNTIME = ROOT / "configs/runtime/kaggle_t4.yaml"


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _submission(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "submission.json").read_text(encoding="utf-8"))


def _query_status(kernel_id: str) -> dict[str, Any]:
    result = subprocess.run(
        ["kaggle", "kernels", "status", kernel_id],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    raw = (result.stdout or result.stderr).strip()
    return {
        "command": ["kaggle", "kernels", "status", kernel_id],
        "returncode": result.returncode,
        "status": parse_kaggle_status(raw),
        "raw_output": raw,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    preflight_parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    prepare_parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)

    command_parser = subparsers.add_parser("submit-command")
    command_parser.add_argument("--run-dir", type=Path, required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--run-dir", type=Path, required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--run-dir", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "preflight":
        result = phase1_preflight(ROOT, args.config, args.runtime)
        _print(result)
        return 0 if result["valid"] else 1
    if args.command == "prepare":
        result = prepare_staging(ROOT, args.config, args.runtime)
        _print(result)
        return 0

    run_dir = args.run_dir.resolve()
    submission = _submission(run_dir)
    if args.command == "submit-command":
        staging_dir = run_dir / "staging"
        _print({"command": build_submit_command(staging_dir)})
        return 0
    if args.command == "status":
        status = _query_status(submission["kernel_id"])
        atomic_write_json(run_dir / "kaggle_status.json", status)
        _print(status)
        return 0 if status["returncode"] == 0 else 1
    if args.command == "fetch":
        status = _query_status(submission["kernel_id"])
        if status["returncode"] != 0 or status["status"] != "COMPLETE":
            _print(status)
            return 1
        destination = run_dir / "fetched"
        temporary = run_dir / ".fetch.tmp"
        if destination.exists() or temporary.exists():
            raise FileExistsError(
                "fetch destination already exists; refusing overwrite"
            )
        temporary.mkdir(parents=True)
        result = subprocess.run(
            [
                "kaggle",
                "kernels",
                "output",
                submission["kernel_id"],
                "-p",
                str(temporary),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _print(
                {
                    "returncode": result.returncode,
                    "error": result.stderr.strip(),
                    "partial_fetch": str(temporary),
                }
            )
            return 1
        temporary.replace(destination)
        atomic_write_json(run_dir / "kaggle_status.json", status)
        _print({"status": "FETCHED", "destination": str(destination)})
        return 0
    if args.command == "verify":
        status_path = run_dir / "kaggle_status.json"
        if not status_path.is_file():
            raise FileNotFoundError(
                "kaggle_status.json is required; run status or fetch first"
            )
        status = json.loads(status_path.read_text(encoding="utf-8"))
        artifact_dir = run_dir / "fetched" / "artifacts" / submission["run_id"]
        verification = verify_artifacts(artifact_dir, submission, status["status"])
        verification_dir = run_dir / "verification"
        verification_dir.mkdir(exist_ok=False)
        atomic_write_json(verification_dir / "verification.json", verification)
        _print(verification)
        return 0 if verification["verification_status"] == "VERIFIED" else 1
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
