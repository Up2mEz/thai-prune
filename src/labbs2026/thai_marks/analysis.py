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
    _fates_from,
    align,
    align_anchored,
    edit_distance_from,
    is_repetitive,
    mark_decomposition,
    reference_fates,
)
from labbs2026.thai_marks.extract import extract, extract_text
from labbs2026.thai_marks.lexicon import classify_mark_errors
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
    lexical = classify_mark_errors(reference, hypothesis, pairs) if reference else {}
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
        lex = lexical.get(kind, {})
        out[f"{kind}_real_word"] = lex.get("real_word", 0)
        out[f"{kind}_non_word"] = lex.get("non_word", 0)
        out[f"{kind}_word_lost"] = lex.get("word_lost", 0)
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
            # Registered addendum 2026-09-27: among errors on in-lexicon words
            # whose misread span survives, the share that is another real word.
            "real_word_share": bootstrap(items, lambda xs, k=kind: _ratio(
                [{**x, "_classified": x[f"{k}_real_word"] + x[f"{k}_non_word"]} for x in xs],
                f"{k}_real_word", "_classified")),
            "lexical_counts": {c: sum(s[f"{kind}_{c}"] for s in items)
                               for c in ("real_word", "non_word", "word_lost")},
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


CONVENTIONS = ("sum", "mean", "first_divergent")


def variant_scores(site: dict, condition: str, convention: str) -> dict[str, float] | None:
    """Each variant's score for one site under a scoring convention.

    `sum` is the registered summed log-probability of the window; `mean`
    divides by its token count; `first_divergent` is the log-probability of
    the first token after the longest token prefix every variant shares — the
    decision greedy decoding actually makes there, before later tokens are
    conditioned on different text. Needs per-token data (runs from 2026-09-28
    on); returns None when it is absent, or when one variant's tokens are a
    prefix of all the others'.
    """
    variants = site["variants"]
    if convention == "sum":
        return {k: v[condition]["logprob"] for k, v in variants.items()}
    if any("token_logprobs" not in v[condition] for v in variants.values()):
        return None
    if convention == "mean":
        return {k: v[condition]["logprob"] / v[condition]["tokens"] for k, v in variants.items()}
    if convention == "first_divergent":
        seqs = [v[condition]["token_ids"] for v in variants.values()]
        shared = 0
        while all(len(s) > shared for s in seqs) and len({s[shared] for s in seqs}) == 1:
            shared += 1
        if any(len(s) == shared for s in seqs):
            return None
        return {k: v[condition]["token_logprobs"][shared] for k, v in variants.items()}
    raise ValueError(f"unknown convention {convention!r}")


def oracle_by_convention(items: Sequence[dict]) -> dict[str, dict[str, Any]]:
    """Oracle and prior accuracy per mark kind under every scoring convention."""
    out: dict[str, dict[str, Any]] = {}
    for convention in CONVENTIONS:
        counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for item in items:
            for site in item["sites"]:
                c = counts[site["kind"]]
                for condition, key in (("image", "oracle"), ("no_image", "prior")):
                    scores = variant_scores(site, condition, convention)
                    if scores is None:
                        c[f"{key}_unscorable"] += 1
                        continue
                    c[f"{key}_n"] += 1
                    c[key] += _argmax({k: {"s": v} for k, v in scores.items()},
                                      lambda v: v["s"]) == site["reference"]
        out[convention] = {
            kind: {key: (c[key] / c[f"{key}_n"] if c[f"{key}_n"] else None)
                   for key in ("oracle", "prior")} | {
                       "sites": c["oracle_n"], "unscorable": c["oracle_unscorable"]}
            for kind, c in sorted(counts.items())
        }
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


def _greedy_fates_v1(reference_collapsed: str, greedy_output: str):
    hyp = normalize_text(greedy_output)
    return hyp, align(reference_collapsed, hyp), reference_fates(reference_collapsed, hyp)


def summarize_t2(items: Sequence[dict], greedy: dict[str, str] | None = None,
                 fates_of: Callable = _greedy_fates_v1) -> dict[str, Any]:
    """Site-level accuracies by kind, aggregated per item before bootstrapping."""
    per_item = []
    for item in items:
        counts = collections.Counter()
        gains = collections.defaultdict(list)
        hypothesis = greedy.get(item["id"]) if greedy else None
        pairs = fates = None
        if hypothesis is not None:
            hyp, pairs, fates = fates_of(item["reference_collapsed"], hypothesis)
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


# --- Scoring version 2 (docs/stage0/THAI_MARKS_T1_SCORING_V2.md) -------------
#
# Version 1 above is kept unchanged so the as-registered numbers stay
# reproducible. Version 2 differs in three ways only: structure-aware
# extraction (`extract.py`), reference-anchored alignment, and results that are
# always split by task and prompt, never pooled.


def anchored_cer(reference: str, hypothesis: str) -> float | None:
    if not reference:
        return None
    pairs, _, _ = align_anchored(reference, hypothesis)
    return edit_distance_from(pairs, reference, hypothesis) / len(reference)


def chance_threshold(references: Sequence[str], hypotheses: Sequence[str], *,
                     seed: int, quantile: float = 0.05) -> dict[str, Any]:
    """The anchored CER a wrong answer reaches by chance, for one cell.

    Each reference is aligned against a different item's hypothesis from the
    same cell (a seeded derangement). An observed CER below the `quantile` of
    this null is better than chance at that level; above it, the output cannot
    be told apart from one that never read the reference, and chance
    character matches must not be credited as reading.
    """
    order = [i for i, r in enumerate(references) if r]
    if len(order) < 2:
        return {"threshold": None, "n": len(order)}
    random.Random(seed).shuffle(order)
    null = sorted(anchored_cer(references[order[k]], hypotheses[order[(k + 1) % len(order)]])
                  for k in range(len(order)))
    return {
        "threshold": null[int(quantile * len(null))],
        "quantile": quantile, "n": len(null),
        "null_median": statistics.median(null), "null_min": null[0],
    }


def score_t1_record_v2(record: dict, located_below: float | None = None) -> dict[str, Any]:
    """Per-observation reading metrics, with surplus output measured apart.

    `cer` is reference-anchored: text produced before or after the span that
    matches the reference is not a reading error, and is reported as
    `overgeneration` (surplus characters per reference character) instead.
    With `located_below` (from `chance_threshold`), an output whose anchored
    CER is not below chance level is `located = 0`: it is scored as reading
    nothing (every reference character deleted, `cer` 1) rather than credited
    with chance matches; `cer_raw` keeps the unthresholded value.
    `ref_in_figure_share` is the `TYPHOON_CARD` contract diagnostic: the share
    of reference characters read correctly only when `<figure>` content is
    kept, i.e. transcription placed where the prompt asks for an image
    description. It is never folded into `cer`.
    """
    reference = extract_text(record["reference"])
    hypothesis, structure = extract(record["raw_output"])
    pairs, start, end = align_anchored(reference, hypothesis)
    edits = edit_distance_from(pairs, reference, hypothesis)
    cer_raw = edits / len(reference) if reference else None
    located = int(cer_raw is not None and (located_below is None or cer_raw < located_below))
    if reference and not located:
        pairs, start, end, edits = [(i, None) for i in range(len(reference))], 0, 0, len(reference)
    marks = mark_decomposition(reference, hypothesis, pairs)
    lexical = classify_mark_errors(reference, hypothesis, pairs) if reference else {}

    ref_in_figure = None
    if reference and structure["figures"]:
        kept = extract_text(record["raw_output"], keep_figures=True)
        kept_pairs, _, _ = align_anchored(reference, kept)
        kept_cer = edit_distance_from(kept_pairs, reference, kept) / len(reference)
        kept_located = located_below is None or kept_cer < located_below
        kept_fates = _fates_from(kept_pairs, reference, kept)[0] if kept_located else {}
        fates, _ = _fates_from(pairs, reference, hypothesis)
        only_in_figure = sum(1 for i in range(len(reference))
                             if kept_fates.get(i) == "correct" and fates.get(i) != "correct")
        ref_in_figure = only_in_figure / len(reference)

    out = {
        "id": record["id"], "task": record["task"], "prompt_kind": record.get("prompt_kind"),
        "chars": len(reference), "edits": edits,
        "cer": edits / len(reference) if reference else None,
        "cer_raw": cer_raw, "located": located,
        "hyp_chars": len(hypothesis), "window_chars": end - start,
        "overgeneration": (len(hypothesis) - (end - start)) / len(reference) if reference else None,
        "figures": structure["figures"], "unclosed_figures": structure["unclosed_figures"],
        "ref_in_figure_share": ref_in_figure,
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
        lex = lexical.get(kind, {})
        out[f"{kind}_real_word"] = lex.get("real_word", 0)
        out[f"{kind}_non_word"] = lex.get("non_word", 0)
        out[f"{kind}_word_lost"] = lex.get("word_lost", 0)
    return out


def summarize_t1_v2(scored: Sequence[dict]) -> dict[str, Any]:
    """Version-1 summary fields plus robust and surplus-output metrics, one cell."""
    cells = {(s["task"], s["prompt_kind"]) for s in scored}
    if len(cells) > 1:
        raise ValueError(f"summarize one (task, prompt) cell at a time, got {sorted(cells)}")
    summary = summarize_t1(scored)
    items = [s for s in scored if s["chars"]]
    summary["median_cer"] = statistics.median(s["cer"] for s in items) if items else None
    summary["located_rate"] = statistics.fmean(s["located"] for s in items) if items else None
    summary["median_cer_raw"] = statistics.median(s["cer_raw"] for s in items) if items else None
    summary["median_overgeneration"] = (
        statistics.median(s["overgeneration"] for s in items) if items else None)
    with_figure = [s for s in items if s["figures"]]
    summary["figure_contract"] = {
        "outputs_with_figure": len(with_figure),
        "unclosed_figure_outputs": sum(1 for s in items if s["unclosed_figures"]),
        "mean_ref_in_figure_share": (
            statistics.fmean(s["ref_in_figure_share"] for s in with_figure)
            if with_figure else None),
    }
    return summary


def analyze_t1_v2(records: Sequence[dict], *, seed: int) -> dict[str, dict[str, Any]]:
    """Scoring version 2 for one model's T1 records: per cell, chance-calibrated."""
    cells: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for record in records:
        cells[(record["task"], record["prompt_kind"])].append(record)
    out = {}
    for (task, prompt), rows in sorted(cells.items()):
        rows = sorted(rows, key=lambda r: r["id"])
        chance = chance_threshold([extract_text(r["reference"]) for r in rows],
                                  [extract_text(r["raw_output"]) for r in rows], seed=seed)
        scored = [score_t1_record_v2(r, located_below=chance["threshold"]) for r in rows]
        summary = summarize_t1_v2(scored)
        summary["chance"] = chance
        out[f"{task} / {prompt}"] = summary
    return out


def summarize_t1_cells(scored: Sequence[dict]) -> dict[str, dict[str, Any]]:
    """One summary per (task, prompt) cell; results are never pooled across tasks."""
    cells: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for s in scored:
        cells[(s["task"], s["prompt_kind"])].append(s)
    return {f"{task} / {prompt}": summarize_t1_v2(rows)
            for (task, prompt), rows in sorted(cells.items())}


def greedy_fates_v2(reference_collapsed: str, greedy_output: str,
                    located_below: float | None = None):
    """Hypothesis, alignment and site fates of a T1 greedy output under version 2.

    The reference stays whitespace-collapsed only, because T2 site indices
    point into it. An output not below the chance threshold reads no site.
    """
    hypothesis = extract_text(greedy_output)
    pairs, _, _ = align_anchored(reference_collapsed, hypothesis)
    cer = edit_distance_from(pairs, reference_collapsed, hypothesis) / max(1, len(reference_collapsed))
    if located_below is not None and cer >= located_below:
        return hypothesis, [], {}
    fates, _ = _fates_from(pairs, reference_collapsed, hypothesis)
    return hypothesis, pairs, fates


def summarize_t2_v2(items: Sequence[dict], greedy: dict[str, str] | None = None,
                    located_below: dict[str, float] | None = None) -> dict[str, dict[str, Any]]:
    """`summarize_t2` split by task, with greedy correctness from version-2 scoring.

    `located_below` maps task to the chance threshold of the T1 cell the greedy
    outputs come from.
    """
    by_task: dict[str, list[dict]] = collections.defaultdict(list)
    for item in items:
        by_task[item["task"]].append(item)
    out = {}
    for task, rows in sorted(by_task.items()):
        threshold = (located_below or {}).get(task)
        out[task] = summarize_t2(
            rows, greedy,
            fates_of=lambda ref, hyp, t=threshold: greedy_fates_v2(ref, hyp, located_below=t))
    return out
