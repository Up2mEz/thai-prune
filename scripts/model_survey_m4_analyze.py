"""Fetch a MODEL_SURVEY_M4 run, verify it, and write the registered readings (CPU only).

Inputs: the run's teacher-forced scores (per token, per item), M3's archived
`E` outputs, and T1's archived base and Typhoon outputs. Steps:

1. the scoring-path check (argmax agreement on ordinary outputs);
2. windows and their scores;
3. the filter threshold, fixed from ordinary text;
4. Full-page labels and the AUROC of each score;
5. the filtered arm `E_F`, scored like M3's arms.

Writes one JSON file with no reference text, and refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.kaggle import kernel_id
from labbs2026.model_survey.analysis import comparison_records, paired_f1_difference, references_by_id, score_role
from labbs2026.model_survey.exploratory import compare
from labbs2026.model_survey.m3 import stop_only
from labbs2026.model_survey.m4 import (
    filtered_output,
    item_bootstrap_auroc,
    label,
    quantile,
    validate,
    window_scores,
    windows,
)

CONFIG = Path("configs/model_survey/m4.yaml")
KERNEL_SLUG = "labbs2026-model-survey-m4"
PAIRS = (("E0", "E_F"), ("E", "E_F"), ("E0", "E"), ("typhoon", "E_F"))


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _score(job: tuple[str, list[dict], dict]) -> tuple[str, dict]:
    name, records, scoring = job
    return name, score_role(records, null_seed=int(scoring["null_seed"]), **scoring["order_free"])


def _load_shards(root: Path, shards: int) -> tuple[dict[str, dict], list[dict]]:
    records: dict[str, dict] = {}
    manifests = []
    for k in range(shards):
        leg = root / "m4" / f"shard-{k}-of-{shards}"
        if not (leg / "manifest.json").is_file():
            raise SystemExit(f"{leg}: no manifest.json (shard did not finish)")
        manifests.append(json.loads((leg / "manifest.json").read_text("utf-8")))
        for line in (leg / "records.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["id"] in records:
                    raise SystemExit(f"{r['id']} scored twice")
                records[r["id"]] = r
    return records, manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    validate(config)
    a = config["analysis"]
    width, max_cer, label_task = int(a["window_min_chars"]), float(a["label_max_cer"]), a["label_task"]

    if not args.skip_fetch:
        args.destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", kernel_id(Path("."), KERNEL_SLUG),
                        "-p", str(args.destination)], check=True, capture_output=True)
    root = next(args.destination.rglob(args.run_id), None)
    if root is None or not root.is_dir():
        raise SystemExit(f"run directory {args.run_id} not found under {args.destination}")
    if (root / "FAILURE.json").is_file() or (root / "PARTIAL.json").is_file():
        raise SystemExit("the scoring run did not finish cleanly")
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    scored, manifests = _load_shards(root, int(config["shards"]))
    archive_path = Path(config["scoring_pass"]["outputs_archive"])
    archive = json.loads(gzip.open(archive_path, "rt", encoding="utf-8").read())
    outputs = {r["id"]: r for r in archive["records"][config["scoring_pass"]["outputs_arm"]]}
    missing = sorted(set(outputs) - set(scored))
    result: dict = {"run_id": args.run_id, "claim_level": config["claim_level"], "git_sha": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
                    "analysis": a, "manifests": manifests, "not_scored": missing,
                    "outputs_archive": {"path": str(archive_path), "run_id": archive["provenance"]["run_id"],
                                        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}}

    # E's records with this run's reference and category, so they score like M3's arms
    E = []
    for i, out in sorted(outputs.items()):
        if i in scored:
            E.append({**out, "reference": scored[i]["reference"], "category": scored[i]["category"]})
    escaped = {r["id"] for r in E if r["escapes"] or r["final_cut"]}
    ordinary = {r["id"] for r in E if r["id"] not in escaped and not r["reached_max_new_tokens"]}

    # 1. scoring-path check
    agree = [x for i in ordinary for x in scored[i]["agrees"]]
    result["check"] = {"ordinary_items": len(ordinary), "ordinary_tokens": len(agree),
                       "argmax_agreement": sum(agree) / len(agree) if agree else None,
                       "roundtrip_items": sum(bool(scored[r["id"]]["roundtrip"]) for r in E), "items": len(E),
                       "passes_floor": bool(agree) and sum(agree) / len(agree) >= float(a["agreement_floor"])}

    # 2-3. windows, scores, threshold
    def scored_windows(r: dict, start: int, end: int) -> list[dict]:
        s = scored[r["id"]]
        spans = windows(r["raw_output"], start, end, width)
        return window_scores(spans, s["offsets"], s["logprob"], s["entropy"])

    ordinary_windows = [w for r in E if r["id"] in ordinary
                        for w in scored_windows(r, 0, len(r["raw_output"])) if w["s_mean"] is not None]
    tau = quantile([w["s_mean"] for w in ordinary_windows], float(a["threshold_quantile"]))
    result["threshold"] = {"tau": tau, "ordinary_windows": len(ordinary_windows),
                           "quantile": float(a["threshold_quantile"])}

    # 4. labels (label task only), AUROC per score, the filter's keep rates
    items, auroc_rows = [], {"s_mean": {}, "s_min": {}, "s_ent": {}}
    filtered: dict[str, dict] = {}
    for r in E:
        if r["id"] not in escaped:
            continue
        p = r["greedy_prefix_chars"]
        post = scored_windows(r, p, len(r["raw_output"]))
        prefix = scored_windows(r, 0, p)
        detail = {"id": r["id"], "task": r["task"], "post_windows": len(post), "prefix_windows": len(prefix),
                  "post_kept": sum(w["s_mean"] is not None and w["s_mean"] >= tau for w in post)}
        if r["task"] == label_task:
            counts = {"read": [0, 0], "invented": [0, 0], "no_letter": [0, 0]}   # [windows, kept]
            for w in post:
                kind, _ = label(r["raw_output"][w["start"]:w["end"]], r["reference"], max_cer)
                kept = w["s_mean"] is not None and w["s_mean"] >= tau
                counts[kind][0] += 1
                counts[kind][1] += kept
                if kind != "no_letter" and w["s_mean"] is not None:
                    for key in auroc_rows:
                        value = -w[key] if key == "s_ent" else w[key]        # higher = more confident
                        auroc_rows[key].setdefault(r["id"], []).append((value, kind == "read"))
            prefix_read = sum(label(r["raw_output"][w["start"]:w["end"]], r["reference"], max_cer)[0] == "read"
                              for w in prefix)
            detail.update({"post": {k: {"windows": v[0], "kept": v[1]} for k, v in counts.items()},
                           "prefix_read": prefix_read,
                           "post_s_mean": [round(w["s_mean"], 4) for w in post if w["s_mean"] is not None],
                           "prefix_s_mean": [round(w["s_mean"], 4) for w in prefix if w["s_mean"] is not None]})
        items.append(detail)
        filtered[r["id"]] = {**r, "raw_output": filtered_output(r["raw_output"], p, post, tau)}
    boot = {"resamples": int(config["scoring"]["bootstrap"]["resamples"]),
            "seed": int(config["scoring"]["bootstrap"]["seed"])}
    result["auroc"] = {key: item_bootstrap_auroc(rows, **boot) for key, rows in auroc_rows.items()}
    result["escaped_items"] = items
    totals = {k: [0, 0] for k in ("read", "invented", "no_letter")}
    for d in items:
        for k, v in d.get("post", {}).items():
            totals[k][0] += v["windows"]
            totals[k][1] += v["kept"]
    result["keep_rates"] = {k: {"windows": v[0], "kept": v[1], "rate": v[1] / v[0] if v[0] else None}
                            for k, v in totals.items()}

    # 5. arms and their scores
    arms = {"E": E, "E0": [stop_only(r) for r in E], "E_F": [filtered.get(r["id"], r) for r in E]}
    comparison = config["comparison"]
    old = comparison_records(Path(comparison["outputs"]), ["typhoon"], comparison["prompt"], references_by_id(E))
    everything = {**arms, **old}
    with ProcessPoolExecutor(args.workers) as pool:
        scores = dict(pool.map(_score, [(n, rows, config["scoring"]) for n, rows in everything.items()]))
    result["arms"] = {n: {k: v for k, v in scores[n].items() if not k.startswith("_")} for n in everything}

    def counts(name: str, task: str) -> dict[str, dict]:
        return {i: c for (t, _, i), c in scores[name]["_counts"].items() if t == task}

    result["pairs"], result["pairs_escaped"] = {}, {}
    for task in config["benchmark"]["tasks"]:
        task_escaped = sorted(r["id"] for r in E if r["id"] in escaped and r["task"] == task)
        for x, y in PAIRS:
            cx, cy = counts(x, task), counts(y, task)
            for key, ids in (("pairs", sorted(set(cx) & set(cy))), ("pairs_escaped", task_escaped)):
                if not ids:
                    continue
                pair = compare(cx, cy, ids, **boot)
                pair["difference"]["matched_lines"] = paired_f1_difference(
                    {i: cx[i] for i in ids}, {i: cy[i] for i in ids}, key="matched_lines", **boot)
                result[key][f"{y} - {x} / {task}"] = pair

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
