"""T5b offline dev check: stop at a detected loop, on T5 outputs (no inference)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.loop_cut import variant_a, variant_b
from labbs2026.thai_marks.t5_analysis import summarize_t5

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched T5 artifacts/<run_id>")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    from transformers import AutoTokenizer

    # Typhoon's tokenizer is Qwen3-VL-2B's (same vocabulary); tokenizer only.
    tok = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    paths = sorted((args.run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
    records = [json.loads(line) for p in paths for line in p.open(encoding="utf-8") if line.strip()]
    out_records, removed = [], {}
    for r in records:
        if r["arm"] not in ("greedy", "ngram_block"):
            continue
        out_records.append(r)
        for tag, cut in (("A", variant_a), ("B", variant_b)):
            text = cut(r)
            name = f"{r['arm']}+{tag}"
            kept = len(tok.encode(text, add_special_tokens=False)) if text != r["raw_output"] else None
            saved = max(0, r["generated_tokens"] - kept) if kept is not None else 0
            out_records.append({**r, "arm": name, "raw_output": text,
                                "generated_tokens": r["generated_tokens"] - saved,
                                "seconds_generate": r["seconds_generate"] * (
                                    (r["generated_tokens"] - saved) / max(1, r["generated_tokens"])),
                                "reached_max_new_tokens": r["reached_max_new_tokens"] and saved == 0})
            cell = f"{r['task']} / {r['prompt_kind']}"
            entry = removed.setdefault(cell, {}).setdefault(name, {"outputs_cut": 0,
                                                                   "loop_free_cut": 0,
                                                                   "tokens_saved": 0})
            if text != r["raw_output"]:
                entry["outputs_cut"] += 1
                entry["loop_free_cut"] += int(not r["reached_max_new_tokens"])
                entry["tokens_saved"] += saved
    summary = summarize_t5(out_records)
    result = {"provenance": {"git_sha": _git("rev-parse", "HEAD"),
                             "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                             "rule": "docs/stage0/T5B_STOP_AT_LOOP_DRAFT.md",
                             "records_sha256": {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                for p in paths},
                             "tokenizer": TOKENIZER,
                             "seconds_note": "seconds of cut outputs scaled by kept/generated tokens"},
              "cuts": removed, "summary": summary}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for cell, block in summary.items():
        print("==", cell)
        for name, arm in block["arms"].items():
            m, d = arm["order_free_marks"], arm.get("delta_f1_vs_greedy")
            c = removed.get(cell, {}).get(name, {})
            print(f"  {name:15s} F1 {m['f1']:.4f} R {m['recall']:.4f} P {m['precision']:.4f}"
                  + (f" dF1 {d['delta']:+.4f} [{d['ci_low']:+.4f},{d['ci_high']:+.4f}]" if d else "")
                  + (f" loop-free dF1 {arm['loop_free_delta_f1_vs_greedy']:+.4f}"
                     if "loop_free_delta_f1_vs_greedy" in arm else "")
                  + (f" cut {c['outputs_cut']} (loop-free {c['loop_free_cut']}) tokens saved {c['tokens_saved']}"
                     if c else ""))


if __name__ == "__main__":
    main()
