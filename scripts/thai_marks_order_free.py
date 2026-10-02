"""Order-free and global mark precision/recall per cell, with the CAT control (diagnostic)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from labbs2026.thai_marks import order_free
from labbs2026.thai_marks.order_free import mark_counts, prf

THRESHOLDS = (0.2, order_free.LINE_MATCH_CER, 0.6)


def _variants(job: tuple[str, str]) -> dict[str, dict]:
    reference, output = job
    out = {"global": mark_counts(reference, output, mode="global")}
    for t in THRESHOLDS:
        out[f"line_matched@{t}"] = mark_counts(reference, output, max_cer=t)
    return out


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-dir", type=Path, required=True,
                        help="fetched artifacts t1/ directory (holds <role>/records.jsonl)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    provenance = {"git_sha": _git("rev-parse", "HEAD"),
                  "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                  "records_sha256": {}, "line_match_thresholds": THRESHOLDS,
                  "min_line_chars": order_free.MIN_ELSEWHERE_CHARS}
    jobs: dict[str, list[tuple[str, str]]] = {}
    for records_path in sorted(args.t1_dir.glob("*/records.jsonl")):
        role = records_path.parent.name
        provenance["records_sha256"][role] = hashlib.sha256(records_path.read_bytes()).hexdigest()
        records = [json.loads(line) for line in records_path.open(encoding="utf-8") if line.strip()]
        by_id: dict[tuple, dict] = {}
        for r in sorted(records, key=lambda r: (r["task"], r["prompt_kind"], r["id"])):
            jobs.setdefault(f"{role} | {r['task']} | {r['prompt_kind']}", []).append(
                (r["reference"], r["raw_output"]))
            by_id.setdefault((r["task"], r["id"]), {})[r["prompt_kind"]] = r
        # CAT control: both prompts' reads of the same item, concatenated, no merging.
        for (task, _), pair in sorted(by_id.items()):
            if task == "Full-page OCR" and len(pair) == 2:
                bq, tc = pair["BENCHMARK_QUESTION"], pair["TYPHOON_CARD"]
                jobs.setdefault(f"{role} | {task} | CAT(BQ+TC)", []).append(
                    (bq["reference"], bq["raw_output"] + "\n\n" + tc["raw_output"]))

    cells: dict[str, dict] = {}
    with ProcessPoolExecutor(args.workers) as pool:
        for name, items in jobs.items():
            results = list(pool.map(_variants, items))
            cells[name] = {v: prf([r[v] for r in results]) for v in results[0]}
            print(name, {v: f"R {s['recall']:.1%} P {s['precision']:.1%} F1 {s['f1']:.1%}"
                         for v, s in cells[name].items()}, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"provenance": provenance, "cells": cells},
                                   ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
