"""MODEL_SURVEY, calibration split: Pathumma's scores with two extraction defects removed.

The locked-split counterpart is `model_survey_w4_stop_arm_fix.py`. Pathumma's outputs have two defects under
extraction v2: an unclosed `<figure>` swallows the page text after it, and answers in Typhoon's JSON format
(`{"natural_text": "..."}`) keep their `\\\\n` escapes as literal characters (`model_survey_w4_figure_fix.rule_text`).
Typhoon has no JSON-wrapped output and two outputs with an unclosed `<figure>` (both under the card prompt, both
that reached the token limit); the rules are applied to both models alike. This script redoes, for Pathumma, every
calibration score the paper reports: mark F1 per task and prompt, the `+ stop` arm, the paired difference to
Typhoon, the tone error after a correctly read consonant, and the Full-page attribution of the stopped output.

References come from the pinned ThaiOCRBench in the local Hugging Face cache (offline); outputs from the archives
`M5_OUTPUTS_8252b99e735d` (Pathumma) and `T1_OUTPUTS_a44199c29759` (Typhoon). The stop is frozen
(`variant_b` on the raw output); only the extraction of the scored text changes. Post hoc and descriptive;
refuses to overwrite its output.

Usage:
  uv run python scripts/model_survey_calibration_extraction_fix.py --out docs/stage0/data/M5_EXTRACTION_FIX.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_survey_w4_figure_fix as ff  # noqa: E402

from labbs2026.model_survey.analysis import paired_f1_difference  # noqa: E402
from labbs2026.model_survey.m5 import is_wrapped  # noqa: E402
from labbs2026.model_survey.w1 import attribution_shares  # noqa: E402
from labbs2026.thai_marks.analysis import analyze_t1_v2  # noqa: E402
from labbs2026.thai_marks.attribution import attribute_marks  # noqa: E402
from labbs2026.thai_marks.extract import extract  # noqa: E402
from labbs2026.thai_marks.loop_cut import variant_b  # noqa: E402
from labbs2026.thai_marks.order_free import mark_counts, prf  # noqa: E402
from labbs2026.thai_marks.split import calibration_ids  # noqa: E402

RULES = ("as_registered", "json_unwrapped_figure_kept")
DATA = Path("docs/stage0/data")


def references() -> dict[str, tuple[str, str]]:
    """id -> (task, answer) for the calibration split of the pinned benchmark, from the local cache."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from datasets import load_dataset

    spec = yaml.safe_load(Path("configs/model_survey/m5.yaml").read_text("utf-8"))
    bench, split = spec["benchmark"], spec["split"]
    dataset = load_dataset(bench["repo"], split=bench["split"], revision=bench["revision"])
    ids, tasks, cats, answers = dataset["Id"], dataset["Task"], dataset["category"], dataset["answer"]
    rows = [i for i, t in enumerate(tasks) if t in set(bench["tasks"])]
    chosen = calibration_ids(((ids[i], tasks[i], cats[i]) for i in rows), seed=int(split["seed"]),
                             fraction=float(split["calibration_fraction"]))
    return {ids[i]: (tasks[i], answers[i]) for i in rows if ids[i] in chosen}


def _score(job: tuple) -> tuple:
    role, record, order_free = job
    ref, cut = record["reference"], variant_b(record)
    rules = RULES  # the same two rules for every model
    out, cache = {}, {}
    for rule in rules:
        row = {}
        for arm, raw in (("greedy", record["raw_output"]), ("stop", cut)):
            hyp = ff.rule_text(rule, raw)
            if hyp not in cache:
                cache[hyp] = {"v2": mark_counts(ref, hyp, **order_free),
                              "ra": mark_counts(ref, hyp, **order_free, repeat_aware=True),
                              "attr": attribute_marks(ref, hyp, approximate_reorder=True)
                              if record["task"] == "Full-page OCR" else None}
            row[arm] = cache[hyp]
        out[rule] = row
    return role, record["prompt_kind"], record["task"], record["id"], out


def _load(name: str, role: str, ref: dict) -> list[dict]:
    payload = json.loads(gzip.open(DATA / f"{name}.json.gz", "rt", encoding="utf-8").read())
    rows = [r for r in payload["records"][role] if r["id"] in ref]
    return [{**r, "reference": ref[r["id"]][1]} for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(Path("configs/model_survey/m5.yaml").read_text("utf-8"))
    order_free, bootstrap = config["scoring"]["order_free"], config["scoring"]["bootstrap"]
    ref = references()
    pathumma = _load("M5_OUTPUTS_8252b99e735d", "pathumma", ref)
    typhoon = _load("T1_OUTPUTS_a44199c29759", "typhoon", ref)
    scan = {"pathumma": {"outputs": len(pathumma), "json_wrapped": sum(is_wrapped(r["raw_output"]) for r in pathumma),
                         "unclosed_figure": sum(bool(extract(r["raw_output"])[1]["unclosed_figures"]) for r in pathumma)},
            "typhoon": {"outputs": len(typhoon), "json_wrapped": sum(is_wrapped(r["raw_output"]) for r in typhoon),
                        "unclosed_figure": sum(bool(extract(r["raw_output"])[1]["unclosed_figures"]) for r in typhoon)}}
    jobs = [("pathumma", r, order_free) for r in pathumma] + [("typhoon", r, order_free) for r in typhoon]
    with ProcessPoolExecutor(args.workers) as pool:
        scored = list(pool.map(_score, jobs, chunksize=2))
    table: dict = {}
    for role, prompt, task, item, out in scored:
        table.setdefault((role, prompt, task), {})[item] = out
    by_id = {(r["prompt_kind"], r["id"]): r for r in pathumma}
    result: dict = {
        "kind": "M5 calibration, post hoc: Pathumma with two extraction defects removed (descriptive)",
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "bootstrap": bootstrap, "defect_scan_calibration": scan, "cells": {}, "typhoon_minus_pathumma": {},
        "t1_tone": {}, "attribution_stopped_fullpage": {},
    }
    for (role, prompt, task), per_item in sorted(table.items()):
        ids = sorted(per_item)
        for rule in RULES:
            result["cells"].setdefault(f"{role} / {prompt} / {task}", {})[rule] = {
                "n": len(ids), **{f"{arm}_{score}": prf([per_item[i][rule][arm][score] for i in ids])
                                  for arm in ("greedy", "stop") for score in ("v2", "ra")}}
            if task == "Full-page OCR":
                counters = [per_item[i][rule]["stop"]["attr"] for i in ids]
                result["attribution_stopped_fullpage"].setdefault(f"{role} / {prompt}", {})[rule] = \
                    attribution_shares(counters)
            if role == "pathumma":
                recs = [{**by_id[(prompt, i)], "raw_output": ff.rule_text(rule, by_id[(prompt, i)]["raw_output"])}
                        for i in ids]
                result["t1_tone"].setdefault(f"{prompt} / {task}", {})[rule] = analyze_t1_v2(
                    recs, seed=config["scoring"]["null_seed"])
    for (role, prompt, task), per_item in sorted(table.items()):
        if role != "pathumma":
            continue
        ty = table[("typhoon", "BENCHMARK_QUESTION", task)]
        result["typhoon_minus_pathumma"][f"{prompt} / {task}"] = {
            rule: {score: {key: paired_f1_difference(
                {i: per_item[i][rule]["greedy"][score] for i in per_item},
                {i: ty[i][rule]["greedy"][score] for i in per_item},
                resamples=bootstrap["resamples"], seed=bootstrap["seed"], key=key)
                for key in ("f1", "recall", "precision")} for score in ("v2", "ra")} for rule in RULES}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for key, cell in result["cells"].items():
        if key.startswith("pathumma"):
            print(key, {rule: (round(c["greedy_v2"]["f1"] * 100, 1), round(c["stop_v2"]["f1"] * 100, 1))
                        for rule, c in cell.items()})
    print("scan", scan)
    print(args.out)


if __name__ == "__main__":
    main()
