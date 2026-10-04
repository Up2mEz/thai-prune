"""Verify fetched P-ZOOM-2 (t6) and, optionally, P-ZOOM-3 (t6 controls) runs and write the
pre-registered summaries (offline)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

import yaml

from labbs2026.thai_marks import attribution
from labbs2026.thai_marks import p_zoom2_analysis as pz2
from labbs2026.thai_marks.p_zoom_analysis import score_page


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_run(run_dir: Path, config_path: Path, pages: list[dict]):
    """Checksum-verified run: (success, config, manifests, records). Refuses failed reads."""
    if (run_dir / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (run_dir / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if _sha256(run_dir / relative) != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    success = json.loads((run_dir / "SUCCESS.json").read_text(encoding="utf-8"))
    config = yaml.safe_load(config_path.read_text("utf-8"))
    legs = sorted((run_dir / "t6" / "typhoon").glob("**/manifest.json"))
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
    return success, config, manifests, records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory of P-ZOOM-2")
    parser.add_argument("--controls-run-dir", type=Path, default=None,
                        help="fetched artifacts/<run_id> directory of P-ZOOM-3 (repeat, bands100)")
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="Typhoon's T1 records.jsonl: the zoom-free whole-page baseline")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    cfg2 = args.root / "configs/thai_marks/p_zoom2.yaml"
    pages_cfg = yaml.safe_load(cfg2.read_text("utf-8"))["pages"]
    pages_path = args.root / pages_cfg["file"]
    if _sha256(pages_path) != pages_cfg["sha256"]:
        raise SystemExit("page list does not match the hash in p_zoom2.yaml")
    pages = json.loads(pages_path.read_text(encoding="utf-8"))["pages"]

    runs = [("p_zoom2", args.run_dir, cfg2)]
    if args.controls_run_dir:
        runs.append(("p_zoom3", args.controls_run_dir, args.root / "configs/thai_marks/p_zoom3.yaml"))
    loaded = {name: load_run(d, c, pages) for name, d, c in runs}
    for name, (_, config, _, _) in loaded.items():
        if config["pages"]["sha256"] != pages_cfg["sha256"]:
            raise SystemExit(f"{name} was registered on a different page list")

    t1 = {(r["id"], r["prompt_kind"]): r for r in _jsonl(args.t1_records)
          if r["task"] == "Full-page OCR"}
    page_ids = [p["id"] for p in pages]
    baseline = [score_page(t1[(p["id"], "TYPHOON_CARD")]["reference"],
                           [t1[(p["id"], "TYPHOON_CARD")]["raw_output"]],
                           p["absent_lines"], p["control_lines"]) for p in pages]

    SENSITIVITY_CUTOFFS = (0.15, 0.25, 0.30)  # registered cutoff is attribution.READ_ELSEWHERE_CER

    scores: dict[str, list[dict]] = {}
    outputs: dict[str, dict[str, str]] = {}
    reads = {}
    zoom = {}
    for name, (_, config, _, records) in loaded.items():
        assembled = pz2.assemble_views(records, pages, config["views"])
        for view, page_list in assembled.items():
            scores[view] = pz2.score_view(page_list)
            outputs[view] = {p["id"]: "\n".join(p["tile_outputs"]) for p in page_list}
        for r in records:
            c = reads.setdefault(r["view"], collections.Counter())
            c["reads"] += 1
            c["generated_tokens"] += r["generated_tokens"]
            c["visual_tokens"] += r["visual_tokens"]
            c["reached_max_new_tokens"] += bool(r["reached_max_new_tokens"])
            c["seconds_generate"] += r["seconds_generate"]
        for view in {r["view"] for r in records}:
            zs = [r["zoom_factor"] for r in records if r["view"] == view]
            zoom[view] = [min(zs), max(zs)]

    registered_views = {v["name"] for v in loaded["p_zoom2"][1]["views"]}
    result = pz2.analyze(baseline, {v: s for v, s in scores.items() if v in registered_views})
    out = {
        "runs": {n: {"run": s["run_id"], "git_sha": s["git_sha"], "gpus": s["gpus"],
                     "manifests": m} for n, (s, _, m, _) in loaded.items()},
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "gpu_hours": {n: sum(x["wall_seconds"] for x in m) / 3600 for n, (_, _, m, _) in loaded.items()},
        "reads": {v: dict(c) for v, c in reads.items()}, "zoom_factor": zoom,
        "pages": page_ids, "p_zoom2_as_registered": result,
    }
    if args.controls_run_dir:
        baseline_outputs = {p["id"]: t1[(p["id"], "TYPHOON_CARD")]["raw_output"] for p in pages}
        identical = pz2.identical_pages(
            {i: o for i, o in outputs["repeat"].items()}, baseline_outputs)
        out["p_zoom3_controlled"] = pz2.analyze_controlled(baseline, scores, identical)
        # Sensitivity to the inherited line-match cutoff (P-ZOOM's registered reading flipped at
        # 0.25). Reported, never used for the label, which is the registered cutoff's.
        registered_cutoff = attribution.READ_ELSEWHERE_CER
        assembled_all = {}
        for name, (_, config, _, records) in loaded.items():
            assembled_all.update(pz2.assemble_views(records, pages, config["views"]))
        out["p_zoom3_sensitivity"] = {}
        try:
            for cutoff in SENSITIVITY_CUTOFFS:
                attribution.READ_ELSEWHERE_CER = cutoff
                base_c = [score_page(t1[(p["id"], "TYPHOON_CARD")]["reference"],
                                     [t1[(p["id"], "TYPHOON_CARD")]["raw_output"]],
                                     p["absent_lines"], p["control_lines"]) for p in pages]
                sc = {v: pz2.score_view(pl) for v, pl in assembled_all.items()}
                c = pz2.analyze_controlled(base_c, sc, identical)
                out["p_zoom3_sensitivity"][str(cutoff)] = {
                    "baseline_absent_text_share": c["baseline_absent_text_share"],
                    "zoom_effect_D": c["zoom_effect_D"], "zoom_effect_ci95": c["zoom_effect_ci95"],
                    "crop_control_text_share": c["crop_control_text_share"],
                    "controlled_reading": c["controlled_reading"],
                    "absent_text_share": {v: b["absent_text_share"] for v, b in c["per_view"].items()}}
        finally:
            attribution.READ_ELSEWHERE_CER = registered_cutoff
    out["page_scores"] = {name: [{"id": i, **s} for i, s in zip(page_ids, per_page)]
                          for name, per_page in scores.items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({"gpu_hours": out["gpu_hours"], "registered_reading": result["reading"],
                      "N": result["perturbation_gain_N"], "Z": result["zoom_gain_Z"],
                      "Z_minus_N_ci95": result["Z_minus_N_ci95"],
                      "union": result["union_absent_text_share"]}, indent=1))
    for name, block in result["per_view"].items():
        print(f"{name:8s} absent text {block['absent_text_share']:.1%}  gain {block['gain_over_baseline']:.1%}"
              f"  loss {block['loss_vs_baseline']:.1%}  control text {block['control_text_share']:.1%}"
              f"  reads {reads[name]['reads']} looped {reads[name]['reached_max_new_tokens']}")
    if "p_zoom3_controlled" in out:
        c = out["p_zoom3_controlled"]
        print("controlled:", c["controlled_reading"], "D", round(c["zoom_effect_D"], 3), c["zoom_effect_ci95"],
              "| stack", c["stack"], c["repeat_identical_pages"])
        for name, v in c["per_view"].items():
            print(f"  {name:8s} text {v['absent_text_share']:.1%} net {v['net_vs_baseline']:+.1%}"
                  f" {v['net_vs_baseline_ci95']} churn {v['churn_vs_baseline']:.1%}"
                  f" control {v['control_text_share']:.1%}")


if __name__ == "__main__":
    main()
