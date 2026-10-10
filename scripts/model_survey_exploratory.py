"""MODEL_SURVEY_M1 exploratory readings (not registered): loops versus reading, answering versus transcribing.

Reads a fetched, checksum-verified run (as `model_survey_analyze.py` leaves it)
and T1's archived outputs; writes one JSON file and refuses to overwrite it.
See `labbs2026.model_survey.exploratory`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.model_survey.analysis import comparison_records, load_role, references_by_id
from labbs2026.model_survey.exploratory import compare, no_loop_ids, split_by_length
from labbs2026.thai_marks.order_free import mark_counts

CONFIG = Path("configs/model_survey/m1.yaml")


def _counts(job: tuple[str, str]) -> dict:
    reference, output = job
    return mark_counts(reference, output, max_cer=0.4, residual=True)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id> directory")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    boot = config["scoring"]["bootstrap"]
    kw = {"resamples": int(boot["resamples"]), "seed": int(boot["seed"])}

    primary = {role: m["primary_prompt"] for role, m in config["models"].items()}
    records: dict[tuple[str, str], dict[str, dict]] = {}       # (role, task) -> id -> record
    loaded = []
    for role in config["models"]:
        rows, _ = load_role(args.run_dir, role, config["models"][role]["prompts"])
        loaded += rows
        for r in rows:
            if r["prompt_kind"] == primary[role]:
                records.setdefault((role, r["task"]), {})[r["id"]] = r
    comparison = config["comparison"]
    for role, rows in comparison_records(Path(comparison["outputs"]), comparison["roles"], comparison["prompt"],
                                         references_by_id(loaded)).items():
        primary[role] = comparison["prompt"]
        for r in rows:
            records.setdefault((role, r["task"]), {})[r["id"]] = r

    keys = [(cell, i) for cell, rows in records.items() for i in rows]
    with ProcessPoolExecutor(args.workers) as pool:
        values = list(pool.map(_counts, [(records[c][i]["reference"], records[c][i]["raw_output"]) for c, i in keys],
                               chunksize=8))
    counts: dict[tuple[str, str], dict[str, dict]] = {}
    for (cell, i), v in zip(keys, values):
        counts.setdefault(cell, {})[i] = v

    out: dict = {"status": "EXPLORATORY_NOT_REGISTERED", "claim_level": config["claim_level"],
                 "git_sha": _git("rev-parse", "HEAD"),
                 "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                 "records_sha256": {f.relative_to(args.run_dir).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                                    for f in sorted((args.run_dir / "m1").rglob("records.jsonl"))},
                 "primary_prompt": primary, "bootstrap": boot,
                 "wayu_minus_paddle": {}, "no_loop_vs_typhoon": {}, "text_recognition_by_length": {}}
    tasks = config["benchmark"]["tasks"]
    for task in tasks:
        ids = sorted(set(counts[("paddle", task)]) & set(counts[("wayu", task)]))
        out["wayu_minus_paddle"][task] = compare(counts[("paddle", task)], counts[("wayu", task)], ids, **kw)
        for role in [*config["models"], "base"]:
            ids = no_loop_ids(records[("typhoon", task)], records[(role, task)])
            out["no_loop_vs_typhoon"][f"{role} / {task}"] = {
                "of": len(records[(role, task)]),
                **compare(counts[("typhoon", task)], counts[(role, task)], ids, **kw)}
    task = "Text recognition"
    for role in ("paddle", "wayu"):
        ids = no_loop_ids(records[("typhoon", task)], records[(role, task)])
        for part, part_ids in split_by_length(records[(role, task)], ids).items():
            out["text_recognition_by_length"][f"{role} / {part}"] = compare(
                counts[("typhoon", task)], counts[(role, task)], part_ids, **kw)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
