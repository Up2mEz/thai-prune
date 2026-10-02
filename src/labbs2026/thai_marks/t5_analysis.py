"""T5 summaries as registered (`docs/stage0/T5_LOOP_DECODING_DRAFT.md` §3).

Offline. Every comparison is paired with the `greedy` arm of the same run, per
(task, prompt) cell; nothing is pooled across tasks.
"""

from __future__ import annotations

import collections
import random
import statistics
from typing import Any, Sequence

from labbs2026.thai_marks.analysis import chance_threshold, score_t1_record_v2, summarize_t1_v2
from labbs2026.thai_marks.attribution import attribute_marks
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.order_free import mark_counts, prf

CONTROL = "greedy"
BOOTSTRAP_SEED = 20261003
BOOTSTRAP_RESAMPLES = 2000
FULL_PAGE = "Full-page OCR"


def paired_bootstrap_delta_f1(arm: Sequence[dict], control: Sequence[dict], *,
                              seed: int = BOOTSTRAP_SEED,
                              resamples: int = BOOTSTRAP_RESAMPLES) -> dict[str, float]:
    """95% interval of micro F1(arm) − F1(control), resampling pages (paired)."""
    if len(arm) != len(control) or not arm:
        raise ValueError("paired samples of equal, non-zero length required")
    rng = random.Random(seed)
    n = len(arm)
    deltas = []
    for _ in range(resamples):
        pick = [rng.randrange(n) for _ in range(n)]
        a = prf([arm[i] for i in pick])["f1"] or 0.0
        c = prf([control[i] for i in pick])["f1"] or 0.0
        deltas.append(a - c)
    deltas.sort()
    point = (prf(list(arm))["f1"] or 0.0) - (prf(list(control))["f1"] or 0.0)
    return {"delta": point, "ci_low": deltas[int(0.025 * resamples)],
            "ci_high": deltas[int(0.975 * resamples) - 1]}


def _speed(rows: Sequence[dict]) -> dict[str, Any]:
    return {"median_generated_tokens": statistics.median(r["generated_tokens"] for r in rows),
            "total_generated_tokens": sum(r["generated_tokens"] for r in rows),
            "median_seconds": statistics.median(r["seconds_generate"] for r in rows),
            "total_seconds": sum(r["seconds_generate"] for r in rows)}


def summarize_t5(records: Sequence[dict], t1_greedy: Sequence[dict] | None = None,
                 *, located_seed: int = 20260928) -> dict[str, Any]:
    """Per (task, prompt) cell: every arm against `greedy`, as registered."""
    cells: dict[tuple, dict[str, dict[str, dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(dict))
    for r in records:
        cells[(r["task"], r["prompt_kind"])][r["arm"]][r["id"]] = r
    t1 = {(r["task"], r["prompt_kind"], r["id"]): r for r in (t1_greedy or [])}
    out: dict[str, Any] = {}
    for (task, prompt), arms in sorted(cells.items()):
        if CONTROL not in arms:
            raise ValueError(f"no {CONTROL} arm in {task} / {prompt}")
        ids = sorted(set.intersection(*(set(a) for a in arms.values())))
        control = [arms[CONTROL][i] for i in ids]
        loop_free = [i for i in ids if not arms[CONTROL][i]["reached_max_new_tokens"]]
        chance = chance_threshold([extract_text(r["reference"]) for r in control],
                                  [extract_text(r["raw_output"]) for r in control],
                                  seed=located_seed)
        block: dict[str, Any] = {"items": len(ids), "loop_free_items": len(loop_free),
                                 "located_threshold_from": CONTROL, "chance": chance, "arms": {}}
        counts = {name: {i: mark_counts(a[i]["reference"], a[i]["raw_output"], residual=True)
                         for i in ids} for name, a in arms.items()}
        for name, a in sorted(arms.items()):
            rows = [a[i] for i in ids]
            entry: dict[str, Any] = {
                "loop_rate": statistics.fmean(r["reached_max_new_tokens"] for r in rows),
                **_speed(rows),
                "order_free_marks": prf([counts[name][i] for i in ids]),
                "loop_free_order_free_marks": prf([counts[name][i] for i in loop_free]),
                "loop_free_identical_to_greedy": statistics.fmean(
                    a[i]["raw_output"] == arms[CONTROL][i]["raw_output"] for i in loop_free)
                if loop_free else None,
            }
            if task == FULL_PAGE:
                causes = collections.Counter()
                for r in rows:
                    causes += attribute_marks(r["reference"], r["raw_output"],
                                              approximate_reorder=True)
                entry["mark_causes"] = dict(causes)
            else:
                scored = [score_t1_record_v2({**r, "prompt_kind": prompt},
                                             located_below=chance["threshold"]) for r in rows]
                entry["v2"] = summarize_t1_v2(scored)
            if name != CONTROL:
                entry["delta_f1_vs_greedy"] = paired_bootstrap_delta_f1(
                    [counts[name][i] for i in ids], [counts[CONTROL][i] for i in ids])
                if loop_free:
                    entry["loop_free_delta_f1_vs_greedy"] = (
                        (entry["loop_free_order_free_marks"]["f1"] or 0.0)
                        - (prf([counts[CONTROL][i] for i in loop_free])["f1"] or 0.0))
            guards = [r["ngram_block"] for r in rows if r.get("ngram_block")]
            if guards:
                entry["ngram_block"] = {
                    "items_with_interventions": sum(g["interventions"] > 0 for g in guards),
                    "total_interventions": sum(g["interventions"] for g in guards),
                    "whitelist_ids": guards[0]["whitelist_ids"]}
            block["arms"][name] = entry
        if t1:
            same = [arms[CONTROL][i]["raw_output"] == t1[(task, prompt, i)]["raw_output"]
                    for i in ids if (task, prompt, i) in t1]
            block["greedy_identical_to_t1"] = statistics.fmean(same) if same else None
        out[f"{task} / {prompt}"] = block
    return out
