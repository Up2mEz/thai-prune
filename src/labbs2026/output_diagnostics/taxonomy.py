"""Per-item error taxonomy: which failure a CER number is actually made of.

For one (reference, raw output) pair this reports the registered T1 CER next
to the same CER after structure-aware normalization and after de-looping, the
insertion/deletion/substitution split, an order-insensitive character overlap
(to tell reading-order problems from misreading), and T1's mark decomposition.
`primary_cause` is a descriptive label from fixed thresholds, meant to route
attention, not to be tested.

Mark-error rates are only meaningful on items whose cause is `misread` (or
`reading_order`): in a looped or over-generated output most reference marks
are "deleted" because that part of the page was never read, so pooling such
items mixes the loop rate into the mark rate.
"""

from __future__ import annotations

import collections
import re
from typing import Any

from labbs2026.output_diagnostics.distance import levenshtein
from labbs2026.output_diagnostics.structure import deloop, loop_period, structural_normalize
from labbs2026.thai_marks.decompose import align, is_repetitive, mark_decomposition
from labbs2026.thai_marks.normalize import normalize_text

_THAI = re.compile(r"[฀-๿]")

# thresholds for the descriptive label, fixed 2026-09-28 before any evaluation output
FORMAT_LOSS_CER_GAP = 0.20
LOOP_SHARE = 0.30
OMISSION_RECALL = 0.70
OVERGENERATION_PRECISION = 0.70
ORDER_RECALL = 0.90
ORDER_CER = 0.30

# full alignments (ins/del/sub split, mark fates) only below this many DP cells;
# the distance itself is always exact (bit-parallel, `distance.levenshtein`)
MAX_ALIGN_CELLS = 4_000_000


def _thai_count(text: str) -> int:
    return len(_THAI.findall(text))


def _alignable(reference: str, hypothesis: str) -> bool:
    return (len(reference) + 1) * (len(hypothesis) + 1) <= MAX_ALIGN_CELLS


def _cer(reference: str, hypothesis: str) -> tuple[float | None, dict[str, int | None]]:
    edits = levenshtein(reference, hypothesis)
    counts: dict[str, int | None] = {"edits": edits, "insertions": None, "deletions": None, "substitutions": None}
    if _alignable(reference, hypothesis):
        pairs = align(reference, hypothesis)
        ins = sum(1 for r, _ in pairs if r is None)
        dele = sum(1 for _, h in pairs if h is None)
        counts.update(insertions=ins, deletions=dele, substitutions=edits - ins - dele)
    return (edits / len(reference) if reference else None), counts


def bag_overlap(reference: str, hypothesis: str) -> tuple[float, float]:
    """Order-insensitive character recall and precision (spaces ignored)."""
    ref = collections.Counter(reference.replace(" ", ""))
    hyp = collections.Counter(hypothesis.replace(" ", ""))
    common = sum((ref & hyp).values())
    return (common / max(1, sum(ref.values())), common / max(1, sum(hyp.values())))


def diagnose(reference: str, raw_output: str, *, with_marks: bool = True) -> dict[str, Any]:
    ref_t1 = normalize_text(reference)
    hyp_t1 = normalize_text(raw_output)
    ref_s = structural_normalize(reference)
    hyp_s = structural_normalize(raw_output)
    loop = loop_period(raw_output)
    hyp_sd = structural_normalize(deloop(raw_output))

    cer_t1, counts_t1 = _cer(ref_t1, hyp_t1)
    cer_s, _ = _cer(ref_s, hyp_s)
    cer_sd, counts_sd = _cer(ref_s, hyp_sd)
    recall, precision = bag_overlap(ref_s, hyp_sd)
    raw_thai = _thai_count(raw_output)
    format_lost = max(0, raw_thai - _thai_count(hyp_t1))
    looped_chars = 0
    if loop is not None:
        looped_chars = len(raw_output) - (loop[1] + loop[0])

    out: dict[str, Any] = {
        "ref_chars": len(ref_t1), "hyp_chars_t1": len(hyp_t1),
        "cer_t1": cer_t1, "cer_structural": cer_s, "cer_structural_delooped": cer_sd,
        **{f"t1_{k}": v for k, v in counts_t1.items()},
        **{f"sd_{k}": v for k, v in counts_sd.items()},
        "thai_in_raw": raw_thai,
        "thai_lost_to_t1_normalization": format_lost,
        "t1_repetitive": is_repetitive(raw_output),
        "loop_period": loop[0] if loop else None,
        "looped_share_of_output": looped_chars / max(1, len(raw_output)),
        "bag_recall": recall, "bag_precision": precision,
        "marks": (mark_decomposition(ref_s, hyp_sd)
                  if with_marks and _alignable(ref_s, hyp_sd) else None),
    }
    out["primary_cause"] = primary_cause(out)
    return out


def primary_cause(d: dict[str, Any]) -> str:
    """Descriptive routing label; the order of the checks is the priority."""
    if d["cer_t1"] is None:
        return "empty_reference"
    if d["cer_t1"] - (d["cer_structural"] or 0) >= FORMAT_LOSS_CER_GAP and d["thai_lost_to_t1_normalization"] > 0:
        return "format_loss"
    if d["looped_share_of_output"] >= LOOP_SHARE:
        return "loop"
    if d["bag_recall"] < OMISSION_RECALL:
        return "omission"
    if d["bag_precision"] < OVERGENERATION_PRECISION:
        return "overgeneration"   # e.g. near-repeated paragraphs an exact loop test misses
    if d["bag_recall"] >= ORDER_RECALL and (d["cer_structural_delooped"] or 0) >= ORDER_CER:
        return "reading_order"
    return "misread"
