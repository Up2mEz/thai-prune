"""MODEL_SURVEY W4: the registered analysis of the locked-split runs (offline, CPU only).

Reads one or more fetched W4 runs (checksums verified; `split.json` must say `locked`), scores every
record as `docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` §5 registers, and runs §7's
tests (S1, S2, R1 under one Holm family) and the H-rank report. Writes one JSON file with no reference
text and no output text, and refuses to overwrite it.

Usage: --run RUN_DIR:CONFIG (once per phase), e.g.
  --run runs/kaggle/<w4a>/fetched/artifacts/<w4a>:configs/model_survey/w4a.yaml

`--allow-calibration` accepts a run whose `split.json` says `calibration` (an engineering smoke) so the
plumbing can be tested without opening a locked score; its output is marked `PLUMBING_ONLY`.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from labbs2026.model_survey import w4
from labbs2026.model_survey.analysis import load_role, paired_f1_difference
from labbs2026.model_survey.m5 import is_wrapped
from labbs2026.thai_marks.analysis import analyze_t1_v2
from labbs2026.thai_marks.attribution import attribute_marks
from labbs2026.thai_marks.extract import extract
from labbs2026.thai_marks.loop_cut import variant_b
from labbs2026.thai_marks.order_free import mark_counts, prf

ATTRIBUTION_TASK = "Full-page OCR"
TYPHOON = "typhoon"
CALIBRATION_ARCHIVES = {  # role -> (archive, key inside it); calibration loop shares for S1 eligibility
    "typhoon": ("T1_OUTPUTS_a44199c29759", "typhoon"), "base": ("T1_OUTPUTS_a44199c29759", "base"),
    "qwen3vl4b": ("M1_OUTPUTS_3431d9f9dccf", "qwen3vl4b"), "paddle": ("M1_OUTPUTS_3431d9f9dccf", "paddle"),
    "wayu": ("M1_OUTPUTS_3431d9f9dccf", "wayu"), "pathumma": ("M5_OUTPUTS_8252b99e735d", "pathumma"),
    "sealion": ("M6A_OUTPUTS_3ee076494466", "sealion"), "deepseek": ("M6B_OUTPUTS_afe5126bedd7", "deepseek"),
}
TAG = re.compile(r"</?[A-Za-z][^>]*>")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _verify(run: Path) -> None:
    for line in (run / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((run / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {run.name}/{relative}")


def _score(job: tuple) -> tuple:
    role, prompt, record, order_free, attribute = job
    cut = variant_b(record)
    ref = record["reference"]
    out = {"v2": mark_counts(ref, record["raw_output"], **order_free),
           "v2_stop": mark_counts(ref, cut, **order_free),
           "ra": mark_counts(ref, record["raw_output"], **order_free, repeat_aware=True),
           "ra_stop": mark_counts(ref, cut, **order_free, repeat_aware=True)}
    if attribute and record["task"] == ATTRIBUTION_TASK:
        out["attr_stop"] = attribute_marks(ref, cut, approximate_reorder=True)
        out["attr_raw"] = attribute_marks(ref, record["raw_output"], approximate_reorder=True)
    return role, prompt, record["task"], record["id"], out


def _calibration_loop_share(role: str, task: str, prompt: str, data: Path) -> dict:
    name, key = CALIBRATION_ARCHIVES[role]
    archive = json.loads(gzip.open(data / f"{name}.json.gz", "rt", encoding="utf-8").read())
    rows = [r for r in archive["records"][key] if r["task"] == task and r["prompt_kind"] == prompt]
    return {"items": len(rows), "share": w4.loop_share(rows), "archive": name}


def _audit(rows: list[dict]) -> dict:
    structure = [extract(r["raw_output"])[1] for r in rows]
    unclosed = sorted(r["id"] for r, s in zip(rows, structure) if s["unclosed_figures"])
    return {"n": len(rows), "with_markup": sum(bool(TAG.search(r["raw_output"])) for r in rows),
            "json_wrapped": sorted(r["id"] for r in rows if is_wrapped(r["raw_output"])),
            "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in rows),
            "with_figure": sum(1 for s in structure if s["figures"]),
            "unclosed_figure": unclosed,
            "unclosed_figure_ended": sorted(r["id"] for r in rows
                                            if r["id"] in unclosed and not r["reached_max_new_tokens"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, metavar="RUN_DIR:CONFIG")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("docs/stage0/data"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--allow-calibration", action="store_true")
    parser.add_argument("--skip-t1-scoring", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    models: dict[str, dict] = {}
    records: dict[tuple, list[dict]] = {}
    runs, run_on_seen = [], set()
    for spec in args.run:
        run_dir, config_path = spec.rsplit(":", 1)
        run, cfg = Path(run_dir), Path(config_path)
        config = yaml.safe_load(cfg.read_text("utf-8"))
        _verify(run)
        runs.append({"run": run.name, "config": cfg.as_posix(),
                     "config_sha256": hashlib.sha256(cfg.read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
        order_free = config["scoring"]["order_free"]
        bootstrap = config["scoring"]["bootstrap"]
        for role, model in config["models"].items():
            for split_file in (run / "m1" / role).rglob("split.json"):
                run_on_seen.add(json.loads(split_file.read_text("utf-8"))["run_on"])
            rows, _ = load_role(run, role, model["prompts"])
            models[role] = model
            for r in rows:
                records.setdefault((role, r["prompt_kind"]), []).append(r)
    plumbing = run_on_seen != {"locked"}
    if plumbing and not (args.allow_calibration and run_on_seen == {"calibration"}):
        raise SystemExit(f"runs are not locked-split runs (run_on {sorted(run_on_seen)})")
    assert bootstrap["resamples"] == w4.RESAMPLES and bootstrap["seed"] == w4.SEED, "bootstrap differs from §6"

    page_hash: dict[str, str] = {}
    reference: dict[str, str] = {}
    for rows in records.values():
        for r in rows:
            if page_hash.setdefault(r["id"], r["image_sha256"]) != r["image_sha256"]:
                raise SystemExit(f"{r['id']}: two image hashes")
            if reference.setdefault(r["id"], r["reference"]) != r["reference"]:
                raise SystemExit(f"{r['id']}: two references")

    jobs = [(role, prompt, r, order_free, prompt == models[role]["primary_prompt"])
            for (role, prompt), rows in records.items() for r in rows]
    with ProcessPoolExecutor(args.workers) as pool:
        scored = list(pool.map(_score, jobs, chunksize=4))
    table: dict = {}
    for role, prompt, task, item, out in scored:
        table.setdefault((role, prompt), {}).setdefault(task, {})[item] = out
    tasks = sorted({r["task"] for rows in records.values() for r in rows})

    result: dict = {
        "kind": "PLUMBING_ONLY (calibration smoke)" if plumbing else
                "W4 confirmatory analysis (registration §5-§7); phases read: " + ", ".join(sorted(models)),
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "git_sha": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "runs": runs, "models": sorted(models), "order_free": order_free, "bootstrap": bootstrap,
        "items": len(page_hash), "distinct_pages": len(set(page_hash.values())),
        "contamination_note": "Typhoon is from ThaiOCRBench's group; Pathumma's 377K training samples are unnamed.",
        "cells": {}, "audit": {}, "h_rank": {}, "s1": {}, "r1": {}, "t1_scoring_v2": {},
        "upper_bound_unclosed_figure": {},
    }

    # ---- per-cell scores (§5) and markup audit
    for (role, prompt), per_task in sorted(table.items()):
        for task, per_item in sorted(per_task.items()):
            ids = sorted(per_item)
            recs = {r["id"]: r for r in records[(role, prompt)] if r["task"] == task}
            result["cells"][f"{role} / {prompt} / {task}"] = {
                "n": len(ids), "primary": prompt == models[role]["primary_prompt"],
                **{k: prf([per_item[i][k] for i in ids]) for k in ("v2", "v2_stop", "ra", "ra_stop")},
                "looping": sum(bool(recs[i]["reached_max_new_tokens"]) for i in ids)}
            result["audit"][f"{role} / {prompt} / {task}"] = _audit(list(recs.values()))
            if not args.skip_t1_scoring:
                result["t1_scoring_v2"][f"{role} / {prompt} / {task}"] = analyze_t1_v2(
                    list(recs.values()), seed=config["scoring"]["null_seed"])

    # ---- S1: stop - greedy per model and task (primary prompt), eligibility from calibration
    p_family: dict[str, float | None] = {}
    for role, model in sorted(models.items()):
        primary = model["primary_prompt"]
        for task in tasks:
            per_item = table.get((role, primary), {}).get(task)
            if not per_item:
                continue
            cal = _calibration_loop_share(role, task, primary, args.data)
            eligible = cal["share"] is not None and cal["share"] >= w4.LOOP_SHARE_MIN
            greedy = {i: c["v2"] for i, c in per_item.items()}
            stopped = {i: c["v2_stop"] for i, c in per_item.items()}
            ra = w4.s1_difference({i: c["ra"] for i, c in per_item.items()},
                                  {i: c["ra_stop"] for i, c in per_item.items()}, page_hash)
            entry = {"prompt": primary, "calibration_loop_share": cal, "eligible": eligible,
                     "v2": w4.s1_difference(greedy, stopped, page_hash), "repeat_aware_descriptive": ra}
            result["s1"][f"{role} / {task}"] = entry
            if eligible:
                p_family[f"S1 {role} / {task}"] = entry["v2"]["p_one_sided"]
        # Pathumma's secondary prompt, descriptive only
        for prompt in model["prompts"]:
            if prompt != primary:
                for task in tasks:
                    per_item = table.get((role, prompt), {}).get(task)
                    if per_item:
                        result["s1"][f"{role} ({prompt}, descriptive) / {task}"] = w4.s1_difference(
                            {i: c["v2"] for i, c in per_item.items()},
                            {i: c["v2_stop"] for i, c in per_item.items()}, page_hash)

    # ---- S2: ended outputs the stop changes, pooled over models (primary prompts, both tasks)
    per_model: dict[str, dict[str, list[str]]] = {}
    for role, model in sorted(models.items()):
        recs = {r["id"]: r for r in records[(role, model["primary_prompt"])]}
        eff = w4.stop_effects(recs, {k: variant_b(r) for k, r in recs.items()})
        per_model[role] = eff
    s2 = w4.s2_pooled(per_model, page_hash)
    s2["per_model"] = {m: {"ended": len(v["ended"]), "changed": len(v["changed"]),
                           "no_repeat_share_of_ended": (1 - len(v["changed"]) / len(v["ended"]))
                           if v["ended"] else None} for m, v in per_model.items()}
    result["s2"] = s2
    p_family["S2 pooled"] = s2["p_one_sided_above_threshold"]

    # ---- R1: Full-page, stopped outputs, per model (primary prompt)
    for role, model in sorted(models.items()):
        per_item = table.get((role, model["primary_prompt"]), {}).get(ATTRIBUTION_TASK)
        if not per_item:
            continue
        attr = {i: c["attr_stop"] for i, c in per_item.items()}
        entry = w4.r1_test(attr, page_hash)
        entry["attribution_stopped"] = dict(sum(attr.values(), collections.Counter()))
        entry["attribution_raw"] = dict(sum((c["attr_raw"] for c in per_item.values()), collections.Counter()))
        result["r1"][role] = entry
        p_family[f"R1 {role}"] = entry["p_one_sided"]

    result["holm"] = w4.holm(p_family)
    result["holm_note"] = ("one family: the S1 tests of eligible cells, S2 and one R1 per model; "
                           "p-values are one-sided bootstrap p against each test's threshold")

    # ---- H-rank (reported, not tested): paired difference to Typhoon, per task
    typhoon = {t: {i: c for i, c in per.items()} for (r, p), per_task in table.items()
               if r == TYPHOON and p == models[TYPHOON]["primary_prompt"] for t, per in per_task.items()} \
        if TYPHOON in models else {}
    for (role, prompt), per_task in sorted(table.items()):
        if role == TYPHOON and prompt == models[TYPHOON]["primary_prompt"]:
            continue
        for task, per_item in sorted(per_task.items()):
            if task not in typhoon:
                continue
            ids = sorted(per_item)
            entry = {}
            for score in ("v2", "ra"):
                a = {i: per_item[i][score] for i in ids}
                b = {i: typhoon[task][i][score] for i in ids}
                entry[score] = {key: paired_f1_difference(a, b, resamples=w4.RESAMPLES, seed=w4.SEED, key=key)
                                for key in ("f1", "recall", "precision")}
            result["h_rank"][f"typhoon - {role} ({prompt}) / {task}"] = entry
    # §5's upper bound, beside v2 (as M5's diagnostic): ended outputs with an unclosed <figure> credited
    # with a perfect read, then the same paired difference to Typhoon
    for (role, prompt), per_task in sorted(table.items()):
        if (role == TYPHOON and prompt == models[TYPHOON]["primary_prompt"]) or TYPHOON not in models:
            continue
        for task, per_item in sorted(per_task.items()):
            dropped = result["audit"][f"{role} / {prompt} / {task}"]["unclosed_figure_ended"]
            if not dropped or task not in typhoon:
                continue
            bound = {i: ({**c["v2"], "correct": c["v2"]["reference_marks"],
                          "output_marks": c["v2"]["reference_marks"]} if i in dropped else c["v2"])
                     for i, c in per_item.items()}
            ids = sorted(per_item)
            result["upper_bound_unclosed_figure"][f"typhoon - {role} ({prompt}) / {task}"] = {
                "items": len(dropped), "reference_marks": sum(per_item[i]["v2"]["reference_marks"] for i in dropped),
                "model_f1_as_scored": prf([per_item[i]["v2"] for i in ids])["f1"],
                "model_f1_upper_bound": prf([bound[i] for i in ids])["f1"],
                "typhoon_minus_model_upper_bound": paired_f1_difference(
                    bound, {i: typhoon[task][i]["v2"] for i in ids}, resamples=w4.RESAMPLES, seed=w4.SEED)}
    lower = [e["v2"]["f1"]["ci95"][0] for k, e in result["h_rank"].items() if e["v2"]["f1"]["ci95"]]
    result["h_rank_best_rule"] = ("Typhoon's lower bound is above 0 against every model read, on both tasks"
                                  if lower and all(x > 0 for x in lower) else
                                  "not met: 'best' is not used")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)
    print(result["kind"])
    for name, c in result["cells"].items():
        print(f"{name}: n={c['n']} v2 F1 {c['v2']['f1']:.3f} stop {c['v2_stop']['f1']:.3f} "
              f"ra {c['ra']['f1']:.3f} loops {c['looping']}")
    print("S2:", {k: s2[k] for k in ("ended", "changed", "share", "upper95_binomial_one_sided",
                                     "passes_as_written")})
    for k, v in result["holm"].items():
        print("Holm", k, v)


if __name__ == "__main__":
    main()
