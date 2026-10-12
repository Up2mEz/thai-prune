"""E4b: verify a fetched t6 run (views of p_zoom5.yaml) and write the registered readings (offline)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from labbs2026.thai_marks import e4b_analysis as e4
from labbs2026.thai_marks import p_zoom2_analysis as pz2
from labbs2026.thai_marks.p_zoom_analysis import score_page


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id>")
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="Typhoon's T1 records.jsonl (stack check and baseline)")
    parser.add_argument("--root", type=Path, default=Path("."))
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
    config = yaml.safe_load((args.root / "configs/thai_marks/p_zoom5.yaml").read_text("utf-8"))
    pages_path = args.root / config["pages"]["file"]
    if hashlib.sha256(pages_path.read_bytes()).hexdigest() != config["pages"]["sha256"]:
        raise SystemExit("page list does not match the hash in p_zoom5.yaml")
    pages = json.loads(pages_path.read_text(encoding="utf-8"))["pages"]

    records, manifests = [], []
    for manifest_path in sorted((run / "t6" / "typhoon").glob("**/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["failures"]:
            raise SystemExit(f"{manifest_path}: failed reads {manifest['failures']}")
        records += _jsonl(manifest_path.parent / "records.jsonl")
        manifests.append({k: manifest[k] for k in ("model_id", "revision", "dtype_used", "items",
                                                   "wall_seconds", "torch", "transformers",
                                                   "cuda_device", "git_sha", "run_id")})
    assembled = pz2.assemble_views(records, pages, config["views"])
    scores = {view: pz2.score_view(page_list) for view, page_list in assembled.items()}
    t1 = {(r["id"], r["prompt_kind"]): r for r in _jsonl(args.t1_records) if r["task"] == "Full-page OCR"}
    baseline_outputs = {p["id"]: t1[(p["id"], "TYPHOON_CARD")]["raw_output"] for p in pages}
    repeat_outputs = {p["id"]: "\n".join(p["tile_outputs"]) for p in assembled["repeat"]}
    identical = pz2.identical_pages(repeat_outputs, baseline_outputs)

    reads = {}
    for r in records:
        c = reads.setdefault(r["view"], {"reads": 0, "generated_tokens": 0, "visual_tokens": 0,
                                          "reached_max_new_tokens": 0})
        c["reads"] += 1
        c["generated_tokens"] += r["generated_tokens"]
        c["visual_tokens"] += r["visual_tokens"]
        c["reached_max_new_tokens"] += bool(r["reached_max_new_tokens"])
    result = e4.analyze(scores)
    out = {"claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE", "draft": config["draft"],
           "manifests": manifests, "gpu_hours": sum(m["wall_seconds"] for m in manifests) / 3600,
           "repeat_identical_to_t1": identical, "reads": reads, **result,
           "page_scores": {v: [{"id": p["id"], **s} for p, s in zip(pages, per)]
                           for v, per in scores.items()}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("text_share_single", "control_text_share", "W3_union",
                                          "W5_union", "M3_union", "D1_M3_minus_W3", "D2_M3_minus_W5",
                                          "whole_page_k_read_curve", "reading",
                                          "repeat_identical_to_t1", "reads")}, indent=1))


if __name__ == "__main__":
    main()
