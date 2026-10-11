"""MODEL_SURVEY W1: cross-model failure profile and the stop at a loop (offline; see `model_survey.w1`).

Reads a fetched model-survey run (M1's by default; `--config` for M5, which
uses M1's schema) for the items' references (checksums verified), its
primary-prompt outputs, and T1's archived Typhoon and base outputs
(`BENCHMARK_QUESTION`). Writes one JSON file with no reference text and no
output text, and refuses to overwrite it.
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
from labbs2026.model_survey.exploratory import compare
from labbs2026.model_survey.w1 import attribution_shares, cell_scores, stop_summary, stopped
from labbs2026.thai_marks.attribution import attribute_marks
from labbs2026.thai_marks.order_free import mark_counts

ATTRIBUTION_TASK = "Full-page OCR"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _score(job: tuple) -> tuple:
    model, record, order_free = job
    after = stopped(record)
    out = {"v2": mark_counts(record["reference"], record["raw_output"], **order_free),
           "v2_stop": mark_counts(record["reference"], after["raw_output"], **order_free),
           "ra": mark_counts(record["reference"], record["raw_output"], **order_free, repeat_aware=True),
           "ra_stop": mark_counts(record["reference"], after["raw_output"], **order_free, repeat_aware=True)}
    if record["task"] == ATTRIBUTION_TASK:
        out["attr"] = attribute_marks(record["reference"], record["raw_output"], approximate_reorder=True)
        out["attr_stop"] = attribute_marks(record["reference"], after["raw_output"], approximate_reorder=True)
    return model, record["task"], record["id"], out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="the fetched artifacts/<run_id> directory")
    parser.add_argument("--config", type=Path, default=Path("configs/model_survey/m1.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    by_model: dict[str, list[dict]] = {}
    everything = []
    for role, model in config["models"].items():
        records, _ = load_role(args.run_dir, role, model["prompts"])
        everything += records
        by_model[role] = [r for r in records if r["prompt_kind"] == model["primary_prompt"]]
    references = references_by_id(everything)
    comparison = config["comparison"]
    archive = Path(comparison["outputs"])
    by_model.update(comparison_records(archive, comparison["roles"], comparison["prompt"], references))

    order_free = config["scoring"]["order_free"]
    boot = config["scoring"]["bootstrap"]
    jobs = [(m, r, order_free) for m, rows in by_model.items() for r in rows]
    with ProcessPoolExecutor(args.workers) as pool:
        scored = list(pool.map(_score, jobs, chunksize=4))
    table: dict = {}
    for model, task, item, out in scored:
        table.setdefault(model, {}).setdefault(task, {})[item] = out

    result: dict = {
        "kind": "exploratory, offline (Up2mEz's work split W1, 2026-10-11)",
        "claim_level": config["claim_level"], "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "config": args.config.as_posix(), "run": args.run_dir.name,
        "t1_outputs": {"path": str(archive), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "prompts": {**{m: config["models"][m]["primary_prompt"] for m in config["models"]},
                    **{m: comparison["prompt"] for m in comparison["roles"]}},
        "stop_rule": "loop_cut.variant_b (k = 8 / 6)", "order_free": order_free, "bootstrap": boot,
        "cells": {},
    }
    for model, rows in by_model.items():
        for task in sorted({r["task"] for r in rows}):
            records = {r["id"]: r for r in rows if r["task"] == task}
            ids = sorted(records)
            t = table[model][task]
            pick = {k: {i: t[i][k] for i in ids} for k in ("v2", "v2_stop", "ra", "ra_stop")}
            non_looping = [i for i in ids if not records[i]["reached_max_new_tokens"]]
            cell = {
                "stop": stop_summary(records, pick["v2"], pick["v2_stop"]),
                "scores": {k: cell_scores(v, ids) for k, v in pick.items()},
                "stop_effect": {
                    "v2_all": compare(pick["v2"], pick["v2_stop"], ids, **boot),
                    "v2_non_looping": compare(pick["v2"], pick["v2_stop"], non_looping, **boot)
                    if non_looping else None,
                    "repeat_aware_all": compare(pick["ra"], pick["ra_stop"], ids, **boot),
                },
            }
            if task == ATTRIBUTION_TASK:
                cell["attribution"] = {"raw": attribution_shares(t[i]["attr"] for i in ids),
                                       "stopped": attribution_shares(t[i]["attr_stop"] for i in ids)}
            result["cells"][f"{model} | {task}"] = cell
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
