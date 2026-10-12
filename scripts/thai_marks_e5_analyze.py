"""E5: verify a fetched e5 run and write the registered readings (offline)."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from labbs2026.thai_marks import e5_analysis as e5


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id>")
    parser.add_argument("--cases", type=Path, required=True, help="the e5_cases.json that was attached")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    run = args.run_dir
    if (run / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (run / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (run / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((run / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    expected = {c["case"] for c in json.loads(args.cases.read_text(encoding="utf-8"))["cases"]}
    records, manifests = [], []
    for manifest_path in sorted((run / "e5" / "typhoon").glob("**/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["failures"]:
            raise SystemExit(f"{manifest_path}: failed reads {manifest['failures']}")
        records += _jsonl(manifest_path.parent / "records.jsonl")
        manifests.append({k: manifest[k] for k in ("model_id", "revision", "dtype_used", "items",
                                                   "wall_seconds", "torch", "transformers",
                                                   "cuda_device", "git_sha", "run_id")})
    got = {r["case"] for r in records}
    if got != expected:
        raise SystemExit(f"cases missing {sorted(expected - got)[:5]} extra {sorted(got - expected)[:5]}")
    pages = [r for r in records if r["kind"] == "page"]
    cells = e5.cell_summary(pages)
    reference_marks = sum(sum(x["marks"] for x in e5.page_lines(p)) for p in pages)
    absent_marks = sum(r["absent"] for r in e5.omitted_share_by_page(pages))
    arms = e5.line_arms(records)
    cost = {}
    for kind in ("page", "line_tight", "line_masked"):
        sel = [r for r in records if r["kind"] == kind]
        cost[kind] = {"reads": len(sel), "generated_tokens": sum(r["generated_tokens"] for r in sel),
                      "visual_tokens": sum(r["visual_tokens"] for r in sel),
                      "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in sel)}
    overall = absent_marks / reference_marks if reference_marks else 0.0
    out = {
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE", "synthetic": True,
        "draft": "docs/stage0/E5_SYNTHETIC_OMISSION_DRAFT.md", "manifests": manifests,
        "gpu_hours": sum(m["wall_seconds"] for m in manifests) / 3600,
        "omitted_share_overall": overall, "cells": cells,
        "D1_density_18_minus_4": e5.pooled_contrast(pages, {"lines": 18}, {"lines": 4}),
        "D2_size_24_minus_44": e5.pooled_contrast(pages, {"font_px": 24}, {"font_px": 44}),
        "line_arms": {k: v for k, v in arms.items() if k != "rows"},
        "line_arms_reading": e5.reading(arms),
        "cost": cost, "reads_by_kind": Counter(r["kind"] for r in records),
        "line_rows": arms["rows"],
    }
    if overall < 0.02:
        out["reading_overall"] = "clean_synthetic_text_almost_never_omitted"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("omitted_share_overall", "D1_density_18_minus_4",
                                          "D2_size_24_minus_44", "line_arms", "line_arms_reading",
                                          "cost")}, indent=1))
    for name, c in cells.items():
        print(f"{name}: omitted {c['omitted_share']:.1%} {c['omitted_ci95']}  "
              f"misread in found {c['misread_share_in_found_lines']:.1%}")


if __name__ == "__main__":
    main()
