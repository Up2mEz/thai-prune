"""Fetch a MODEL_SURVEY_M1 run, verify its checksums, and write the registered scores (CPU only).

Scores every finished model leg and, for comparison, the archived T1 outputs of
base and Typhoon against the same items' references. Refuses to overwrite a
results file. `--outputs-archive` also writes the new models' outputs without
reference text or images, in the format of `T1_OUTPUTS_a44199c29759.json.gz`.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.kaggle import kernel_id
from labbs2026.model_survey.analysis import (
    UnfinishedLeg,
    comparison_records,
    load_role,
    paired_f1_difference,
    references_by_id,
    score_role,
)

CONFIG = Path("configs/model_survey/m1.yaml")
KERNEL_SLUG = "labbs2026-model-survey-m1"
ARCHIVE_FIELDS = ("id", "task", "prompt_kind", "raw_output", "generated_tokens",
                  "reached_max_new_tokens", "visual_tokens", "prompt_tokens", "seconds_generate",
                  "seconds_per_generated_token", "resized_size")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _by_id(counts: dict[tuple, dict], task: str, prompt: str) -> dict[str, dict]:
    return {i: c for (t, p, i), c in counts.items() if t == task and p == prompt}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--outputs-archive", type=Path, default=None)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--kernel-id", default=None, help="owner/slug (default: this account's M1 kernel)")
    args = parser.parse_args()
    for path in (args.out, args.outputs_archive):
        if path is not None and path.exists():
            raise SystemExit(f"{path} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))

    if not args.skip_fetch:
        args.destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", args.kernel_id or kernel_id(Path("."), KERNEL_SLUG),
                        "-p", str(args.destination)], check=True, capture_output=True)
    root = next(args.destination.rglob(args.run_id), None)
    if root is None or not root.is_dir():
        raise SystemExit(f"run directory {args.run_id} not found under {args.destination}")
    partial = (root / "PARTIAL.json").is_file()
    if (root / "FAILURE.json").is_file() and not partial:
        raise SystemExit("run failed before inference ended: "
                         + (root / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    scoring = config["scoring"]
    order_free = scoring["order_free"]
    result: dict = {
        "run_id": args.run_id, "claim_level": config["claim_level"], "partial_run": partial,
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "scoring": scoring, "records_sha256": {}, "manifests": {}, "excluded": {},
        "models": {}, "comparison": {}, "paired_mark_f1": {},
    }
    scored, by_role = {}, {}
    for role, model in config["models"].items():
        try:
            records, manifests = load_role(root, role, model["prompts"])
        except UnfinishedLeg as exc:
            result["excluded"][role] = str(exc)
            continue
        for f in sorted((root / "m1" / role).rglob("records.jsonl")):
            result["records_sha256"][f.relative_to(root).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
        result["manifests"][role] = manifests
        by_role[role] = records
        scored[role] = score_role(records, null_seed=int(scoring["null_seed"]), **order_free)
        result["models"][role] = {k: v for k, v in scored[role].items() if not k.startswith("_")}

    references = references_by_id([r for records in by_role.values() for r in records])
    comparison = config["comparison"]
    archive = Path(comparison["outputs"])
    old = comparison_records(archive, comparison["roles"], comparison["prompt"], references)
    result["comparison"]["source"] = {"run_id": comparison["run_id"], "outputs": str(archive),
                                      "outputs_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    for role, records in old.items():
        scored[role] = score_role(records, null_seed=int(scoring["null_seed"]), **order_free)
        result["comparison"][role] = {k: v for k, v in scored[role].items() if not k.startswith("_")}

    boot = scoring["bootstrap"]
    for role, model in config["models"].items():
        if role not in result["models"]:
            continue
        for task in config["benchmark"]["tasks"]:
            new = _by_id(scored[role]["_counts"], task, model["primary_prompt"])
            for reference_role in comparison["roles"]:
                ref = _by_id(scored[reference_role]["_counts"], task, comparison["prompt"])
                result["paired_mark_f1"][f"{role} ({model['primary_prompt']}) - {reference_role} "
                                         f"({comparison['prompt']}) / {task}"] = paired_f1_difference(
                    ref, new, resamples=int(boot["resamples"]), seed=int(boot["seed"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.outputs_archive is not None:
        rows = {role: [{k: r.get(k) for k in ARCHIVE_FIELDS}
                       for r in sorted(records, key=lambda r: (r["id"], r["prompt_kind"]))]
                for role, records in by_role.items()}
        payload = {"provenance": {"run_id": args.run_id, "records_sha256": result["records_sha256"],
                                  "note": "MODEL_SURVEY_M1 outputs; no reference text and no image."},
                   "records": rows}
        args.outputs_archive.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(args.outputs_archive, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
    print(args.out)


if __name__ == "__main__":
    main()
