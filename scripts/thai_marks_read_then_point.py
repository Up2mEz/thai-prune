"""G1 dev check: read-then-point on existing Typhoon Text recognition outputs (offline)."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

from labbs2026.thai_marks.analysis import chance_threshold, score_t1_record_v2, summarize_t1_v2
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.order_free import mark_counts, prf
from labbs2026.thai_marks.read_then_point import point

TASK = "Text recognition"
SEED = 20260928


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True, help="t1/typhoon/records.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    rows = [json.loads(line) for line in args.records.open(encoding="utf-8") if line.strip()]
    by_id: dict[str, dict] = {}
    for r in rows:
        if r["task"] == TASK:
            by_id.setdefault(r["id"], {})[r["prompt_kind"]] = r
    ids = sorted(i for i, p in by_id.items() if {"BENCHMARK_QUESTION", "TYPHOON_CARD"} <= set(p))
    bq = [by_id[i]["BENCHMARK_QUESTION"] for i in ids]
    chance = chance_threshold([extract_text(r["reference"]) for r in bq],
                              [extract_text(r["raw_output"]) for r in bq], seed=SEED)
    picks = {i: point(by_id[i]["BENCHMARK_QUESTION"]["raw_output"],
                      by_id[i]["TYPHOON_CARD"]["raw_output"]) for i in ids}

    def as_record(i: str, answer: str, kind: str) -> dict:
        # One prompt label for every variant: the cell is "answers to the
        # benchmark question", whichever way they were produced.
        return {**by_id[i]["BENCHMARK_QUESTION"], "raw_output": answer,
                "prompt_kind": "BENCHMARK_QUESTION", "variant": kind}

    variants = {
        "BQ": {i: by_id[i]["BENCHMARK_QUESTION"]["raw_output"] for i in ids},
        "TC": {i: by_id[i]["TYPHOON_CARD"]["raw_output"] for i in ids},
        "read_then_point": {i: picks[i]["answer"] for i in ids},
    }
    out: dict = {"provenance": {"git_sha": _git("rev-parse", "HEAD"),
                                "git_dirty": bool(_git("status", "--porcelain",
                                                       "--untracked-files=no")),
                                "records_sha256": hashlib.sha256(args.records.read_bytes()).hexdigest(),
                                "rule": "docs/stage0/G1_READ_THEN_POINT_DRAFT.md",
                                "located_threshold_from": "BQ cell", "chance": chance},
                 "items": len(ids), "cells": {}}
    scored_by: dict[str, dict] = {}
    for name, answers in variants.items():
        scored = [score_t1_record_v2(as_record(i, answers[i], name), located_below=chance["threshold"])
                  for i in ids]
        scored_by[name] = {s["id"]: s for s in scored}
        counts = [mark_counts(by_id[i]["BENCHMARK_QUESTION"]["reference"], answers[i], mode="global")
                  for i in ids]
        ratios = [len(extract_text(answers[i])) / max(1, len(extract_text(by_id[i]["BENCHMARK_QUESTION"]["reference"])))
                  for i in ids]
        out["cells"][name] = {"summary_v2": summarize_t1_v2(scored),
                              "global_marks": prf(counts),
                              "median_length_ratio": statistics.median(ratios)}
    oracle = {i: min((scored_by["BQ"][i], scored_by["read_then_point"][i]),
                     key=lambda s: (s["cer"] if s["cer"] is not None else 9)) for i in ids}
    out["cells"]["oracle_bound_BQ_or_rule"] = {"summary_v2": summarize_t1_v2(list(oracle.values()))}
    out["fell_back"] = sum(p["fell_back"] for p in picks.values())
    out["unlocated_under_BQ"] = [
        {"id": i, "rule_located": scored_by["read_then_point"][i]["located"],
         "bq_cer": scored_by["BQ"][i]["cer"], "rule_cer": scored_by["read_then_point"][i]["cer"],
         "fell_back": picks[i]["fell_back"], "similarity": picks[i]["similarity"]}
        for i in ids if not scored_by["BQ"][i]["located"]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, cell in out["cells"].items():
        s = cell["summary_v2"]
        g = cell.get("global_marks", {})
        print(name, "micro_cer", round(s["micro_cer"]["estimate"], 4),
              "median_cer", round(s["median_cer"], 4), "located", round(s["located_rate"], 3),
              {m: round(s[m]["error"]["estimate"], 4) for m in ("TONE", "UPPER", "LOWER") if m in s},
              {k: (round(g[k], 4) if isinstance(g.get(k), float) else g.get(k))
               for k in ("recall", "precision", "f1")} if g else "",
              cell.get("median_length_ratio"))
    print("fell back:", out["fell_back"], "| unlocated under BQ:", out["unlocated_under_BQ"])


if __name__ == "__main__":
    main()
