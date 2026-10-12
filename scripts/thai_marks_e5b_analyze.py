"""E5b: verify a fetched e5 run on sentence pages and write the registered readings against E5 (offline)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from labbs2026.thai_marks import e5b_analysis as e5b


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _load(run: Path, cases: Path) -> tuple[list[dict], list[dict]]:
    if (run / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (run / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (run / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((run / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    expected = {c["case"] for c in json.loads(cases.read_text(encoding="utf-8"))["cases"]
                if c["kind"] == "page"}
    records, manifests = [], []
    for manifest_path in sorted((run / "e5" / "typhoon").glob("**/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["failures"]:
            raise SystemExit(f"{manifest_path}: failed reads {manifest['failures']}")
        records += _jsonl(manifest_path.parent / "records.jsonl")
        manifests.append({k: manifest[k] for k in ("model_id", "revision", "dtype_used", "items",
                                                   "wall_seconds", "torch", "transformers",
                                                   "cuda_device", "git_sha", "run_id")})
    pages = [r for r in records if r["kind"] == "page"]
    if {r["case"] for r in pages} != expected:
        raise SystemExit("page cases do not match the cases file")
    return pages, manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id> of E5b")
    parser.add_argument("--cases", type=Path, required=True, help="the sentence cases json that was attached")
    parser.add_argument("--e5-run-dir", type=Path, required=True, help="fetched artifacts/<run_id> of E5 (words)")
    parser.add_argument("--e5-cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    new_pages, manifests = _load(args.run_dir, args.cases)
    old_pages, _ = _load(args.e5_run_dir, args.e5_cases)
    result = e5b.analyze(new_pages, old_pages)
    cost = {"reads": len(new_pages), "generated_tokens": sum(r["generated_tokens"] for r in new_pages),
            "visual_tokens": sum(r["visual_tokens"] for r in new_pages),
            "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in new_pages)}
    out = {"claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE", "synthetic": True,
           "draft": "docs/stage0/E5B_MEANINGFUL_TEXT_DRAFT.md", "manifests": manifests,
           "gpu_hours": sum(m["wall_seconds"] for m in manifests) / 3600, "cost": cost, **result}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("omitted_share_overall", "reading_omission",
                                          "D1_density_18_minus_4", "D2_size_24_minus_44",
                                          "D3_misread_meaningful_minus_words", "D3_reading",
                                          "D3_by_size", "cost")}, indent=1))
    for name, c in out["cells"].items():
        print(f"{name}: omitted {c['omitted_share']:.1%} {c['omitted_ci95']}  "
              f"misread in found {c['misread_share_in_found_lines']:.1%}")


if __name__ == "__main__":
    main()
