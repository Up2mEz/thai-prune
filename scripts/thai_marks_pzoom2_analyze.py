"""Verify a fetched P-ZOOM-2 (t6) run and write its pre-registered summary (offline)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

import yaml

from labbs2026.thai_marks import p_zoom2_analysis as pz2
from labbs2026.thai_marks.p_zoom_analysis import score_page


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory")
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="Typhoon's T1 records.jsonl: the zoom-free whole-page baseline")
    parser.add_argument("--root", type=Path, default=Path("."))
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

    config = yaml.safe_load((args.root / "configs/thai_marks/p_zoom2.yaml").read_text("utf-8"))
    pages_path = args.root / config["pages"]["file"]
    if _sha256(pages_path) != config["pages"]["sha256"]:
        raise SystemExit("page list does not match the hash in p_zoom2.yaml")
    pages = json.loads(pages_path.read_text(encoding="utf-8"))["pages"]

    legs = sorted((root / "t6" / "typhoon").glob("**/manifest.json"))
    if not legs:
        raise SystemExit("no t6/typhoon manifest in the run")
    records, manifests = [], []
    for manifest_path in legs:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["failures"]:
            raise SystemExit(f"{manifest_path}: failed reads {manifest['failures']}")
        records += _jsonl(manifest_path.parent / "records.jsonl")
        manifests.append({k: manifest[k] for k in (
            "model_id", "revision", "dtype_used", "items", "generation", "wall_seconds",
            "setup_seconds", "torch", "transformers", "cuda_device", "git_sha", "run_id")})

    assembled = pz2.assemble_views(records, pages, config["views"])
    scores = {name: pz2.score_view(p) for name, p in assembled.items()}

    t1 = {(r["id"], r["prompt_kind"]): r for r in _jsonl(args.t1_records)
          if r["task"] == "Full-page OCR"}
    page_ids = [p["id"] for p in pages]
    baseline = [score_page(t1[(p["id"], "TYPHOON_CARD")]["reference"],
                           [t1[(p["id"], "TYPHOON_CARD")]["raw_output"]],
                           p["absent_lines"], p["control_lines"]) for p in pages]

    per_view_reads = collections.defaultdict(lambda: collections.Counter())
    for r in records:
        c = per_view_reads[r["view"]]
        c["reads"] += 1
        c["generated_tokens"] += r["generated_tokens"]
        c["visual_tokens"] += r["visual_tokens"]
        c["reached_max_new_tokens"] += bool(r["reached_max_new_tokens"])
        c["seconds_generate"] += r["seconds_generate"]
    zoom = {v: [min(r["zoom_factor"] for r in records if r["view"] == v),
                max(r["zoom_factor"] for r in records if r["view"] == v)]
            for v in per_view_reads}

    result = pz2.analyze(baseline, scores)
    out = {
        "run": success["run_id"], "git_sha": success["git_sha"], "gpus": success["gpus"],
        "claim_level": config["claim_level"], "manifests": manifests,
        "gpu_hours": sum(m["wall_seconds"] for m in manifests) / 3600,
        "reads": {v: dict(c) for v, c in per_view_reads.items()}, "zoom_factor": zoom,
        "pages": page_ids, **result,
        "page_scores": {name: [{"id": i, **s} for i, s in zip(page_ids, per_page)]
                        for name, per_page in scores.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in (
        "run", "gpu_hours", "perturbation_gain_N", "zoom_gain_Z", "Z_minus_N", "Z_minus_N_ci95",
        "union_absent_text_share", "reading")}, indent=1))
    for name, block in out["per_view"].items():
        print(f"{name:8s} absent text {block['absent_text_share']:.1%}  gain {block['gain_over_baseline']:.1%}"
              f"  loss {block['loss_vs_baseline']:.1%}  control text {block['control_text_share']:.1%}"
              f"  reads {out['reads'][name]['reads']} looped {out['reads'][name]['reached_max_new_tokens']}"
              f"  zoom {zoom[name]}")


if __name__ == "__main__":
    main()
