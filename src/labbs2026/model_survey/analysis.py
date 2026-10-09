"""MODEL_SURVEY_M1 scoring: T1's scoring v2 and the order-free v2 mark metric, per model and cell.

Offline, on fetched records; no model is loaded. The two models already in T1
(base, Typhoon) are scored by the same functions on their archived T1 outputs,
against the references this run records for the same item ids.
"""

from __future__ import annotations

import gzip
import json
import random
from pathlib import Path
from typing import Any

from labbs2026.thai_marks.analysis import analyze_t1_v2
from labbs2026.thai_marks.order_free import mark_counts, prf


class UnfinishedLeg(RuntimeError):
    pass


def load_role(run_root: Path, role: str, prompts: list[str]) -> tuple[list[dict], list[dict]]:
    """All records of one model, merged over shards, with every shard's manifest.

    Refuses a leg with a shard that did not finish, an item read twice, or a
    record count the manifests do not account for.
    """
    leg = run_root / "m1" / role
    record_files = sorted(leg.rglob("records.jsonl"))
    if not record_files:
        raise UnfinishedLeg(f"{leg}: no records")
    unfinished = [str(f.parent) for f in record_files if not (f.parent / "manifest.json").is_file()]
    if unfinished:
        raise UnfinishedLeg(f"{leg}: no manifest.json in {unfinished}")
    manifests = [json.loads((f.parent / "manifest.json").read_text("utf-8")) for f in record_files]
    records = [json.loads(line) for f in record_files
               for line in f.read_text("utf-8").splitlines() if line.strip()]
    keys = [(r["id"], r["prompt_kind"]) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{leg}: an (item, prompt) is recorded twice")
    expected = (sum(m["items"] for m in manifests) * len(prompts)
                - sum(len(m["failures"]) for m in manifests))
    if len(records) != expected:
        raise ValueError(f"{leg}: {len(records)} records, manifests imply {expected}")
    return records, manifests


def comparison_records(outputs_path: Path, roles: list[str], prompt: str,
                       references: dict[str, dict]) -> dict[str, list[dict]]:
    """Archived T1 outputs of `roles` for `prompt`, with this run's reference per item id."""
    archive = json.loads(gzip.open(outputs_path, "rt", encoding="utf-8").read())
    out: dict[str, list[dict]] = {}
    for role in roles:
        rows = []
        for record in archive["records"][role]:
            if record["prompt_kind"] != prompt or record["id"] not in references:
                continue
            ref = references[record["id"]]
            if ref["task"] != record["task"]:
                raise ValueError(f"{record['id']}: task differs between the runs")
            rows.append({**record, "reference": ref["reference"], "category": ref["category"]})
        out[role] = rows
    return out


def references_by_id(records: list[dict]) -> dict[str, dict]:
    """One reference per item id; refuses two different references for the same id."""
    out: dict[str, dict] = {}
    for r in records:
        entry = {"task": r["task"], "category": r["category"], "reference": r["reference"]}
        if out.setdefault(r["id"], entry) != entry:
            raise ValueError(f"{r['id']}: two references")
    return out


def order_free_counts(records: list[dict], *, max_cer: float, residual: bool) -> dict[tuple, dict]:
    """`mark_counts` per (task, prompt_kind, id)."""
    return {(r["task"], r["prompt_kind"], r["id"]):
            mark_counts(r["reference"], r["raw_output"], max_cer=max_cer, residual=residual)
            for r in records}


def order_free_cells(counts: dict[tuple, dict]) -> dict[str, dict]:
    """Micro precision/recall/F1 per `task / prompt` cell."""
    cells: dict[str, list[dict]] = {}
    for (task, prompt, _), c in sorted(counts.items()):
        cells.setdefault(f"{task} / {prompt}", []).append(c)
    return {name: prf(rows) for name, rows in cells.items()}


def paired_f1_difference(a: dict[str, dict], b: dict[str, dict], *, resamples: int,
                         seed: int) -> dict[str, Any]:
    """F1(b) − F1(a) over the items both read, with a 95% item-bootstrap interval.

    `a` and `b` map item id to `mark_counts`. Items are resampled in pairs, so
    the interval reflects which pages are hard, not only how many marks there
    are. Descriptive: M1 registers no decision rule on it.
    """
    ids = sorted(set(a) & set(b))
    if not ids:
        return {"n": 0, "difference": None, "ci95": None}

    def diff(sample: list[str]) -> float | None:
        fa, fb = prf([a[i] for i in sample])["f1"], prf([b[i] for i in sample])["f1"]
        return None if fa is None or fb is None else fb - fa

    rng = random.Random(seed)
    draws = sorted(d for d in (diff([rng.choice(ids) for _ in ids]) for _ in range(resamples))
                   if d is not None)
    return {"n": len(ids), "difference": diff(ids),
            "ci95": [draws[int(0.025 * len(draws))], draws[min(len(draws) - 1, int(0.975 * len(draws)))]]
            if draws else None}


def headline(t1_cell: dict[str, Any], mark_cell: dict[str, Any]) -> dict[str, Any]:
    """The numbers the T1 comparison reports, for one model and one cell."""
    return {
        "n": t1_cell["observations"],
        "median_cer": t1_cell["median_cer"],
        "located_rate": t1_cell["located_rate"],
        "mark_f1": mark_cell["f1"], "mark_recall": mark_cell["recall"],
        "mark_precision": mark_cell["precision"],
        "tone_error_correct_consonant": t1_cell["TONE"]["mark_specific_error"]["estimate"],
        "truncation_rate": t1_cell["truncation_rate"],
        "repetition_rate": t1_cell["repetition_rate"],
        "median_seconds_per_token": t1_cell["median_seconds_per_token"],
    }


def score_role(records: list[dict], *, null_seed: int, max_cer: float,
               residual: bool) -> dict[str, Any]:
    """T1 scoring v2, order-free cells and headline rows for one model's records."""
    t1 = analyze_t1_v2(records, seed=null_seed)
    counts = order_free_counts(records, max_cer=max_cer, residual=residual)
    marks = order_free_cells(counts)
    return {"t1_v2": t1, "order_free": marks,
            "headline": {cell: headline(t1[cell], marks[cell]) for cell in t1},
            "_counts": counts}
