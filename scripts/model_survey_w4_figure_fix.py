"""MODEL_SURVEY W4, phase A: Typhoon versus Pathumma with the unclosed `<figure>` read as page text.

Extraction v2 follows the `TYPHOON_CARD` output contract: the content of a `<figure>` is a description, so it
is dropped. An unclosed `<figure>` therefore runs to the end of the output (`thai_marks/extract.py`). In nine
Pathumma Full-page outputs the tag is never closed and real page text follows it, so the registered score
(`W4_ANALYSIS_0743f13.json`) loses that text. The registered analysis bounded the effect by crediting those
items with a perfect read (`upper_bound_unclosed_figure`). This script instead rescores them with the opening
tag of an unclosed figure removed, so the text after it is kept (the figure's own description is kept too, and
adds surplus marks), and repeats the paired Typhoon - Pathumma comparison.

Post hoc and descriptive: it reads the locked outputs a second time, changes only this extraction rule, and
does not replace any registered result. The same rule is applied to Typhoon (it changes none of its outputs).
Offline, CPU only. Refuses to overwrite its output.

Usage:
  uv run python scripts/model_survey_w4_figure_fix.py \\
      --run runs/kaggle/kaggle-model-survey-w4a-37b0d59989de/fetched/artifacts/kaggle-model-survey-w4a-37b0d59989de \\
      --config configs/model_survey/w4a.yaml --out docs/stage0/data/W4_FIGURE_FIX.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.model_survey import w4
from labbs2026.model_survey.analysis import load_role, paired_f1_difference
from labbs2026.thai_marks.extract import extract
from labbs2026.thai_marks.order_free import mark_counts, prf

FIGURE_OPEN = re.compile(r"<figure\b[^>]*>", re.I)
RULES = ("as_registered", "figure_text_kept")


def fix_unclosed_figure(text: str) -> str:
    """Drop the opening tag of a `<figure>` that is never closed, so that the text after it is kept."""
    if extract(text)[1]["unclosed_figures"] and "</figure" not in text.lower():
        return FIGURE_OPEN.sub(" ", text)
    return text


def _score(job: tuple) -> tuple:
    role, prompt, record, order_free = job
    ref = record["reference"]
    out = {}
    for rule, hyp in (("as_registered", record["raw_output"]),
                      ("figure_text_kept", fix_unclosed_figure(record["raw_output"]))):
        out[rule] = {"v2": mark_counts(ref, hyp, **order_free),
                     "ra": mark_counts(ref, hyp, **order_free, repeat_aware=True)}
    out["changed"] = fix_unclosed_figure(record["raw_output"]) != record["raw_output"]
    return role, prompt, record["task"], record["id"], out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True, help="the fetched phase-A run (has the references)")
    parser.add_argument("--config", type=Path, default=Path("configs/model_survey/w4a.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    config = yaml.safe_load(args.config.read_text("utf-8"))
    order_free, bootstrap = config["scoring"]["order_free"], config["scoring"]["bootstrap"]
    assert bootstrap["resamples"] == w4.RESAMPLES and bootstrap["seed"] == w4.SEED
    jobs = []
    for role in ("typhoon", "pathumma"):
        rows, _ = load_role(args.run, role, config["models"][role]["prompts"])
        jobs += [(role, r["prompt_kind"], r, order_free) for r in rows]
    with ProcessPoolExecutor(args.workers) as pool:
        scored = list(pool.map(_score, jobs, chunksize=4))
    table: dict = {}
    changed: dict = {}
    for role, prompt, task, item, out in scored:
        table.setdefault((role, prompt, task), {})[item] = out
        if out["changed"]:
            changed.setdefault((role, prompt, task), []).append(item)

    typhoon_prompt = config["models"]["typhoon"]["primary_prompt"]
    result: dict = {
        "kind": "W4 phase A, post hoc sensitivity: unclosed <figure> read as page text (descriptive)",
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "config_sha256": hashlib.sha256(args.config.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "rule": "opening tag of a <figure> that is never closed is removed; text after it (and the figure's own "
                "description) is kept; applied to Typhoon and Pathumma alike",
        "bootstrap": bootstrap, "cells": {}, "typhoon_minus_pathumma": {},
    }
    for (role, prompt, task), per_item in sorted(table.items()):
        ids = sorted(per_item)
        result["cells"][f"{role} / {prompt} / {task}"] = {
            "n": len(ids), "items_changed_by_rule": sorted(changed.get((role, prompt, task), [])),
            **{rule: {score: prf([per_item[i][rule][score] for i in ids]) for score in ("v2", "ra")}
               for rule in RULES}}
    for (role, prompt, task), per_item in sorted(table.items()):
        if role != "pathumma":
            continue
        typhoon = table[("typhoon", typhoon_prompt, task)]
        entry = {}
        for rule in RULES:
            entry[rule] = {score: {key: paired_f1_difference(
                {i: per_item[i][rule][score] for i in per_item}, {i: typhoon[i][rule][score] for i in per_item},
                resamples=w4.RESAMPLES, seed=w4.SEED, key=key) for key in ("f1", "recall", "precision")}
                for score in ("v2", "ra")}
        result["typhoon_minus_pathumma"][f"{prompt} / {task}"] = entry
        print(f"{prompt} / {task}:", {rule: {k: round(entry[rule]['v2'][k]['difference'], 4)
                                              for k in ('f1', 'recall', 'precision')} for rule in RULES})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
