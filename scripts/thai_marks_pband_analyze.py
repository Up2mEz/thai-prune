"""Verify the fetched P-BAND run and P-ZOOM-3's band reads, and write the P-BAND summary (offline)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import yaml

from labbs2026.thai_marks import p_band_analysis as pb

_SPEC = importlib.util.spec_from_file_location(
    "thai_marks_pzoom2_analyze", Path(__file__).resolve().parent / "thai_marks_pzoom2_analyze.py")
pz2s = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pz2s)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory of the P-BAND run (48 pages)")
    parser.add_argument("--pzoom3-run-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory of P-ZOOM-3 (bands100 of 21 pages)")
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="Typhoon's T1 records.jsonl: the whole-page TYPHOON_CARD reads")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    cfg_band = args.root / "configs/thai_marks/p_band.yaml"
    cfg_zoom3 = args.root / "configs/thai_marks/p_zoom3.yaml"
    pages_ids = {}
    for name, cfg in (("p_band", cfg_band), ("p_zoom3", cfg_zoom3)):
        pages_cfg = yaml.safe_load(cfg.read_text("utf-8"))["pages"]
        path = args.root / pages_cfg["file"]
        if _sha256(path) != pages_cfg["sha256"]:
            raise SystemExit(f"{name}: page list does not match the hash in its config")
        pages_ids[name] = [p["id"] for p in json.loads(path.read_text(encoding="utf-8"))["pages"]]
    overlap = set(pages_ids["p_band"]) & set(pages_ids["p_zoom3"])
    if overlap:
        raise SystemExit(f"page lists overlap: {sorted(overlap)[:3]}")

    band_run = pz2s.load_run(args.run_dir, cfg_band, [])
    zoom_run = pz2s.load_run(args.pzoom3_run_dir, cfg_zoom3, [])
    band_records = [r for r in band_run[3] if r["view"] == "bands100"]
    zoom_records = [r for r in zoom_run[3] if r["view"] == "bands100"]
    sigs = {n: [pz2s.stack_signature(m) for m in run[2]] for n, run in
            (("p_band", band_run), ("p_zoom3", zoom_run))}
    same_stack = all(s == sigs["p_zoom3"][0] for v in sigs.values() for s in v)

    t1 = {r["id"]: r for r in map(json.loads, args.t1_records.read_text(encoding="utf-8").splitlines())
          if r["task"] == "Full-page OCR" and r["prompt_kind"] == "TYPHOON_CARD"}
    page_ids = sorted(pages_ids["p_band"] + pages_ids["p_zoom3"])
    pages = pb.assemble_pages(t1, band_records + zoom_records, page_ids)
    result = pb.analyze(pages, subgroups={"pzoom_21_selected_for_omissions": set(pages_ids["p_zoom3"]),
                                          "new_48": set(pages_ids["p_band"])})
    if not same_stack:
        result["headline"]["label"] = "stack_differs"  # registered: no label across different stacks
    out = {
        "runs": {"p_band": {"run": band_run[0]["run_id"], "git_sha": band_run[0]["git_sha"],
                            "gpus": band_run[0]["gpus"], "manifests": band_run[2]},
                 "p_zoom3": {"run": zoom_run[0]["run_id"], "git_sha": zoom_run[0]["git_sha"],
                             "manifests": zoom_run[2]}},
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "gpu_hours": {"p_band": sum(m["wall_seconds"] for m in band_run[2]) / 3600,
                      "p_band_per_gpu_sum": sum(m["wall_seconds"] for m in band_run[2]) / 3600,
                      "p_band_longest_leg": max(m["wall_seconds"] for m in band_run[2]) / 3600},
        "same_stack": same_stack, "stack_signatures": sigs,
        "visual_token_check": {"p_band": pz2s.visual_token_check(band_records),
                               "p_zoom3": pz2s.visual_token_check(zoom_records)},
        **result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    m = result["micro"]
    print("pages", result["pages"], "| same stack", same_stack, "| GPU-hours (sum of legs / longest leg)",
          round(out["gpu_hours"]["p_band_per_gpu_sum"], 2), round(out["gpu_hours"]["p_band_longest_leg"], 2))
    for v in pb.VARIANTS:
        print(f"{v:13s} R {m[v]['recall']:.4f}  P {m[v]['precision']:.4f}  F1 {m[v]['f1']:.4f}"
              f"  correct {m[v]['correct']}  output marks {m[v]['output_marks']}")
    for v, c in result["contrasts_vs_whole"].items():
        print(f"{v:13s} dF1 {c['delta']*100:+.3f} pts [{c['ci_low']*100:+.3f}, {c['ci_high']*100:+.3f}]"
              f"  dR {c['delta_recall']*100:+.3f}  dP {c['delta_precision']*100:+.3f}  -> {c['label']}")
    print("headline:", result["headline"]["variant"], result["headline"].get("label"),
          "| CI half-width (pts)", round(result["ci_halfwidth_headline"] * 100, 3))
    print("pages better/equal/worse (bands_dedup, marks):", result["pages_better_equal_worse"])
    print("cost:", result["cost"])


if __name__ == "__main__":
    main()
