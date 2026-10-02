"""Prepare (and optionally submit) the Thai-mark T1/T2 Kaggle run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from labbs2026.kaggle import (
    atomic_write_json,
    atomic_write_text,
    build_dataset_metadata,
    build_dataset_upload_command,
    build_submit_command,
    dataset_id,
    dataset_mount_path,
    kernel_id,
    load_local_config,
    local_remote_ref,
    locked_package_versions,
    render_worker,
    sha256_file,
    utc_now,
)

# Shared across whoever's Kaggle account runs this: the kernel *slug* (not the
# full id — the local config prefixes the account username), and the upstream
# repository every submission clones from regardless of whose fork or account
# is pushing it.
KERNEL_SLUG = "labbs2026-thai-marks-t1-t2"


def dataset_slugs(kernel_slug: str) -> tuple[str, str]:
    """Resume and T3-cases dataset slugs that belong to one kernel slug.

    Two sessions running in parallel use different kernel slugs (`--kernel-slug`)
    so that neither push replaces the other's kernel or its input datasets.
    """
    return f"{kernel_slug}-resume", f"{kernel_slug}-t3-cases"

HASHED = (
    "configs/thai_marks/t1_t2.yaml",
    "configs/thai_marks/typhoon_card_prompt.txt",
    "src/labbs2026/thai_marks/__init__.py",
    "src/labbs2026/thai_marks/decompose.py",
    "src/labbs2026/thai_marks/generation.py",
    "src/labbs2026/thai_marks/loop_guard.py",
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


def committed_sha256(root: Path, git_sha: str, path: str) -> str:
    """Hash of the file as committed, which is what the Kaggle worker checks out.

    The working copy can differ in line endings only (Windows autocrlf, or a
    tool writing CRLF) while git reports it clean; hashing it then fails the
    worker's source check on a file nobody changed.
    """
    blob = subprocess.run(["git", "show", f"{git_sha}:{path}"], cwd=root, check=True,
                          capture_output=True).stdout
    return hashlib.sha256(blob).hexdigest()


def preflight(root: Path, remote_ref: str) -> str:
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked files have uncommitted changes; commit before staging")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "ls-remote", REPOSITORY, remote_ref)
    if not remote or remote.split()[0] != head:
        raise RuntimeError(f"remote ref {remote_ref!r} is not at HEAD; push first")
    return head


def stage_resume_dataset(resume_from: Path, run_dir: Path) -> tuple[str, Path]:
    """Copy a previous attempt's fetched artifacts into a Kaggle-dataset staging dir.

    Returns the id fragment used to locate this attempt once mounted
    (`<dataset-slug>/<old_run_id>/<test>/<role>/...`) and the staging directory
    to upload.
    """
    old_run_id = resume_from.name
    staging = run_dir / "resume_dataset"
    shutil.copytree(resume_from, staging / old_run_id)
    return old_run_id, staging


def upload_dataset(root: Path, staging: Path, slug: str, title: str,
                   wait_seconds: int = 900) -> str:
    """Create or version a private dataset and wait until Kaggle marks it ready.

    A kernel pushed while its input dataset is still processing may start
    without the files, so the push waits for `ready`.
    """
    ref = dataset_id(root, slug)
    atomic_write_json(staging / "dataset-metadata.json", build_dataset_metadata(ref, title))
    exists = subprocess.run(["kaggle", "datasets", "status", ref],
                            capture_output=True, text=True).returncode == 0
    result = subprocess.run(build_dataset_upload_command(staging, exists=exists),
                            capture_output=True, text=True)
    print(result.stdout or result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        status = subprocess.run(["kaggle", "datasets", "status", ref],
                                capture_output=True, text=True).stdout.strip().lower()
        if "ready" in status:
            return ref
        if "error" in status:
            raise SystemExit(f"dataset {ref} failed processing: {status}")
        time.sleep(15)
    raise SystemExit(f"dataset {ref} not ready after {wait_seconds} s")


def upload_resume_dataset(root: Path, staging: Path, slug: str) -> str:
    ref = dataset_id(root, slug)
    atomic_write_json(staging / "dataset-metadata.json",
                      build_dataset_metadata(ref, "LabBS2026 Thai Marks T1 T2 Resume"))
    exists = subprocess.run(["kaggle", "datasets", "status", ref],
                            capture_output=True, text=True).returncode == 0
    result = subprocess.run(build_dataset_upload_command(staging, exists=exists),
                            capture_output=True, text=True)
    print(result.stdout or result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    return ref


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--tests", default="t1,t2")
    parser.add_argument("--roles", default="base,typhoon",
                        help="which models to run, e.g. 'base' for a one-model session")
    parser.add_argument("--shards", type=int, default=1,
                        help="split each role's items across this many processes/GPUs")
    parser.add_argument("--limit", type=int, default=0,
                        help="engineering smoke only: run the first N calibration items")
    parser.add_argument("--resume-from", type=Path, default=None,
                        help="a previous, interrupted attempt's fetched artifact "
                             "directory (runs/kaggle/<old-run-id>/fetched/artifacts/"
                             "<old-run-id>) whose already-finished legs this "
                             "submission should skip instead of re-running")
    parser.add_argument("--t3-cases", type=Path, default=None,
                        help="T3 cases JSON (scripts/thai_marks_t3_cases.py); attached as a "
                             "private dataset")
    parser.add_argument("--kernel-slug", default=KERNEL_SLUG,
                        help="Kaggle kernel slug; give each parallel session its own")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    resume_slug, t3_slug = dataset_slugs(args.kernel_slug)
    config = yaml.safe_load((root / "configs/thai_marks/t1_t2.yaml").read_text("utf-8"))
    local = load_local_config(root)
    remote_ref = local.get("remote_ref") or local_remote_ref(root)
    git_sha = preflight(root, remote_ref)
    tests = [t for t in args.tests.split(",") if t]
    roles = [r for r in args.roles.split(",") if r]
    if set(roles) - {"base", "typhoon"} or not roles:
        raise SystemExit(f"unknown roles: {roles}")
    if "t5" in tests and roles != list(config["t5"]["roles"]):
        raise SystemExit(f"t5 is registered for roles {config['t5']['roles']} only")
    suffix = "" if roles == ["base", "typhoon"] else "-" + "-".join(roles)
    suffix += f"-x{args.shards}" if args.shards > 1 else ""
    suffix += f"-smoke{args.limit}" if args.limit else ""
    run_id = f"kaggle-thai-marks-{'-'.join(tests)}-{git_sha[:12]}{suffix}"

    spec = {
        "schema_version": 1,
        "run_id": run_id,
        "repository_url": REPOSITORY,
        "remote_ref": remote_ref,
        "git_sha": git_sha,
        "expected_file_hashes": {p: committed_sha256(root, git_sha, p) for p in HASHED},
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "uv_bootstrap_version": "0.11.25",
        "uv_sync_args": ["--frozen", "--extra", "model", "--extra", "bench"],
        "python_version": "3.12",
        "source_dir": "/tmp/labbs2026-source",
        "output_root": "/kaggle/working/artifacts",
        "tests": tests,
        "limit": args.limit,
        "roles": roles,
        "shards": args.shards,
        "models": config["models"],
        "benchmark_repo": config["benchmark"]["repo"],
        "benchmark_revision": config["benchmark"]["revision"],
        "benchmark_split": config["benchmark"]["split"],
        "tasks": config["benchmark"]["tasks"],
        "split_seed": config["split"]["seed"],
        "calibration_fraction": config["split"]["calibration_fraction"],
        "typhoon_prompt_file": config["prompts"]["TYPHOON_CARD"]["file"],
        "typhoon_prompt_sha256": config["prompts"]["TYPHOON_CARD"]["sha256"],
        "dtype_preferred": config["runtime"]["dtype_preferred"],
        "dtype_fallback": config["runtime"]["dtype_fallback"],
        "t1_prompts": config["t1"]["prompts"],
        "max_new_tokens": config["t1"]["max_new_tokens"],
        "generation": config["t1"]["generation"],
        "t5_arms": config.get("t5", {}).get("arms"),
        "window_after_chars": config["t2"]["window_after_chars"],
        "t2_dtype": config["t2"].get("dtype"),
        "consistency_tolerance": config["t2"]["consistency_tolerance_nats"],
        "kernel_slug": args.kernel_slug,
        "created_at_utc": utc_now(),
    }

    run_dir = root / "runs" / "kaggle" / run_id
    dataset_sources: list[str] = []
    resume_dataset_staging: Path | None = None
    t3_staging: Path | None = None
    if args.t3_cases:
        if "t3" not in tests:
            raise SystemExit("--t3-cases given but t3 is not in --tests")
        t3_staging = run_dir / "t3_dataset"
        t3_staging.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(args.t3_cases, t3_staging / "t3_cases.json")
        spec["t3_cases_sha256"] = sha256_file(t3_staging / "t3_cases.json")
        spec["t3_cases"] = dataset_mount_path(t3_slug, "t3_cases.json")
        dataset_sources.append(dataset_id(root, t3_slug))
    elif "t3" in tests:
        raise SystemExit("t3 needs --t3-cases")
    if args.resume_from:
        old_run_id, resume_dataset_staging = stage_resume_dataset(
            args.resume_from.resolve(), run_dir)
        spec["resume_artifact_dir"] = dataset_mount_path(resume_slug, old_run_id)
        dataset_sources.append(dataset_id(root, resume_slug))

    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / "infra/kaggle/thai_marks_worker.py"
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    atomic_write_json(staging / "kernel-metadata.json", {
        "id": kernel_id(root, args.kernel_slug), "title": "LabBS2026 Thai Marks T1 T2", "code_file": "worker.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": dataset_sources, "competition_sources": [], "kernel_sources": [],
        "model_sources": [],
    })
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    print(json.dumps({"run_id": run_id, "git_sha": git_sha, "tests": tests,
                      "limit": args.limit, "staging": str(staging),
                      "resume_artifact_dir": spec.get("resume_artifact_dir")}, indent=1))
    if args.submit:
        if t3_staging is not None:
            print("t3 cases dataset ready:", upload_dataset(
                root, t3_staging, t3_slug, "LabBS2026 Thai Marks T3 Cases"))
        if resume_dataset_staging is not None:
            uploaded_ref = upload_resume_dataset(root, resume_dataset_staging, resume_slug)
            print(f"resume dataset uploaded: {uploaded_ref}")
        result = subprocess.run(build_submit_command(staging), capture_output=True, text=True)
        print(result.stdout or result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
