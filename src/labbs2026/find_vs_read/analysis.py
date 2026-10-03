"""Offline analysis of FIND_VS_READ_F1, as registered.

Per arm: found rate (with its chance baseline), exact rate, over-generation.
Paired by item: CROP vs WHOLE (primary) and WHOLE_MARKED vs WHOLE
(secondary) — a found-transition table, the found-rate difference, and
mark-specific and consonant error on items **found in both arms**, measured on
the best-matching window only, so a misplaced or page-length answer is never
counted as misreading. Primary normalization: T1's `normalize_text`;
structure-aware normalization as a sensitivity.
"""

from __future__ import annotations

import collections
import statistics
from typing import Any, Callable, Iterable, Sequence

from labbs2026.find_vs_read.scoring import chance_found_rate, score_answer
from labbs2026.output_diagnostics.structure import structural_normalize
from labbs2026.thai_marks.analysis import bootstrap
from labbs2026.thai_marks.normalize import normalize_text

ARMS = ("WHOLE", "CROP", "WHOLE_MARKED")
CONTRASTS = (("CROP", "WHOLE"), ("WHOLE_MARKED", "WHOLE"))
KINDS = ("TONE", "UPPER", "LOWER")
NORMALIZERS: dict[str, Callable[[str], str]] = {"t1": normalize_text, "structural": structural_normalize}


def item_rows(records: Iterable[dict], normalize: Callable[[str], str] = normalize_text) -> list[dict]:
    rows = []
    for rec in records:
        ref = normalize(rec["reference"])
        row: dict[str, Any] = {"id": rec["id"], "task": rec["task"], "reference": ref, "arms": {}}
        for arm, a in rec["arms"].items():
            if a.get("failed"):
                row["arms"][arm] = {"failed": True}
                continue
            hyp = normalize(a["raw_output"])
            row["arms"][arm] = {**score_answer(ref, hyp), "hypothesis": hyp,
                                "reached_max": a["reached_max_new_tokens"],
                                "seconds": a["seconds_generate"], "visual_tokens": a["visual_tokens"]}
        rows.append(row)
    return rows


def _ratio(xs, num, den):
    n = sum(x[num] for x in xs)
    d = sum(x[den] for x in xs)
    return n / d if d else None


def _rate(xs, key):
    return statistics.fmean(1.0 if x[key] else 0.0 for x in xs) if xs else None


def summarize(rows: Sequence[dict], *, resamples: int = 10_000) -> dict[str, Any]:
    rows = [r for r in rows if r["reference"]]
    out: dict[str, Any] = {"items": len(rows)}
    for arm in ARMS:
        have = [r for r in rows if arm in r["arms"] and not r["arms"][arm].get("failed")]
        if not have:
            continue
        cells = [{"task": r["task"], **r["arms"][arm]} for r in have]
        found = [c for c in cells if c["found"]]
        out[arm] = {
            "n": len(cells),
            "found_rate": bootstrap(cells, lambda xs: _rate(xs, "found"), resamples=resamples),
            "chance_found_rate": chance_found_rate([r["reference"] for r in have],
                                                   [r["arms"][arm]["hypothesis"] for r in have]),
            "exact_rate": _rate(cells, "exact"),
            "window_cer_found_micro": _ratio(found, "window_distance", "ref_chars") if found else None,
            "median_extra_chars": statistics.median(c["extra_chars"] for c in cells),
            "reached_max_new_tokens": sum(c["reached_max"] for c in cells),
            "median_seconds": statistics.median(c["seconds"] for c in cells),
            "median_visual_tokens": statistics.median(c["visual_tokens"] for c in cells),
        }
    for arm, base in CONTRASTS:
        both = [r for r in rows if all(k in r["arms"] and not r["arms"][k].get("failed") for k in (arm, base))]
        if not both:
            continue
        pairs = [{"task": r["task"], "arm": r["arms"][arm], "base": r["arms"][base]} for r in both]
        transitions = collections.Counter((p["base"]["found"], p["arm"]["found"]) for p in pairs)
        kept = [p for p in pairs if p["arm"]["found"] and p["base"]["found"]]

        def paired(num, den, xs=kept):
            def diff(ys):
                a, b = _ratio([y["arm"] for y in ys], num, den), _ratio([y["base"] for y in ys], num, den)
                return None if a is None or b is None else a - b
            return {base: _ratio([x["base"] for x in xs], num, den), arm: _ratio([x["arm"] for x in xs], num, den),
                    "difference": bootstrap(xs, diff, resamples=resamples)} if xs else None

        entry: dict[str, Any] = {
            "items": len(pairs), "found_in_both": len(kept),
            "found_transitions": {f"{'found' if b else 'missed'}->{'found' if a else 'missed'}": n
                                  for (b, a), n in sorted(transitions.items())},
            "found_rate_difference": bootstrap(
                pairs, lambda ys: _rate([y["arm"] for y in ys], "found") - _rate([y["base"] for y in ys], "found"),
                resamples=resamples),
            "window_cer_found_in_both": paired("window_distance", "ref_chars"),
            "consonant_error_found_in_both": paired("consonant_error", "consonant_n"),
        }
        for kind in KINDS:
            entry[f"{kind}_mark_specific_error_found_in_both"] = paired(f"{kind}_base_error", f"{kind}_base_n")
        out[f"{arm}_vs_{base}"] = entry
    return out
