"""E1-B1 offline dev check: confidence-gated, lexicon-checked swap on E1 scores."""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.confidence import aligned_pairs_full_page, label_clusters, token_offsets
from labbs2026.thai_marks.confidence_fix import apply, flag_threshold, propose
from labbs2026.thai_marks.lexicon import lexicon
from labbs2026.thai_marks.order_free import mark_counts, prf
from labbs2026.thai_marks.t5_analysis import paired_bootstrap_delta_f1

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _labels(reference: str, raw: str) -> dict[int, bool]:
    return {c["start"]: c["error"] for c in label_clusters(raw, aligned_pairs_full_page(reference, raw))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1-run-dir", type=Path, required=True)
    parser.add_argument("--t5-run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    from pythainlp.tokenize import word_tokenize
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    words = lexicon()
    segment = lambda s: word_tokenize(s, engine="newmm", keep_whitespace=True)  # noqa: E731
    decode = lambda t: tok.decode([t], clean_up_tokenization_spaces=False)  # noqa: E731
    scored = {r["case"]: r["scores"] for p in sorted((args.e1_run_dir).glob("*/typhoon/*/records.jsonl"))
              for r in _jsonl(p)}
    t5 = [r for p in sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
          for r in _jsonl(p) if r["arm"] == "greedy" and not r["reached_max_new_tokens"]]
    cells: dict[str, list[dict]] = collections.defaultdict(list)
    for r in t5:
        cells[f"{r['task']} / {r['prompt_kind']}"].append(r)

    out: dict = {"provenance": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                          text=True, check=True).stdout.strip(),
                                "rule": "docs/stage0/E1B_LEXICON_GATED_SWAP_DRAFT.md"}, "cells": {}}
    examples = []
    for cell, rows in sorted(cells.items()):
        rows = sorted(rows, key=lambda r: r["id"])
        sc = [scored[f"{r['task']}|{r['prompt_kind']}|{r['id']}"] for r in rows]
        offs = [token_offsets(tok, r["raw_output"], s["token_ids"]) for r, s in zip(rows, sc)]
        texts = [[r["raw_output"][a:b] for a, b in o] for r, o in zip(rows, offs)]
        threshold = flag_threshold([s["logprob"] for s in sc], texts)
        base_counts, new_counts = [], []
        tally = collections.Counter()
        for r, s, o in zip(rows, sc, offs):
            raw = r["raw_output"]
            swaps = propose(raw, o, s["logprob"], s["top_ids"], s["top_logprobs"], threshold,
                            decode, segment, words)
            edited = apply(raw, swaps)
            base_counts.append(mark_counts(r["reference"], raw, residual=True))
            new_counts.append(mark_counts(r["reference"], edited, residual=True))
            tally["swaps"] += len(swaps)
            if swaps and r["task"] == "Full-page OCR":
                before, after = _labels(r["reference"], raw), _labels(r["reference"], edited)
                shift = 0
                for sw in sorted(swaps, key=lambda s: s["start"]):
                    old, new = before.get(sw["start"]), after.get(sw["start"] + shift)
                    shift += len(sw["new"]) - len(sw["old"])
                    if old is True and new is False:
                        tally["fixed"] += 1
                    elif old is False and new is True:
                        tally["broken"] += 1
                    else:
                        tally["unlabelled_or_unchanged"] += 1
                    if len(examples) < 40:
                        examples.append({"cell": cell, "id": r["id"], "w0": sw["w0"], "old": sw["old"],
                                         "new": sw["new"], "before": old, "after": new})
        base, new = prf(base_counts), prf(new_counts)
        out["cells"][cell] = {"threshold_logprob": threshold, **tally,
                              "f1_greedy": base["f1"], "f1_swap": new["f1"],
                              "recall": [base["recall"], new["recall"]],
                              "precision": [base["precision"], new["precision"]],
                              "delta_f1": paired_bootstrap_delta_f1(new_counts, base_counts)}
    full = [out["cells"][c] for c in out["cells"] if c.startswith("Full-page")]
    fixed = sum(c.get("fixed", 0) for c in full)
    broken = sum(c.get("broken", 0) for c in full)
    out["verdict"] = ("PASS" if all(c["f1_swap"] >= c["f1_greedy"] for c in out["cells"].values())
                      and all(c["f1_swap"] > c["f1_greedy"] for c in full) and broken <= fixed
                      else "FAIL")
    out["examples"] = examples
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for cell, c in out["cells"].items():
        d = c["delta_f1"]
        print(f"{cell}: swaps {c['swaps']} fixed {c.get('fixed', '-')} broken {c.get('broken', '-')} "
              f"F1 {c['f1_greedy']:.4f} -> {c['f1_swap']:.4f} (d {d['delta']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}])")
    print("verdict:", out["verdict"])
    for e in examples[:20]:
        print("  ", e["cell"][:14], e["w0"], repr(e["old"]), "->", repr(e["new"]), e["before"], "->", e["after"])


if __name__ == "__main__":
    main()
