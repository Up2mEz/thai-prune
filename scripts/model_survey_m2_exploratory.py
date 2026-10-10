"""MODEL_SURVEY_M2 exploratory readings (not registered): the stop, the penalty, and what the loops repeat.

Reads a fetched run (as `model_survey_m2_analyze.py` leaves it; checksums are
verified again), M1's archived Wayu outputs (`G`) and T1's archived Typhoon
outputs; writes one JSON file and refuses to overwrite it. With
`--outputs-archive`, also writes the run arms' outputs, without reference text
or images, in M1's archive format. See `labbs2026.model_survey.m2_exploratory`.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.model_survey.analysis import comparison_records, references_by_id
from labbs2026.model_survey.exploratory import compare
from labbs2026.model_survey.m2 import load_arm, stop_at_loop
from labbs2026.model_survey.m2_exploratory import (
    loop_content,
    split_by_loop,
    stop_effect,
    summarize_stops,
    symmetric_ids,
)
from labbs2026.thai_marks.order_free import mark_counts

CONFIG = Path("configs/model_survey/m2.yaml")
PAIRS = (("G+B", "R105+B"), ("G+B", "CARD+B"), ("R105", "CARD"), ("R105+B", "CARD+B"))
ARCHIVE_FIELDS = ("id", "task", "prompt_kind", "arm", "seed", "raw_output", "generated_tokens",
                  "reached_max_new_tokens", "visual_tokens", "prompt_tokens", "seconds_generate",
                  "seconds_per_generated_token", "resized_size")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _counts(job: tuple[str, str, str, str, dict]) -> tuple[str, str, dict]:
    name, item, reference, output, order_free = job
    return name, item, mark_counts(reference, output, **order_free)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id> directory")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--outputs-archive", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    for path in (args.out, args.outputs_archive):
        if path is not None and path.exists():
            raise SystemExit(f"{path} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    order_free = config["scoring"]["order_free"]
    boot = {"resamples": int(config["scoring"]["bootstrap"]["resamples"]),
            "seed": int(config["scoring"]["bootstrap"]["seed"])}

    arms: dict[str, list[dict]] = {}
    records_sha256 = {}
    for arm in config["arms"]:
        arms[arm], _ = load_arm(args.run_dir, arm)
        f = args.run_dir / "m2" / arm / "records.jsonl"
        records_sha256[f.relative_to(args.run_dir).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
    references = references_by_id([r for rows in arms.values() for r in rows])
    ref_arm = config["reference_arm"]
    arms[ref_arm["name"]] = comparison_records(Path(ref_arm["outputs"]), [ref_arm["role"]], config["prompt_kind"],
                                               references)[ref_arm["role"]]
    for name, source in config["offline_arms"].items():
        arms[name] = [stop_at_loop(r) for r in arms[source]]
    comparison = config["comparison"]
    arms["typhoon"] = comparison_records(Path(comparison["outputs"]), ["typhoon"], comparison["prompt"],
                                         references)["typhoon"]

    jobs = [(name, r["id"], r["reference"], r["raw_output"], order_free) for name, rows in arms.items() for r in rows]
    counts: dict[str, dict[str, dict]] = {name: {} for name in arms}
    with ProcessPoolExecutor(args.workers) as pool:
        for name, item, c in pool.map(_counts, jobs, chunksize=4):
            counts[name][item] = c

    result: dict = {"run_id": args.run_dir.name, "claim_level": "EXPLORATORY_NOT_REGISTERED",
                    "git_sha": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                    "records_sha256": records_sha256, "order_free": order_free, "bootstrap": boot,
                    "pairs": {}, "stops": {}, "cut_items": {}, "loop_content": {}, "loop_split_vs_typhoon": {},
                    "text_recognition_symmetric": {}}
    for task in config["benchmark"]["tasks"]:
        rows = {name: {r["id"]: r for r in arms[name] if r["task"] == task} for name in arms}
        task_counts = {name: {i: counts[name][i] for i in rows[name]} for name in arms}
        for a, b in PAIRS:
            ids = sorted(set(rows[a]) & set(rows[b]))
            result["pairs"][f"{b} - {a} / {task}"] = compare(task_counts[a], task_counts[b], ids, **boot)
        for stopped, source in config["offline_arms"].items():
            effects = [stop_effect(raw, task_counts[source][i], task_counts[stopped][i])
                       for i, raw in sorted(rows[source].items()) if rows[stopped][i]["t5b_cut"]]
            result["stops"][f"{stopped} / {task}"] = summarize_stops(effects)
            result["cut_items"][f"{stopped} / {task}"] = effects
            result["loop_content"][f"{source} / {task}"] = loop_content(list(rows[source].values()),
                                                                        task_counts[source])
            for part, ids in split_by_loop(rows[source]).items():
                result["loop_split_vs_typhoon"][f"{stopped} / {task} / {part}"] = compare(
                    task_counts["typhoon"], task_counts[stopped], ids, **boot)
        if task == "Text recognition":       # the review's symmetric subset, next to M1's one-sided split
            for name in [*config["arms"], ref_arm["name"], *config["offline_arms"]]:
                ids = symmetric_ids(rows["typhoon"], rows[name])
                result["text_recognition_symmetric"][name] = compare(task_counts["typhoon"], task_counts[name],
                                                                     ids, **boot)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.outputs_archive is not None:
        payload = {"provenance": {"run_id": args.run_dir.name, "records_sha256": records_sha256,
                                  "note": "MODEL_SURVEY_M2 run arms' outputs; no reference text and no image."},
                   "records": {arm: [{k: r.get(k) for k in ARCHIVE_FIELDS}
                                     for r in sorted(arms[arm], key=lambda r: r["id"])]
                               for arm in config["arms"]}}
        args.outputs_archive.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(args.outputs_archive, "wt", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
    print(args.out)


if __name__ == "__main__":
    main()
