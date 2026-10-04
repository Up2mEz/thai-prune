"""Prepare (and optionally submit) the FIND_VS_READ_F1 Kaggle run (Track C)."""

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

KERNEL_SLUG = "labbs2026-find-vs-read-f1"
CONFIG = "configs/find_vs_read/f1.yaml"
PROMPT_FILE = "configs/thai_marks/typhoon_card_prompt.txt"  # required by thai_marks.remote's loader

HASHED = (
    CONFIG,
    PROMPT_FILE,
    "src/labbs2026/find_vs_read/__init__.py",
    "src/labbs2026/find_vs_read/geometry.py",
    "src/labbs2026/find_vs_read/remote.py",
    "src/labbs2026/find_vs_read/scoring.py",
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--smoke", type=int, default=0,
                        help="engineering smoke: the first N calibration items")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config = yaml.safe_load((root / CONFIG).read_text("utf-8"))
    if config["status"] != "APPROVED":
        raise SystemExit(f"{CONFIG} status is {config['status']!r}, not APPROVED")
    import hashlib

    prompt_digest = hashlib.sha256(config["crop_prompt"].encode("utf-8")).hexdigest()
    if prompt_digest != config["crop_prompt_sha256"]:
        raise SystemExit(f"crop prompt sha256 {prompt_digest} does not match the config")
    if hashlib.sha256(config["question_clause"].encode("utf-8")).hexdigest() != config["question_clause_sha256"]:
        raise SystemExit("question clause sha256 does not match the config")
    local = load_local_config(root)
    remote_ref = local.get("remote_ref") or local_remote_ref(root)
    git_sha = preflight(root, remote_ref)
    suffix = f"-smoke{args.smoke}" if args.smoke else ""
    run_id = f"kaggle-find-vs-read-f1-{git_sha[:12]}{suffix}"
    prompt_sha = sha256_file(root / PROMPT_FILE)

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
        "tests": ["f1"],
        "limit": args.smoke,
        "models": config["models"],
        "benchmark_repo": config["benchmark"]["repo"],
        "benchmark_revision": config["benchmark"]["revision"],
        "benchmark_split": config["benchmark"]["split"],
        "tasks": config["benchmark"]["tasks"],
        "split_seed": config["split"]["seed"],
        "calibration_fraction": config["split"]["calibration_fraction"],
        "typhoon_prompt_file": PROMPT_FILE,
        "typhoon_prompt_sha256": prompt_sha,
        "dtype_preferred": config["runtime"]["dtype_preferred"],
        "dtype_fallback": config["runtime"]["dtype_fallback"],
        "max_new_tokens": config["runtime"]["max_new_tokens"],
        "generation": config["runtime"]["generation"],
        "arms": config["arms"],
        "crop_margin": config["crop_margin"],
        "crop_prompt": config["crop_prompt"],
        "crop_prompt_sha256": config["crop_prompt_sha256"],
        "question_clause": config["question_clause"],
        "question_clause_sha256": config["question_clause_sha256"],
        "created_at_utc": utc_now(),
    }

    run_dir = root / "runs" / "kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / "infra/kaggle/find_vs_read_worker.py"
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", {
        "id": kernel_id(root, KERNEL_SLUG), "title": "LabBS2026 Find Vs Read F1", "code_file": "worker.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
        "model_sources": [],
    })
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    print(json.dumps({"run_id": run_id, "git_sha": git_sha, "limit": args.smoke,
                      "staging": str(staging)}, indent=1))
    if args.submit:
        result = subprocess.run(build_submit_command(staging), capture_output=True, text=True)
        print(result.stdout or result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
