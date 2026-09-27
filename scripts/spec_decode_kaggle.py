"""Prepare (and optionally submit) the SPEC_DECODE_S1 Kaggle run (Track A)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.kaggle import (
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    kernel_id,
    load_local_config,
    local_remote_ref,
    locked_package_versions,
    render_worker,
    sha256_file,
    utc_now,
)
from labbs2026.spec_decode.design import drop_arm, estimated_t4_hours

KERNEL_SLUG = "labbs2026-spec-decode-s1"
CONFIG = "configs/spec_decode/s1.yaml"

HASHED = (
    CONFIG,
    "configs/thai_marks/typhoon_card_prompt.txt",
    "src/labbs2026/spec_decode/__init__.py",
    "src/labbs2026/spec_decode/design.py",
    "src/labbs2026/spec_decode/identity.py",
    "src/labbs2026/spec_decode/remote.py",
    "src/labbs2026/spec_decode/runtime.py",
    "src/labbs2026/thai_marks/__init__.py",
    "src/labbs2026/thai_marks/normalize.py",
    "src/labbs2026/thai_marks/orthography.py",
    "src/labbs2026/thai_marks/remote.py",
    "src/labbs2026/thai_marks/runtime.py",
    "src/labbs2026/thai_marks/split.py",
    "uv.lock",
)
REPOSITORY = "https://github.com/Up2mEz/thai-prune.git"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def preflight(root: Path, remote_ref: str) -> str:
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked files have uncommitted changes; commit before staging")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "ls-remote", REPOSITORY, remote_ref)
    if not remote or remote.split()[0] != head:
        raise RuntimeError(f"remote ref {remote_ref!r} is not at HEAD; push first")
    return head


def budget(config: dict, limit: int, calibration_items: int | None,
           t1_seconds_per_item: float | None) -> tuple[dict, list[list[str]]]:
    """Registration §7. Smoke runs (`limit`) are exempt; a full run must supply T1's timing."""
    rule = config["budget"]
    rotation = [list(order) for order in config["arm_rotation"]]
    if limit:
        return {"rule": "smoke_exempt", "limit": limit}, rotation
    if calibration_items is None or t1_seconds_per_item is None:
        raise SystemExit("a full run needs --calibration-items and --t1-seconds-per-item "
                         "(registration §7)")
    hours = estimated_t4_hours(calibration_items, t1_seconds_per_item, len(rotation[0]))
    record = {"rule": "registration_s7", "calibration_items": calibration_items,
              "t1_seconds_per_item": t1_seconds_per_item, "estimated_t4_hours": hours,
              "max_t4_hours": rule["max_t4_hours"], "dropped": None}
    if hours > float(rule["max_t4_hours"]):
        rotation = drop_arm(rotation, rule["drop_if_over"])
        record["dropped"] = rule["drop_if_over"]
        record["estimated_t4_hours_after_drop"] = estimated_t4_hours(
            calibration_items, t1_seconds_per_item, len(rotation[0]))
    return record, rotation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--limit", type=int, default=0,
                        help="engineering smoke only: run the first N timed calibration items")
    parser.add_argument("--calibration-items", type=int)
    parser.add_argument("--t1-seconds-per-item", type=float,
                        help="T1 TYPHOON_CARD mean seconds per item, slower of the two models")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config = yaml.safe_load((root / CONFIG).read_text("utf-8"))
    if config["status"] != "APPROVED":
        raise SystemExit(f"{CONFIG} status is {config['status']!r}, not APPROVED")
    budget_record, rotation = budget(config, args.limit, args.calibration_items,
                                     args.t1_seconds_per_item)
    local = load_local_config(root)
    remote_ref = local.get("remote_ref") or local_remote_ref(root)
    git_sha = preflight(root, remote_ref)
    suffix = f"-smoke{args.limit}" if args.limit else ""
    run_id = f"kaggle-spec-decode-s1-{git_sha[:12]}{suffix}"
    arms = {name: dict(config["arms"][name] or {}) for name in rotation[0]}

    spec = {
        "schema_version": 1,
        "run_id": run_id,
        "repository_url": REPOSITORY,
        "remote_ref": remote_ref,
        "git_sha": git_sha,
        "expected_file_hashes": {p: sha256_file(root / p) for p in HASHED},
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "uv_bootstrap_version": "0.11.25",
        "uv_sync_args": ["--frozen", "--extra", "model", "--extra", "bench"],
        "python_version": "3.12",
        "source_dir": "/tmp/labbs2026-source",
        "output_root": "/kaggle/working/artifacts",
        "tests": ["s1"],
        "limit": args.limit,
        "models": config["models"],
        "benchmark_repo": config["benchmark"]["repo"],
        "benchmark_revision": config["benchmark"]["revision"],
        "benchmark_split": config["benchmark"]["split"],
        "tasks": config["benchmark"]["tasks"],
        "split_seed": config["split"]["seed"],
        "calibration_fraction": config["split"]["calibration_fraction"],
        "typhoon_prompt_file": config["prompt"]["file"],
        "typhoon_prompt_sha256": config["prompt"]["sha256"],
        "dtype_preferred": config["runtime"]["dtype_preferred"],
        "dtype_fallback": config["runtime"]["dtype_fallback"],
        "max_new_tokens": config["runtime"]["max_new_tokens"],
        "warmup_items": config["runtime"]["warmup_items"],
        "arms": arms,
        "arm_rotation": rotation,
        "budget": budget_record,
        "created_at_utc": utc_now(),
    }

    run_dir = root / "runs" / "kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / "infra/kaggle/spec_decode_worker.py"
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", {
        "id": kernel_id(root, KERNEL_SLUG), "title": "LabBS2026 Spec Decode S1", "code_file": "worker.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
        "model_sources": [],
    })
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    print(json.dumps({"run_id": run_id, "git_sha": git_sha, "limit": args.limit,
                      "arms": rotation[0], "budget": budget_record, "staging": str(staging)},
                     indent=1))
    if args.submit:
        result = subprocess.run(build_submit_command(staging), capture_output=True, text=True)
        print(result.stdout or result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
