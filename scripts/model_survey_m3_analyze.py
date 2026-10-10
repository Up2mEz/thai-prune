"""Fetch a MODEL_SURVEY_M3 run, verify its checksums, and write the registered scores (CPU only).

Arms: `E` (the run), `E0` (its stop-only twin, `m3.stop_only`), `G` and `G+B`
(M1's greedy outputs, without and with T5b's stop), and base and Typhoon from
T1's archive. All are scored against this run's references for the same items.
Refuses to overwrite a results file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.kaggle import kernel_id
from labbs2026.model_survey.analysis import (
    comparison_records,
    paired_f1_difference,
    references_by_id,
    score_role,
)
from labbs2026.model_survey.exploratory import compare
from labbs2026.model_survey.m2 import stop_at_loop
from labbs2026.model_survey.m3 import control, escape_summary, load_shards, stop_only, validate

CONFIG = Path("configs/model_survey/m3.yaml")
KERNEL_SLUG = "labbs2026-model-survey-m3"
# (a, b): b − a, paired over the items both read
PAIRS = (("E0", "E"), ("G+B", "E"), ("typhoon", "E"), ("typhoon", "E0"), ("G+B", "E0"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _score(job: tuple[str, list[dict], dict]) -> tuple[str, dict]:
    name, records, scoring = job
    return name, score_role(records, null_seed=int(scoring["null_seed"]), **scoring["order_free"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    validate(config)

    if not args.skip_fetch:
        args.destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", kernel_id(Path("."), KERNEL_SLUG),
                        "-p", str(args.destination)], check=True, capture_output=True)
    root = next(args.destination.rglob(args.run_id), None)
    if root is None or not root.is_dir():
        raise SystemExit(f"run directory {args.run_id} not found under {args.destination}")
    partial = (root / "PARTIAL.json").is_file()
    if (root / "FAILURE.json").is_file() and not partial:
        raise SystemExit("run failed before inference ended: " + (root / "FAILURE.json").read_text("utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    scoring = config["scoring"]
    boot = {"resamples": int(scoring["bootstrap"]["resamples"]), "seed": int(scoring["bootstrap"]["seed"])}
    arm = config["escape"]["arm"]
    records, manifests = load_shards(root, arm, int(config["shards"]))
    shard_files = sorted((root / "m3" / arm).glob("shard-*/records.jsonl"))
    result: dict = {"run_id": args.run_id, "claim_level": config["claim_level"], "partial_run": partial,
                    "git_sha": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                    "scoring": scoring, "manifests": manifests,
                    "records_sha256": {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                                       for f in shard_files}}

    references = references_by_id(records)
    ref_arm = config["reference_arm"]
    archive = Path(ref_arm["outputs"])
    greedy = comparison_records(archive, [ref_arm["role"]], config["prompt_kind"], references)[ref_arm["role"]]
    result["reference_arm"] = {**ref_arm, "outputs_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    result["control"] = control(records, {r["id"]: r for r in greedy})
    arms = {arm: records, "E0": [stop_only(r) for r in records], ref_arm["name"]: greedy,
            config["stopped_arm"]: [stop_at_loop(r) for r in greedy]}
    comparison = config["comparison"]
    old = comparison_records(Path(comparison["outputs"]), comparison["roles"], comparison["prompt"], references)
    everything = {**arms, **old}
    with ProcessPoolExecutor(args.workers) as pool:
        scored = dict(pool.map(_score, [(name, rows, scoring) for name, rows in everything.items()]))
    result["arms"] = {name: {k: v for k, v in scored[name].items() if not k.startswith("_")} for name in arms}
    result["comparison"] = {name: {k: v for k, v in scored[name].items() if not k.startswith("_")} for name in old}

    def counts(name: str, task: str) -> dict[str, dict]:
        return {i: c for (t, _, i), c in scored[name]["_counts"].items() if t == task}

    result["pairs"], result["escaped_items"], result["escape"] = {}, {}, {}
    for task in config["benchmark"]["tasks"]:
        task_records = [r for r in records if r["task"] == task]
        result["escape"][task] = escape_summary(task_records)
        escaped = sorted(r["id"] for r in task_records if r["escapes"] or r["final_cut"])
        for a, b in PAIRS:
            ca, cb = counts(a, task), counts(b, task)
            ids = sorted(set(ca) & set(cb))
            pair = compare(ca, cb, ids, **boot)
            pair["difference"]["matched_lines"] = paired_f1_difference(
                {i: ca[i] for i in ids}, {i: cb[i] for i in ids}, key="matched_lines", **boot)
            result["pairs"][f"{b} - {a} / {task}"] = pair
            if escaped:
                part = compare(ca, cb, escaped, **boot)
                part["difference"]["matched_lines"] = paired_f1_difference(
                    {i: ca[i] for i in escaped}, {i: cb[i] for i in escaped}, key="matched_lines", **boot)
                result["escaped_items"][f"{b} - {a} / {task}"] = part

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
