"""Prepare (and optionally submit) the region-OCR Kaggle run."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import yaml

from labbs2026.kaggle import (
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    canonical_json_bytes,
    locked_package_versions,
    render_worker,
    sha256_file,
    utc_now,
)

TRACKED_FOR_HASHING = (
    "configs/region_ocr/run_design.yaml",
    "configs/runtime/kaggle_t4_region_ocr.yaml",
    "src/labbs2026/region_ocr/budget.py",
    "src/labbs2026/region_ocr/dataset.py",
    "src/labbs2026/region_ocr/execute.py",
    "src/labbs2026/region_ocr/prune_runtime.py",
    "src/labbs2026/region_ocr/pruning.py",
    "src/labbs2026/region_ocr/remote.py",
    "src/labbs2026/region_ocr/run.py",
    "src/labbs2026/region_ocr/text_metrics.py",
    "src/labbs2026/region_ocr/workload.py",
    "uv.lock",
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def preflight(root: Path, runtime: dict) -> str:
    # Only tracked changes matter: the worker clones from the remote by SHA, so
    # untracked local files cannot reach the run. Including them here would block
    # staging on unrelated scratch files.
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked files have uncommitted changes; commit before staging")
    head = _git(root, "rev-parse", "HEAD")
    ref = runtime["source"]["remote_ref"]
    remote = _git(root, "ls-remote", runtime["source"]["repository_url"], ref)
    if not remote:
        raise RuntimeError(f"remote ref {ref} does not exist; push the branch first")
    remote_sha = remote.split()[0]
    if remote_sha != head:
        raise RuntimeError(
            f"remote {ref} is at {remote_sha[:12]} but HEAD is {head[:12]}; push first"
        )
    return head


def build_spec(root: Path, design: dict, runtime: dict, git_sha: str,
               dataset_slug: str) -> dict:
    return {
        "schema_version": 1,
        "run_id": f"kaggle-region-ocr-{git_sha[:12]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        "expected_file_hashes": {p: sha256_file(root / p) for p in TRACKED_FOR_HASHING},
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "transformers_override_lock": runtime["uv"].get("transformers_override_lock"),
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "python_version": runtime["python"]["version"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "dataset_root": runtime["paths"]["dataset_root"],
        "dataset_slug": dataset_slug,
        "dataset_metadata_sha256": design["dataset"]["metadata_csv_sha256"],
        "model_id": design["model"]["model_id"],
        "model_revision": design["model"]["revision"],
        "model_dtype": runtime["model_runtime"]["dtype"],
        "attention_implementation": runtime["model_runtime"]["attention_implementation"],
        "device": runtime["model_runtime"]["device"],
        "selection_seed": design["selection"]["seed"],
        "selection_photos": design["selection"]["photos"],
        "selection_crops_per_photo": design["selection"]["crops_per_photo"],
        "selection_splits": [design["dataset"]["split_used"]],
        "ratios": design["intervention"]["ratios"],
        "sweep_factors": design["intervention"].get("magnification_sweep", {})
        .get("factors", []),
        "random_seeds": design["intervention"]["pruning"]["random_seeds"],
        "max_new_tokens": design["output_contract"]["decoding"]["max_new_tokens"],
        "created_at_utc": utc_now(),
    }


def conditions_per_region(root: Path, spec: dict) -> int:
    """The registered count, cross-checked against what the builder produces."""
    import yaml

    from labbs2026.region_ocr.workload import build_region_observations

    design = yaml.safe_load(
        (root / "configs/region_ocr/run_design.yaml").read_text(encoding="utf-8")
    )
    registered = int(design["intervention"]["conditions_per_region"])
    built = len(build_region_observations(
        {"image_id": "probe", "source_photo_id": "probe", "label": "probe"},
        {
            "full_placeholders": 160,
            "budgets": [
                {"ratio": r, "target_placeholders": 1, "pruning_placeholders": 1,
                 "resolution_reduction": {"forced_pixels": 1},
                 "restored": {"down_height": 1, "down_width": 1, "up_height": 1,
                              "up_width": 1, "forced_pixels": 1, "placeholders": 160}}
                for r in spec["ratios"]
            ],
            "sweep": [
                {"factor": f, "target_placeholders": 1, "placeholders": 1,
                 "resolution": {"forced_pixels": 1}}
                for f in spec["sweep_factors"]
            ],
        },
        random_seeds=[int(s) for s in spec["random_seeds"]],
    ))
    if built != registered:
        raise SystemExit(
            f"run_design.yaml registers {registered} conditions per region but the "
            f"workload builder produces {built}; refusing to submit a run whose "
            f"design record disagrees with its code"
        )
    return registered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--dataset-slug", required=True,
                        help="owner/dataset-name of the uploaded TEMS release")
    parser.add_argument("--submit", action="store_true",
                        help="run `kaggle kernels push` after staging")
    args = parser.parse_args()

    root = args.root.resolve()
    design = yaml.safe_load((root / "configs/region_ocr/run_design.yaml").read_text("utf-8"))
    runtime = yaml.safe_load((root / "configs/runtime/kaggle_t4_region_ocr.yaml").read_text("utf-8"))

    git_sha = preflight(root, runtime)
    spec = build_spec(root, design, runtime, git_sha, args.dataset_slug)

    run_dir = root / "runs" / "kaggle" / spec["run_id"]
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)

    template = root / "infra/kaggle/region_ocr_worker.py"
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py",
                      render_worker(template.read_text("utf-8"), spec))

    metadata = json.loads((root / "infra/kaggle/region-ocr-kernel-metadata.json").read_text("utf-8"))
    metadata["dataset_sources"] = [args.dataset_slug]
    atomic_write_json(staging / "kernel-metadata.json", metadata)

    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)

    command = build_submit_command(staging)
    print(json.dumps({
        "run_id": spec["run_id"],
        "git_sha": git_sha,
        "kernel_id": metadata["id"],
        "dataset_sources": metadata["dataset_sources"],
        "staging_dir": str(staging),
        "submit_command": command,
        "regions": spec["selection_photos"] * spec["selection_crops_per_photo"],
        # Derived from the registered design rather than from a formula written
        # beside it: an arm added to the grid must not leave this summary quietly
        # reporting the old count back to whoever submitted the run.
        "conditions_per_region": conditions_per_region(root, spec),
    }, indent=1))

    if args.submit:
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout or result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
