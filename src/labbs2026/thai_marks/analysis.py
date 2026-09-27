"""Offline analysis of T1 and T2, exactly as registered.

Runs on fetched records on CPU; no model is loaded. Every aggregate carries an
item-level bootstrap interval, stratified by task so each resample keeps the
calibration split's task proportions.
"""

from __future__ import annotations

import collections
import random
import statistics
from typing import Any, Callable, Iterable, Sequence

from labbs2026.thai_marks.decompose import (
    align,
    edit_distance_from,
    is_repetitive,
    mark_decomposition,
    reference_fates,
)
from labbs2026.thai_marks.normalize import normalize_text
from labbs2026.thai_marks.orthography import TONE_MARKS

BOOTSTRAP = 10_000
SEED = 20260927
MARK_KINDS = ("TONE", "UPPER", "LOWER")


def _strata(items: Sequence[dict]) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = collections.defaultdict(list)
    for position, item in enumerate(items):
        groups[item["task"]].append(position)
    return groups


def bootstrap(items: Sequence[dict], statistic: Callable[[list[dict]], float | None],
              *, resamples: int = BOOTSTRAP, seed: int = SEED) -> dict[str, Any]:
    """Point estimate and 95% percentile interval, resampling items within task."""
    estimate = statistic(list(items))
    rng = random.Random(seed)
    groups = _strata(items)
    draws = []
    for _ in range(resamples):
        sample = [items[rng.choice(pos)] for pos in groups.values() for _ in pos]
        value = statistic(sample)
        if value is not None:
            draws.append(value)
    draws.sort()
    if not draws:
        return {"estimate": estimate, "ci_low": None, "ci_high": None, "n_items": len(items)}
    return {
        "estimate": estimate,
        "ci_low": draws[int(0.025 * len(draws))],
        "ci_high": draws[min(len(draws) - 1, int(0.975 * len(draws)))],
        "n_items": len(items),
    }


def _ratio(items: Iterable[dict], num: str, den: str) -> float | None:
    n = d = 0
    for item in items:
        n += item[num]
        d += item[den]
    return n / d if d else None


# --- T1 ----------------------------------------------------------------------


def score_t1_record(record: dict) -> dict[str, Any]:
    """Per-observation metrics on normalized strings, from one alignment."""
    reference = normalize_text(record["reference"])
    hypothesis = normalize_text(record["raw_output"])
    pairs = align(reference, hypothesis)
    distance = edit_distance_from(pairs, reference, hypothesis)
    marks = mark_decomposition(reference, hypothesis, pairs)
    out = {
        "id": record["id"], "task": record["task"],
        "chars": len(reference), "edits": distance,
        "cer": distance / len(reference) if reference else None,
        "truncated": int(bool(record["reached_max_new_tokens"])),
        "repetitive": int(is_repetitive(record["raw_output"])),
        "seconds_per_token": record["seconds_per_generated_token"],
        "consonant_n": marks["CONSONANT"]["n"], "consonant_error": marks["CONSONANT"]["error"],
    }
    for kind in MARK_KINDS:
        entry = marks.get(kind, {})
        out[f"{kind}_n"] = entry.get("n", 0)
        out[f"{kind}_error"] = entry.get("n", 0) - entry.get("correct", 0)
        out[f"{kind}_deleted"] = entry.get("deleted", 0)
        out[f"{kind}_same_class"] = entry.get("same_class", 0)
        out[f"{kind}_base_n"] = entry.get("base_correct_n", 0)
        out[f"{kind}_base_error"] = entry.get("base_correct_error", 0)
    return out


def summarize_t1(scored: Sequence[dict]) -> dict[str, Any]:
    items = [s for s in scored if s["chars"]]
    summary: dict[str, Any] = {
        "observations": len(scored),
        "empty_references_skipped": len(scored) - len(items),
        "macro_cer": bootstrap(items, lambda xs: statistics.fmean(x["cer"] for x in xs)),
        "micro_cer": bootstrap(items, lambda xs: _ratio(xs, "edits", "chars")),
        "consonant_error": bootstrap(items, lambda xs: _ratio(xs, "consonant_error", "consonant_n")),
        "truncation_rate": statistics.fmean(s["truncated"] for s in scored) if scored else None,
        "repetition_rate": statistics.fmean(s["repetitive"] for s in scored) if scored else None,
        "median_seconds_per_token": statistics.median(s["seconds_per_token"] for s in scored)
        if scored else None,
    }
    for kind in MARK_KINDS:
        summary[kind] = {
            "error": bootstrap(items, lambda xs, k=kind: _ratio(xs, f"{k}_error", f"{k}_n")),
            "mark_specific_error": bootstrap(
                items, lambda xs, k=kind: _ratio(xs, f"{k}_base_error", f"{k}_base_n")),
            "deletion_share_of_errors": _ratio(items, f"{kind}_deleted", f"{kind}_error"),
            "same_class_share_of_errors": _ratio(items, f"{kind}_same_class", f"{kind}_error"),
            "n": sum(s[f"{kind}_n"] for s in items),
        }
    return summary


# --- T2 ----------------------------------------------------------------------


def _argmax(variants: dict, key: Callable[[dict], float]) -> str:
    return max(sorted(variants), key=lambda label: key(variants[label]))


def site_outcomes(site: dict, lambdas: Sequence[float] = (0.5, 1.0)) -> dict[str, Any]:
    variants = site["variants"]
    reference = site["reference"]
    out = {
        "kind": site["kind"],
        "oracle": int(_argmax(variants, lambda v: v["image"]["logprob"]) == reference),
        "prior": int(_argmax(variants, lambda v: v["no_image"]["logprob"]) == reference),
        "image_gain": variants[reference]["image"]["logprob"]
        - variants[reference]["no_image"]["logprob"],
    }
    for lam in lambdas:
        out[f"contrastive_{lam}"] = int(_argmax(
            variants, lambda v, l=lam: v["image"]["logprob"] - l * v["no_image"]["logprob"]
        ) == reference)
    return out


def greedy_correct_at(site: dict, reference: str, hypothesis: str,
                      fates: dict[int, str] | None = None,
                      pairs: list | None = None) -> int:
    """Whether greedy decoding got this site right, from a T1 hypothesis.

    For a mark site the mark must survive; for a bare consonant the consonant
    must survive with no tone mark inserted directly after it.
    """
    if pairs is None:
        pairs = align(reference, hypothesis)
    if fates is None:
        fates = reference_fates(reference, hypothesis)
    index = site["index"]
    if site["kind"] != "TONE_ABSENT":
        return int(fates.get(index) == "correct")
    if fates.get(index) != "correct":
        return 0
    hyp_of = {r: h for r, h in pairs if r is not None and h is not None}
    h = hyp_of[index]
    return int(not (h + 1 < len(hypothesis) and hypothesis[h + 1] in TONE_MARKS))


def summarize_t2(items: Sequence[dict], greedy: dict[str, str] | None = None) -> dict[str, Any]:
    """Site-level accuracies by kind, aggregated per item before bootstrapping."""
    per_item = []
    for item in items:
        counts = collections.Counter()
        gains = collections.defaultdict(list)
        hypothesis = greedy.get(item["id"]) if greedy else None
        pairs = fates = None
        if hypothesis is not None:
            hyp = normalize_text(hypothesis)
            pairs = align(item["reference_collapsed"], hyp)
            fates = reference_fates(item["reference_collapsed"], hyp)
        for site in item["sites"]:
            outcome = site_outcomes(site)
            kind = outcome["kind"]
            counts[f"{kind}_n"] += 1
            for key in ("oracle", "prior", "contrastive_0.5", "contrastive_1.0"):
                counts[f"{kind}_{key}"] += outcome[key]
            gains[kind].append(outcome["image_gain"])
            if hypothesis is not None:
                counts[f"{kind}_greedy"] += greedy_correct_at(
                    site, item["reference_collapsed"], hyp, fates, pairs)
                counts[f"{kind}_greedy_n"] += 1
        per_item.append({"id": item["id"], "task": item["task"], **counts,
                         "gains": dict(gains)})

    summary: dict[str, Any] = {"items": len(per_item)}
    for kind in ("TONE", "UPPER", "LOWER", "TONE_ABSENT"):
        n_key = f"{kind}_n"
        present = [p for p in per_item if p.get(n_key)]
        if not present:
            continue
        block = {"sites": sum(p[n_key] for p in present)}
        for key in ("oracle", "prior", "contrastive_0.5", "contrastive_1.0"):
            block[key] = bootstrap(present, lambda xs, k=f"{kind}_{key}": _ratio(
                [{**x, k: x.get(k, 0)} for x in xs], k, n_key))
        if greedy:
            block["greedy"] = bootstrap(present, lambda xs, k=kind: _ratio(
                [{**x, f"{k}_greedy": x.get(f"{k}_greedy", 0),
                  f"{k}_greedy_n": x.get(f"{k}_greedy_n", 0)} for x in xs],
                f"{k}_greedy", f"{k}_greedy_n"))
        all_gains = [g for p in present for g in p["gains"].get(kind, [])]
        block["image_gain_median"] = statistics.median(all_gains)
        block["image_gain_share_positive"] = statistics.fmean(g > 0 for g in all_gains)
        summary[kind] = block
    return summary
