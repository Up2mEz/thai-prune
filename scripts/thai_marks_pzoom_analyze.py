"""Verify a fetched P-ZOOM (t4) run and write its pre-registered summary (offline)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from labbs2026.thai_marks import p_zoom_analysis as pza


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

    config = yaml.safe_load((args.root / "configs/thai_marks/p_zoom.yaml").read_text("utf-8"))
    pages_path = args.root / config["pages"]["file"]
    if _sha256(pages_path) != config["pages"]["sha256"]:
        raise SystemExit("page list does not match the hash in p_zoom.yaml")
    pages = json.loads(pages_path.read_text(encoding="utf-8"))["pages"]
    tiles = int(config["tiling"]["rows"]) * int(config["tiling"]["cols"])

    legs = sorted((root / "t4" / "typhoon").glob("**/manifest.json"))
    if not legs:
        raise SystemExit("no t4/typhoon manifest in the run")
    records, manifests = [], []
    for manifest_path in legs:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["failures"]:
            raise SystemExit(f"{manifest_path}: failed reads {manifest['failures']}")
        records += _jsonl(manifest_path.parent / "records.jsonl")
        manifests.append({k: manifest[k] for k in (
            "model_id", "revision", "dtype_used", "items", "generation", "wall_seconds",
            "setup_seconds", "torch", "transformers", "cuda_device", "git_sha", "run_id")})
    assembled = pza.assemble_pages(records, pages, tiles)
    scored = [pza.score_page(p["reference"], p["tile_outputs"], p["absent"], p["control"])
              for p in assembled]
    summary = pza.summarize(scored)

    # Zoom-free baseline: the same pages read whole with the same prompt (T1, TYPHOON_CARD).
    # A scorer check: the BENCHMARK_QUESTION whole-page read selected these lines as absent,
    # so scoring it must recover (almost) none of them and (almost) all control lines.
    t1 = {(r["id"], r["prompt_kind"]): r for r in _jsonl(args.t1_records)
          if r["task"] == "Full-page OCR"}

    def whole_page(prompt_kind: str) -> list[dict]:
        return [pza.score_page(p["reference"], [t1[(p["id"], prompt_kind)]["raw_output"]],
                               p["absent"], p["control"]) for p in assembled]

    comparison = pza.compare_with_baseline(scored, whole_page("TYPHOON_CARD"))
    scorer_check = pza.summarize(whole_page("BENCHMARK_QUESTION"))
    out = {
        "run": success["run_id"], "git_sha": success["git_sha"], "gpus": success["gpus"],
        "claim_level": config["claim_level"], "manifests": manifests,
        "gpu_hours": sum(m["wall_seconds"] for m in manifests) / 3600,
        "reads": len(records),
        "generated_tokens": sum(r["generated_tokens"] for r in records),
        "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in records),
        "zoom_factor": {"min": min(r["zoom_factor"] for r in records),
                        "max": max(r["zoom_factor"] for r in records)},
        "summary": summary,
        "chance_rate": pza.chance_rate(assembled),
        "comparison_with_whole_page_typhoon_card": comparison,
        "scorer_check_whole_page_benchmark_question": scorer_check,
        "thresholds": {"recovery": pza.RECOVERY_THRESHOLD, "gain": pza.GAIN_THRESHOLD},
        "reading": pza.reading(summary, comparison),
        "pages": [{"id": p["id"], **s} for p, s in zip(assembled, scored)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("run", "reads", "gpu_hours", "chance_rate", "reading")},
                     indent=1))
    print("gain over whole page", comparison["gain_share"], "loss", comparison["loss_share"],
          "| whole-page TYPHOON_CARD absent shares", comparison["baseline"]["absent"]["share_of_marks"])
    for group, block in summary.items():
        print(group, block["lines"], "lines", block["marks"], "marks",
              block["lines_by_outcome"], {o: f"{v:.1%}" for o, v in block["share_of_marks"].items()
                                          if v is not None})


if __name__ == "__main__":
    main()
