"""Fetch a MODEL_SURVEY_M2 run, verify its checksums, and write the registered scores (CPU only).

Arms: G (M1's greedy outputs, from the M1 archive), the run arms (R105, CARD)
and, offline, each with T5b's stop (+B). Base and Typhoon from T1's archive.
All are scored against this run's references for the same items. Refuses to
overwrite a results file.
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
from labbs2026.model_survey.analysis import comparison_records, references_by_id, score_role
from labbs2026.model_survey.exploratory import compare, no_loop_ids, split_by_length
from labbs2026.model_survey.m2 import cost, load_arm, stop_at_loop

CONFIG = Path("configs/model_survey/m2.yaml")
KERNEL_SLUG = "labbs2026-model-survey-m2"


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
    parser.add_argument("--workers", type=int, default=8)
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
    partial = (root / "PARTIAL.json").is_file()
    if (root / "FAILURE.json").is_file() and not partial:
        raise SystemExit("run failed before inference ended: " + (root / "FAILURE.json").read_text("utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    scoring = config["scoring"]
    boot = {"resamples": int(scoring["bootstrap"]["resamples"]), "seed": int(scoring["bootstrap"]["seed"])}
    result: dict = {"run_id": args.run_id, "claim_level": config["claim_level"], "partial_run": partial,
                    "git_sha": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                    "scoring": scoring, "records_sha256": {}, "manifests": {}, "excluded": {}}
    arms: dict[str, list[dict]] = {}
    for arm in config["arms"]:
        try:
            arms[arm], result["manifests"][arm] = load_arm(root, arm)
        except FileNotFoundError as exc:
            result["excluded"][arm] = str(exc)
            continue
        f = root / "m2" / arm / "records.jsonl"
        result["records_sha256"][f.relative_to(root).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()

    references = references_by_id([r for rows in arms.values() for r in rows])
    ref_arm = config["reference_arm"]
    archive = Path(ref_arm["outputs"])
    arms[ref_arm["name"]] = comparison_records(archive, [ref_arm["role"]], config["prompt_kind"],
                                               references)[ref_arm["role"]]
    result["reference_arm"] = {**ref_arm, "outputs_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    for name, source in config["offline_arms"].items():
        if source in arms:
            arms[name] = [stop_at_loop(r) for r in arms[source]]
    comparison = config["comparison"]
    old = comparison_records(Path(comparison["outputs"]), comparison["roles"], comparison["prompt"], references)

    everything = {**arms, **old}
    with ProcessPoolExecutor(args.workers) as pool:
        scored = dict(pool.map(_score, [(name, rows, scoring) for name, rows in everything.items()]))
    result["arms"] = {name: {k: v for k, v in scored[name].items() if not k.startswith("_")} for name in arms}
    result["comparison"] = {name: {k: v for k, v in scored[name].items() if not k.startswith("_")} for name in old}

    def by_task(name: str, task: str) -> tuple[dict, dict]:
        rows = {r["id"]: r for r in everything[name] if r["task"] == task}
        counts = {i: c for (t, _, i), c in scored[name]["_counts"].items() if t == task}
        return rows, counts

    result["cost"], result["vs_G"], result["vs_typhoon"], result["text_recognition_by_length"] = {}, {}, {}, {}
    for task in config["benchmark"]["tasks"]:
        g_rows, g_counts = by_task(ref_arm["name"], task)
        t_rows, t_counts = by_task("typhoon", task)
        for name in arms:
            rows, counts = by_task(name, task)
            result["cost"][f"{name} / {task}"] = cost(list(rows.values()))
            if name != ref_arm["name"]:
                result["vs_G"][f"{name} / {task}"] = compare(g_counts, counts, sorted(set(g_counts) & set(counts)), **boot)
            result["vs_typhoon"][f"{name} / {task}"] = compare(t_counts, counts, sorted(set(t_counts) & set(counts)), **boot)
            if task == "Text recognition":       # exploratory, as M1's §4
                ids = no_loop_ids(t_rows, rows)
                for part, part_ids in split_by_length(rows, ids).items():
                    result["text_recognition_by_length"][f"{name} / {part}"] = compare(t_counts, counts, part_ids, **boot)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
