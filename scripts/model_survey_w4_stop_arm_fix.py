"""MODEL_SURVEY W4, phase A: Pathumma's `+ stop` arm, S1 and R1 with the two extraction defects removed.

Follows `model_survey_w4_figure_fix.py` (the greedy arm). The stop itself is frozen: `loop_cut.variant_b` cuts the
raw output, as in the registered analysis and in the decode-time check. Only the extraction of the text that
is scored changes (`rule_text`: unwrap Typhoon's JSON format, then keep the text after an unclosed `<figure>`).
Offline, CPU only, post hoc and descriptive: it replaces no registered number, and it refuses to overwrite its
output.

It also scans every output of all eight models for the two defects, to show that only Pathumma has them (so no
other model's score needs to be redone).

Usage:
  uv run python scripts/model_survey_w4_stop_arm_fix.py \\
      --run runs/kaggle/kaggle-model-survey-w4a-37b0d59989de/fetched/artifacts/kaggle-model-survey-w4a-37b0d59989de \\
      --config configs/model_survey/w4a.yaml --out docs/stage0/data/W4_STOP_ARM_FIX.json
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_survey_w4_figure_fix as ff  # noqa: E402

from labbs2026.model_survey import w4  # noqa: E402
from labbs2026.model_survey.analysis import load_role  # noqa: E402
from labbs2026.model_survey.m5 import is_wrapped  # noqa: E402
from labbs2026.thai_marks.attribution import attribute_marks  # noqa: E402
from labbs2026.thai_marks.extract import extract  # noqa: E402
from labbs2026.thai_marks.loop_cut import variant_b  # noqa: E402
from labbs2026.thai_marks.order_free import mark_counts  # noqa: E402

RULES = ("as_registered", "v2_1")
ARCHIVES = ["W4A_OUTPUTS_37b0d59989de", "W4B_OUTPUTS_1c57af591e7e", "W4C_OUTPUTS_1c57af591e7e",
            "W4CD_OUTPUTS_1c57af591e7e"]


def _score(job: tuple) -> tuple:
    prompt, record, order_free = job
    ref, cut = record["reference"], variant_b(record)
    out, cache = {}, {}
    for rule in RULES:
        ended = not record["reached_max_new_tokens"]
        arms = {"greedy": ff.rule_text(rule, record["raw_output"], ended), "stop": ff.rule_text(rule, cut, ended)}
        row = {}
        for arm, hyp in arms.items():
            if hyp not in cache:
                cache[hyp] = {"v2": mark_counts(ref, hyp, **order_free),
                              "ra": mark_counts(ref, hyp, **order_free, repeat_aware=True),
                              "attr": attribute_marks(ref, hyp, approximate_reorder=True)}
            row[arm] = cache[hyp]
        out[rule] = row
    return prompt, record["id"], out


def _scan(data: Path) -> dict:
    """Per model: outputs that are JSON-wrapped or have an unclosed <figure>, over all four phase archives."""
    found: dict = collections.defaultdict(lambda: {"outputs": 0, "json_wrapped": 0, "unclosed_figure": 0})
    for name in ARCHIVES:
        payload = json.loads(gzip.open(data / f"{name}.json.gz", "rt", encoding="utf-8").read())
        for role, rows in payload["records"].items():
            for r in rows:
                found[role]["outputs"] += 1
                found[role]["json_wrapped"] += int(is_wrapped(r["raw_output"]))
                found[role]["unclosed_figure"] += int(bool(extract(r["raw_output"])[1]["unclosed_figures"]))
    return dict(found)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/model_survey/w4a.yaml"))
    parser.add_argument("--registered", type=Path, default=Path("docs/stage0/data/W4_ANALYSIS_0743f13.json"))
    parser.add_argument("--data", type=Path, default=Path("docs/stage0/data"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    config = yaml.safe_load(args.config.read_text("utf-8"))
    order_free = config["scoring"]["order_free"]
    registered = json.loads(args.registered.read_text("utf-8"))
    rows, _ = load_role(args.run, "pathumma", config["models"]["pathumma"]["prompts"])
    rows = [r for r in rows if r["task"] == "Full-page OCR"]
    page_hash = {r["id"]: r["image_sha256"] for r in rows}
    with ProcessPoolExecutor(args.workers) as pool:
        scored = list(pool.map(_score, [(r["prompt_kind"], r, order_free) for r in rows], chunksize=2))
    table: dict = {}
    for prompt, item, out in scored:
        table.setdefault(prompt, {})[item] = out

    primary = config["models"]["pathumma"]["primary_prompt"]
    result: dict = {
        "kind": "W4 phase A, post hoc: Pathumma's + stop arm, S1 and R1 with two extraction defects removed",
        "claim_level": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE",
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "stop": "loop_cut.variant_b on the raw output (frozen); only the extraction of the scored text changes",
        "rules": list(RULES), "defect_scan_all_models": _scan(args.data), "s1": {}, "r1": {}, "holm": {},
    }
    for prompt, per_item in sorted(table.items()):
        for rule in RULES:
            greedy = {i: c[rule]["greedy"]["v2"] for i, c in per_item.items()}
            stopped = {i: c[rule]["stop"]["v2"] for i, c in per_item.items()}
            ra = w4.s1_difference({i: c[rule]["greedy"]["ra"] for i, c in per_item.items()},
                                  {i: c[rule]["stop"]["ra"] for i, c in per_item.items()}, page_hash)
            result["s1"][f"{prompt} / {rule}"] = {
                "greedy_f1": w4.micro_f1(greedy, sorted(greedy)), "stop_f1": w4.micro_f1(stopped, sorted(stopped)),
                "v2": w4.s1_difference(greedy, stopped, page_hash), "repeat_aware_descriptive": ra}
    for rule in RULES:  # R1, primary prompt
        attr = {i: c[rule]["stop"]["attr"] for i, c in table[primary].items()}
        entry = w4.r1_test(attr, page_hash)
        entry["attribution_stopped"] = dict(sum(attr.values(), collections.Counter()))
        result["r1"][rule] = entry
    # the registered family of 22 p values, with Pathumma's S1 (Full-page) and R1 replaced by the new ones
    family = {k: v["p"] for k, v in registered["holm"].items()}
    for rule in RULES:
        family_rule = dict(family)
        family_rule["S1 pathumma / Full-page OCR"] = result["s1"][f"{primary} / {rule}"]["v2"]["p_one_sided"]
        family_rule["R1 pathumma"] = result["r1"][rule]["p_one_sided"]
        adjusted = w4.holm(family_rule)
        result["holm"][rule] = {k: adjusted[k] for k in ("S1 pathumma / Full-page OCR", "R1 pathumma")}
        result["holm"][rule]["largest_adjusted_p_in_family"] = max(v["p_holm"] for v in adjusted.values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for key, value in result["s1"].items():
        print("S1", key, {k: value[k] for k in ("greedy_f1", "stop_f1")}, value["v2"]["difference"], value["v2"]["ci95"],
              value["v2"]["p_one_sided"])
    for rule, value in result["r1"].items():
        print("R1", rule, value["ratio"], value["ci95"])
    print("Holm", result["holm"])
    print("scan", result["defect_scan_all_models"])
    print(args.out)


if __name__ == "__main__":
    main()
