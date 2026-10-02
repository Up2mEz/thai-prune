"""Verify a fetched T5 run (checksums, GPUs, shards) and write its registered summaries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from labbs2026.thai_marks.t5_analysis import summarize_t5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory")
    parser.add_argument("--t1-records", type=Path, default=None,
                        help="T1 typhoon records.jsonl, for the greedy determinism check")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    root = args.run_dir
    if (root / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (root / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if _sha256(root / relative) != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    success = json.loads((root / "SUCCESS.json").read_text(encoding="utf-8"))

    legs = sorted((root / "t5" / "typhoon").glob("**/manifest.json"))
    shards, records = [], []
    for manifest_path in legs:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = _jsonl(manifest_path.parent / "records.jsonl")
        records += rows
        shards.append({"leg": manifest_path.parent.relative_to(root).as_posix(),
                       "items": manifest["items"], "records": len(rows),
                       "failures": manifest["failures"], "dtype": manifest["dtype_used"],
                       "cuda_device": manifest["cuda_device"],
                       "wall_seconds": manifest["wall_seconds"],
                       "setup_seconds": manifest["setup_seconds"],
                       "generation": manifest["generation"]})
    keys = [(r["id"], r["prompt_kind"], r["arm"]) for r in records]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate (id, prompt, arm) records across shards")
    t1 = None
    if args.t1_records:
        t1 = [r for r in _jsonl(args.t1_records)]
    out = {
        "run": success["run_id"], "git_sha": success["git_sha"], "gpus": success["gpus"],
        "shards": shards,
        "parallel_check": {
            "gpus_reported": success["gpus"],
            "legs": len(shards),
            "sum_shard_wall_seconds": sum(s["wall_seconds"] for s in shards),
            "max_shard_wall_seconds": max((s["wall_seconds"] for s in shards), default=None),
        },
        "records": len(records),
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "summary": summarize_t5(records, t1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("run", "gpus", "parallel_check", "records")}, indent=1))
    for cell, block in out["summary"].items():
        print(cell, "items", block["items"], "loop-free", block["loop_free_items"],
              "greedy==T1", block.get("greedy_identical_to_t1"))
        for name, arm in block["arms"].items():
            m = arm["order_free_marks"]
            d = arm.get("delta_f1_vs_greedy")
            print(f"   {name:12s} loop {arm['loop_rate']:.3f}  F1 {m['f1']:.4f} R {m['recall']:.4f}"
                  f" P {m['precision']:.4f}  loop-free identical {arm['loop_free_identical_to_greedy']}"
                  f"  dF1 {d['delta']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]" if d else
                  f"   {name:12s} loop {arm['loop_rate']:.3f}  F1 {m['f1']:.4f} R {m['recall']:.4f}"
                  f" P {m['precision']:.4f}", f" tokens {arm['total_generated_tokens']}"
                  f" s {arm['total_seconds']:.0f}")


if __name__ == "__main__":
    main()
