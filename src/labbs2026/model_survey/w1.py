"""MODEL_SURVEY W1 — cross-model failure profile and the stop at a loop (offline, no GPU).

Up2mEz's work split (collab `20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`,
W1). On archived greedy outputs only: M1's Qwen3-VL-4B, PaddleOCR-VL-1.6 and
Wayu (each at its M1 primary prompt) and T1's Typhoon and base
(`BENCHMARK_QUESTION`), all on M1's 178 calibration items.

- **Stop:** T5b variant B (`loop_cut.variant_b`, k = 8 / 6), unchanged and
  applied offline as in M2. A non-looping output is one that ended before
  `max_new_tokens`; the stop should leave those untouched.
- **Surplus:** an output's surplus marks are its output marks minus its
  correct marks (order-free v2). The loop share is the share of all surplus
  marks that sits in outputs the stop cuts.
- **Attribution:** `attribution.attribute_marks(..., approximate_reorder=True)`
  on Full-page, as shares of all reference marks (as
  `TYPHOON_FAILURE_PROFILE.md` §2d). Anchored alignment is valid only for
  outputs of about reference length, so it is reported on the stopped outputs
  as well as on the raw ones.

Research logic only; `scripts/model_survey_w1.py` reads the archives and writes
the JSON.
"""

from __future__ import annotations

import collections
from typing import Any, Iterable

from labbs2026.thai_marks.attribution import CAUSES_APPROX
from labbs2026.thai_marks.loop_cut import variant_b
from labbs2026.thai_marks.order_free import prf

ATTRIBUTION_ROWS = ("correct",) + CAUSES_APPROX


def stopped(record: dict[str, Any]) -> dict[str, Any]:
    """The record with its output cut by the stop, and whether the stop changed it."""
    cut = variant_b(record)
    return {**record, "raw_output": cut, "stop_changed": cut != record["raw_output"]}


def surplus(counts: dict[str, Any]) -> int:
    """Output marks that earned no credit (order-free counts of one output)."""
    return counts["output_marks"] - counts["correct"]


def stop_summary(records: dict[str, dict], before: dict[str, dict], after: dict[str, dict]) -> dict[str, Any]:
    """How the stop touched one cell: loops, outputs changed, and where the surplus sits.

    `records`: id -> raw record; `before` / `after`: id -> order-free counts of the
    raw and the stopped output. `changed` is decided on the text, not the score.
    """
    ids = sorted(records)
    looping = [i for i in ids if records[i]["reached_max_new_tokens"]]
    non_looping = [i for i in ids if not records[i]["reached_max_new_tokens"]]
    changed = {i for i in ids if variant_b(records[i]) != records[i]["raw_output"]}
    total_surplus = sum(surplus(before[i]) for i in ids)
    return {
        "items": len(ids), "looping": len(looping), "non_looping": len(non_looping),
        "changed": len(changed), "changed_looping": len(changed & set(looping)),
        "changed_non_looping": len(changed & set(non_looping)),
        "changed_non_looping_share": len(changed & set(non_looping)) / len(non_looping) if non_looping else None,
        "surplus_marks": total_surplus,
        "surplus_in_cut_outputs": sum(surplus(before[i]) for i in changed),
        "loop_share_of_surplus": (sum(surplus(before[i]) for i in changed) / total_surplus) if total_surplus else None,
        "surplus_removed_by_stop": total_surplus - sum(surplus(after[i]) for i in ids),
    }


def attribution_shares(counters: Iterable[collections.Counter]) -> dict[str, Any]:
    """Pooled `attribute_marks` counts and each outcome's share of all reference marks."""
    total: collections.Counter = collections.Counter()
    for c in counters:
        total.update(c)
    marks = sum(total.values())
    return {"reference_marks": marks,
            "counts": {k: total[k] for k in ATTRIBUTION_ROWS},
            "share": {k: (total[k] / marks if marks else None) for k in ATTRIBUTION_ROWS},
            "wrong_share": ((marks - total["correct"]) / marks) if marks else None}


def cell_scores(counts: dict[str, dict], ids: list[str]) -> dict[str, Any]:
    """Micro P/R/F1 over `ids`."""
    return prf([counts[i] for i in ids])
