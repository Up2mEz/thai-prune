"""Prepare (and optionally submit) a MODEL_SURVEY W3 Kaggle run: T2 on another model.

W3a runs Pathumma (one shard per T4); W3b runs Qwen3-VL-4B in fp32 as one
process that sees both T4s. The item loop is `model_survey.remote_w3`, which
imports T2's code from `thai_marks` read-only.
"""

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
from labbs2026.model_survey.plan import unit_command

CONFIG = "configs/model_survey/w3_t2.yaml"
HASHED = (
    CONFIG,
    "configs/thai_marks/typhoon_card_prompt.txt",
    "src/labbs2026/model_survey/__init__.py",
    "src/labbs2026/model_survey/remote_w3.py",
    "src/labbs2026/thai_marks/__init__.py",
    "src/labbs2026/thai_marks/generation.py",
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


def queues(config: dict, roles: list[str]) -> list[list[dict]]:
    """One queue per shard; a two-GPU role is one unit that sees both T4s."""
    out = []
    for role in roles:
        model = config["models"][role]
        shards = int(model["shards"])
        for shard in range(shards):
            unit = unit_command("labbs2026.model_survey.remote_w3", f"w3_{role}_shard-{shard}-of-{shards}",
                                ["--role", role, "--shard", shard, "--shards", shards])
            if model.get("device_map") == "two_gpus":
                unit["visible_devices"] = "0,1"
            out.append([unit])
    if len(out) > 2 or (len(out) == 2 and any("visible_devices" in u for q in out for u in q)):
        raise SystemExit("a W3 run fits one Kaggle session: two one-GPU queues, or one two-GPU unit")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run", choices=("w3a", "w3b"), required=True)
    parser.add_argument("--smoke", type=int, default=0, help="engineering smoke: the first N calibration items")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    config = yaml.safe_load((root / CONFIG).read_text("utf-8"))
    if config["status"] != "APPROVED":
        raise SystemExit(f"{CONFIG} status is {config['status']!r}, not APPROVED")
    run = config["runs"][args.run]
    roles = list(run["roles"])
    gpu_queues = queues(config, roles)
    if args.smoke and any(args.smoke < int(config["models"][r]["shards"]) for r in roles):
        raise SystemExit("--smoke must be at least every selected model's shard count")

    local = load_local_config(root)
    remote_ref = local.get("remote_ref") or local_remote_ref(root)
    git_sha = preflight(root, remote_ref)
    run_id = f"kaggle-model-survey-{args.run}-{git_sha[:12]}" + (f"-smoke{args.smoke}" if args.smoke else "")
    prompt = config["prompts"][config["t2"]["prompt"]]

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
        "tests": ["w3_t2"],
        "limit": args.smoke,
        "roles": roles,
        "gpu_queues": gpu_queues,
        "models": {r: config["models"][r] for r in roles},
        "benchmark_repo": config["benchmark"]["repo"],
        "benchmark_revision": config["benchmark"]["revision"],
        "benchmark_split": config["benchmark"]["split"],
        "tasks": config["benchmark"]["tasks"],
        "split_seed": config["split"]["seed"],
        "calibration_fraction": config["split"]["calibration_fraction"],
        "typhoon_prompt_file": prompt["file"],
        "typhoon_prompt_sha256": prompt["sha256"],
        "t2_dtype": config["t2"]["dtype"],
        "window_after_chars": config["t2"]["window_after_chars"],
        "consistency_tolerance": config["t2"]["consistency_tolerance_nats"],
        "kernel_slug": run["kernel_slug"],
        "config_path": CONFIG,
        "created_at_utc": utc_now(),
    }

    run_dir = root / "runs" / "kaggle" / run_id
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / "infra/kaggle/model_survey_worker.py"
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", {
        "id": kernel_id(root, run["kernel_slug"]), "title": f"LabBS2026 Model Survey {args.run.upper()}",
        "code_file": "worker.py", "language": "python", "kernel_type": "script",
        "is_private": True, "enable_gpu": True, "enable_internet": True,
        "machine_shape": "NvidiaTeslaT4", "dataset_sources": [], "competition_sources": [],
        "kernel_sources": [], "model_sources": [],
    })
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    print(json.dumps({"run_id": run_id, "git_sha": git_sha, "roles": roles, "limit": args.smoke,
                      "gpu_queues": gpu_queues, "staging": str(staging)}, indent=1))
    if args.submit:
        result = subprocess.run(build_submit_command(staging), capture_output=True, text=True)
        print(result.stdout or result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
