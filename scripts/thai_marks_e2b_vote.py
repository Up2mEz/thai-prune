"""E2b offline dev check: majority vote of re-reads at E1-flagged places (no inference)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from labbs2026.thai_marks.confidence import (
    aligned_pairs_full_page,
    clusters,
    label_clusters,
    token_offsets,
)
from labbs2026.thai_marks.order_free import mark_counts, prf
from labbs2026.thai_marks.reread_probe import apply_edits, flagged_edits
from labbs2026.thai_marks.t5_analysis import paired_bootstrap_delta_f1

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")
PROMPT, CELL = "TYPHOON_CARD", "Full-page OCR"
THRESHOLD = 0.043  # E1's 5% s_min threshold, fixed in the E2b draft
VARIANTS = {"V5": ("bands", "tiles", "pad", "scale90"), "V3": ("bands", "pad")}


def _edits(job):
    return flagged_edits(*job)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1-run-dir", type=Path, required=True)
    parser.add_argument("--t5-run-dir", type=Path, required=True)
    parser.add_argument("--tiles", type=Path, required=True)
    parser.add_argument("--views", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    scores = {r["case"]: r["scores"] for p in sorted(args.e1_run_dir.glob("*/typhoon/*/records.jsonl"))
              for r in _jsonl(p)}
    t5 = {r["id"]: r for p in sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
          for r in _jsonl(p) if r["arm"] == "greedy" and r["task"] == CELL and r["prompt_kind"] == PROMPT}
    reads: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in _jsonl(args.tiles):
        reads[r["id"]]["tiles"].append(r["raw_output"])
    for r in _jsonl(args.views):
        reads[r["id"]][r["view"]].append(r["raw_output"])

    result: dict = {"provenance": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                             text=True, check=True).stdout.strip(),
                                   "rule": "docs/stage0/E2B_FLAGGED_VOTE_DRAFT.md",
                                   "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                                     for p in (args.tiles, args.views)}},
                    "threshold": THRESHOLD, "variants": {}}
    jobs = {}
    for pid in sorted(reads):
        r = t5[pid]
        raw, s = r["raw_output"], scores[f"{CELL}|{PROMPT}|{pid}"]
        offs = token_offsets(tok, raw, s["token_ids"])
        scored = []
        for start, end in clusters(raw):
            hits = [s["logprob"][k] for k, (a, b) in enumerate(offs) if a < end and b > start]
            if hits:
                scored.append((start, end, -min(hits)))
        for name, views in VARIANTS.items():
            jobs[(name, pid)] = (raw, scored, {v: reads[pid][v] for v in views}, THRESHOLD)
    with ProcessPoolExecutor(6) as pool:
        done = dict(zip(jobs, pool.map(_edits, jobs.values())))
    for name, views in VARIANTS.items():
        base, new, tally, examples = [], [], collections.Counter(), []
        for pid in sorted(reads):
            r = t5[pid]
            raw = r["raw_output"]
            edits = done[(name, pid)]
            edited = apply_edits(raw, edits)
            base.append(mark_counts(r["reference"], raw, residual=True))
            new.append(mark_counts(r["reference"], edited, residual=True))
            tally["edits"] += len(edits)
            before = {c["start"]: c["error"] for c in label_clusters(raw, aligned_pairs_full_page(r["reference"], raw))}
            after = {c["start"]: c["error"] for c in label_clusters(edited, aligned_pairs_full_page(r["reference"], edited))}
            shift = 0
            for start, end, rep in sorted(edits):
                b, a = before.get(start), after.get(start + shift)
                shift += len(rep) - (end - start)
                key = ("fixed" if b is True and a is False else "broken" if b is False and a is True
                       else "unlabelled_or_unchanged")
                tally[key] += 1
                if len(examples) < 25:
                    examples.append({"id": pid, "old": raw[start:end], "new": rep, "outcome": key,
                                     "context": raw[max(0, start - 6):end + 6]})
        b, n = prf(base), prf(new)
        verdict = "PASS" if tally["fixed"] > tally["broken"] and n["f1"] > b["f1"] else "FAIL"
        result["variants"][name] = {"views": views, **tally, "f1_greedy": b["f1"], "f1_vote": n["f1"],
                                    "recall": [b["recall"], n["recall"]], "precision": [b["precision"], n["precision"]],
                                    "delta_f1": paired_bootstrap_delta_f1(new, base), "verdict": verdict,
                                    "examples": examples}
        d = result["variants"][name]["delta_f1"]
        print(f"{name}: edits {tally['edits']} fixed {tally['fixed']} broken {tally['broken']} "
              f"other {tally['unlabelled_or_unchanged']} | F1 {b['f1']:.4f} -> {n['f1']:.4f} "
              f"(d {d['delta']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]) {verdict}")
        for e in examples[:12]:
            print("   ", e["id"], repr(e["context"]), repr(e["old"]), "->", repr(e["new"]), e["outcome"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
