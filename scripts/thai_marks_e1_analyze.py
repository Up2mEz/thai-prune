"""E1: guards and the registered gate from a fetched E1 run (test `e1`; runs before 2026-10-04 named it `t6`)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from labbs2026.thai_marks.analysis import anchored_cer, chance_threshold
from labbs2026.thai_marks.attribution import reference_lines
from labbs2026.thai_marks.confidence import (
    aligned_pairs_full_page,
    cluster_scores,
    gate,
    label_clusters,
    token_offsets,
)
from labbs2026.thai_marks.decompose import align_anchored
from labbs2026.thai_marks.extract import extract_text

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched E1 artifacts/<run_id>")
    parser.add_argument("--t5-run-dir", type=Path, required=True, help="the T5 run the cases came from")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    root = args.run_dir
    if (root / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (root / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    scored = [r for p in sorted((root).glob("*/typhoon/**/records.jsonl")) for r in _jsonl(p)]
    t5 = {(r["task"], r["prompt_kind"], r["id"]): r
          for p in sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
          for r in _jsonl(p) if r["arm"] == "greedy"}

    # Guards over every case.
    agree = total = 0
    roundtrip_fail = []
    for r in scored:
        s = r["scores"]
        total += len(s["token_ids"])
        agree += sum(a == t for a, t in zip(s["argmax"], s["token_ids"]))
        if not s["roundtrip"]:
            roundtrip_fail.append(r["case"])
    guards = {"greedy_consistency": agree / max(1, total), "tokens": total,
              "roundtrip_failures": roundtrip_fail}

    # Text recognition: located under the BQ cell's null threshold.
    tr_bq = [t5[k] for k in sorted(t5) if k[0] == "Text recognition" and k[1] == "BENCHMARK_QUESTION"]
    chance = chance_threshold([extract_text(r["reference"]) for r in tr_bq],
                              [extract_text(r["raw_output"]) for r in tr_bq], seed=20260928)

    cells: dict[str, list[list[dict]]] = collections.defaultdict(list)
    excluded = collections.Counter()
    for r in scored:
        source = t5[(r["task"], r["prompt_kind"], r["id"])]
        if source["reached_max_new_tokens"]:
            excluded["loop"] += 1
            continue
        raw, s = source["raw_output"], r["scores"]
        if r["task"] == "Full-page OCR":
            labelled = label_clusters(raw, aligned_pairs_full_page(source["reference"], raw))
        else:
            ref = " ".join(reference_lines(source["reference"]))
            if anchored_cer(extract_text(source["reference"]), extract_text(raw)) >= chance["threshold"]:
                excluded["not_located"] += 1
                continue
            pairs, start, end = align_anchored(ref, raw)
            labelled = label_clusters(raw, [(ref, a, h) for a, h in pairs
                                            if a is not None and h is not None], span=(start, end))
        try:
            offsets = token_offsets(tok, raw, s["token_ids"])
        except ValueError:
            excluded["token_mismatch"] += 1
            continue
        cells[f"{r['task']} / {r['prompt_kind']}"].append(
            cluster_scores(labelled, offsets, s["logprob"], s["entropy"]))

    result = {"guards": guards, "excluded": dict(excluded), "tr_located_threshold": chance,
              "gate_rule": "docs/stage0/E1_CONFIDENCE_DRAFT.md §4",
              "cells": {name: {"s_min": gate(items, "s_min"), "s_ent": gate(items, "s_ent")}
                        for name, items in sorted(cells.items())}}
    full = [result["cells"].get(f"Full-page OCR / {p}", {}).get("s_min", {})
            for p in ("BENCHMARK_QUESTION", "TYPHOON_CARD")]
    valid = guards["greedy_consistency"] >= 0.99 and not roundtrip_fail
    result["verdict"] = ("INVALID (guard)" if not valid else
                         "PASS" if all(g.get("auroc") is not None and g["auroc"] >= 0.75
                                       and g["recall_at_5pct"] >= 0.40 for g in full) else "FAIL")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"guards": {k: v for k, v in guards.items() if k != "roundtrip_failures"},
                      "roundtrip_failures": len(roundtrip_fail), "excluded": dict(excluded),
                      "verdict": result["verdict"]}, indent=1))
    for name, c in result["cells"].items():
        g, e = c["s_min"], c["s_ent"]
        print(f"{name}: clusters {g['clusters']} errors {g['errors']} | s_min AUROC {g['auroc']:.3f} "
              f"{g['auroc_ci']} recall@5% {g['recall_at_5pct']:.3f} {g['recall_ci']} | "
              f"s_ent AUROC {e['auroc']:.3f} recall@5% {e['recall_at_5pct']:.3f}")


if __name__ == "__main__":
    main()
