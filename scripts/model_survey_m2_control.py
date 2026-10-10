"""Fetch MODEL_SURVEY_M2's control run and check it reproduces M1's `G` token for token (registration Addendum 1).

CPU only. Verifies the run's checksums, compares each control arm's outputs
with M1's archived Wayu outputs for the same items (`model_survey.m2.reproduces`)
and writes one JSON file; refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.kaggle import kernel_id
from labbs2026.model_survey.analysis import comparison_records, references_by_id
from labbs2026.model_survey.m2 import load_arm, reproduces

CONFIG = Path("configs/model_survey/m2.yaml")
KERNEL_SLUG = "labbs2026-model-survey-m2"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skip-fetch", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))

    if not args.skip_fetch:
        args.destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", kernel_id(Path("."), KERNEL_SLUG),
                        "-p", str(args.destination)], check=True, capture_output=True)
    root = next(args.destination.rglob(args.run_id), None)
    if root is None or not root.is_dir():
        raise SystemExit(f"run directory {args.run_id} not found under {args.destination}")
    if (root / "FAILURE.json").is_file() or (root / "PARTIAL.json").is_file():
        raise SystemExit("the control run did not finish cleanly")
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    ref_arm = config["reference_arm"]
    archive = Path(ref_arm["outputs"])
    result: dict = {"run_id": args.run_id, "git_sha": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                    "reference_arm": {**ref_arm, "outputs_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
                    "manifests": {}, "arms": {}}
    for arm in config["control"]["arms"]:
        records, result["manifests"][arm] = load_arm(root, arm)
        g = comparison_records(archive, [ref_arm["role"]], config["prompt_kind"], references_by_id(records))
        result["arms"][arm] = reproduces(records, {r["id"]: r for r in g[ref_arm["role"]]})
    result["all_reproduced"] = all(v["all_reproduced"] for v in result["arms"].values())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({arm: {k: v[k] for k in ("n", "reproduced", "all_reproduced")}
                      for arm, v in result["arms"].items()}))


if __name__ == "__main__":
    main()
