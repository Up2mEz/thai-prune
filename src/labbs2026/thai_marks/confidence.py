"""E1: does Typhoon's own token confidence locate its mark errors?

`docs/stage0/E1_CONFIDENCE_DRAFT.md`. Offline: builds the cases sent to Kaggle
(the model's own greedy outputs) and, from the teacher-forced scores that come
back, labels output grapheme clusters as mark errors and measures how well
low confidence finds them.

Alignment is done on the **raw** output (the text the model actually
generated and was scored on), so token offsets index it directly; markup is
just unaligned output. Clusters inside `<figure>` (an image description by
the model's contract) are left out.
"""

from __future__ import annotations

import random
import re
from typing import Any, Sequence

from labbs2026.thai_marks.attribution import (
    MARKS,
    MIN_ELSEWHERE_CHARS,
    READ_ELSEWHERE_CER,
    reference_lines,
)
from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from
from labbs2026.thai_marks.order_free import LINE_MATCH_CER, MASK
from labbs2026.thai_marks.orthography import COMBINING, CONSONANTS

CONSONANT_SET = frozenset(CONSONANTS)
FIGURE = re.compile(r"<figure>.*?(?:</figure>|\Z)", re.S | re.I)
SEED = 20261004
RESAMPLES = 1000
FLAG_SHARE = 0.05


def build_cases(records: Sequence[dict]) -> list[dict]:
    """E1 cases from T5 `greedy` records, in a fixed order."""
    rows = [r for r in records if r["arm"] == "greedy"]
    return [{"case": f"{r['task']}|{r['prompt_kind']}|{r['id']}", "id": r["id"],
             "task": r["task"], "prompt_kind": r["prompt_kind"], "output": r["raw_output"],
             "reached_max_new_tokens": r["reached_max_new_tokens"]}
            for r in sorted(rows, key=lambda r: (r["task"], r["prompt_kind"], r["id"]))]


def clusters(text: str) -> list[tuple[int, int]]:
    """Grapheme clusters: a consonant with its following combining marks, else one character."""
    out, i = [], 0
    while i < len(text):
        j = i + 1
        if text[i] in CONSONANT_SET:
            while j < len(text) and text[j] in COMBINING:
                j += 1
        out.append((i, j))
        i = j
    return out


def _marks(text: str, start: int) -> str:
    """Marks attached to the character at `start` (empty if it is not a consonant)."""
    if start >= len(text) or text[start] not in CONSONANT_SET:
        return ""
    j, found = start + 1, []
    while j < len(text) and text[j] in COMBINING:
        if text[j] in MARKS:
            found.append(text[j])
        j += 1
    return "".join(found)


def base_of(text: str, i: int) -> int:
    """Step back from a combining mark to the character it sits on.

    Anchored alignment can pair a consonant with a mark at a window start (a
    substitution/insertion tie); the cluster to compare is the mark's own.
    Found 2026-10-04: 19 of 232 E1 mark-error labels sat on a reference mark.
    """
    while i > 0 and text[i] in COMBINING:
        i -= 1
    return i


def _figure_mask(raw: str) -> set[int]:
    return {i for m in FIGURE.finditer(raw) for i in range(m.start(), m.end())}


def aligned_pairs_full_page(reference: str, raw: str,
                            label_cer: float = READ_ELSEWHERE_CER) -> list[tuple]:
    """(reference line, ref index, raw index, line number) for lines matched as in order-free v2.

    Lines are matched and their output claimed exactly as order-free v2 does,
    but only lines read at CER < `label_cer` contribute pairs: E1 concerns
    misreads inside lines the model read (the threshold `attribution` uses for
    "read"); a looser match of a long line across shuffled short fields
    (seen in the smoke, `048AEF1B`) labels correct marks as errors.
    """
    lines = reference_lines(reference)
    masked = list(raw)
    out: list[tuple[str, int, int]] = []
    eligible = sorted((i for i, line in enumerate(lines) if len(line) >= MIN_ELSEWHERE_CHARS),
                      key=lambda i: (-len(lines[i]), i))
    for i in eligible:
        line, current = lines[i], "".join(masked)
        pairs, _, _ = align_anchored(line, current)
        cer = edit_distance_from(pairs, line, current) / len(line)
        if cer >= LINE_MATCH_CER:
            continue
        hyp = [h for _, h in pairs if h is not None]
        if not hyp:
            continue
        if cer < label_cer:
            out += [(line, r, h, i) for r, h in pairs if r is not None and h is not None]
        for h in range(min(hyp), max(hyp) + 1):
            masked[h] = MASK
    return out


def label_clusters(raw: str, pairs: list[tuple[str, int, int]],
                   span: tuple[int, int] | None = None) -> list[dict]:
    """Mark-bearing output clusters with their mark-error label.

    `pairs` are (reference text, ref index, raw index[, line]). Only clusters whose
    base character is aligned (or lies inside `span` for an anchored read,
    then counted as inserted) are labelled; figure content is skipped.
    """
    ref_of = {p[2]: (p[0], p[1]) for p in pairs}
    # Each matched line covers its own stretch of output only (2026-10-04: one
    # span from the first to the last matched line labelled every unmatched
    # line between them as inserted marks; seen in the smoke before the run).
    stretches: dict[Any, list[int]] = {}
    for p in pairs:
        stretches.setdefault(p[3] if len(p) > 3 else 0, []).append(p[2])
    covered = set(ref_of)
    for hs in stretches.values():
        covered |= set(range(min(hs), max(hs) + 1))
    if span is not None:
        covered |= set(range(*span))
    figure = _figure_mask(raw)
    out = []
    for start, end in clusters(raw):
        if start in figure or start not in covered:
            continue
        own = _marks(raw, start)
        if start in ref_of:
            text, r = ref_of[start]
            r = base_of(text, r)
            ref_marks = _marks(text, r)
            consonant_error = text[r] != raw[start]
        else:
            ref_marks, consonant_error = "", True
        if not own and not ref_marks:
            continue
        out.append({"start": start, "end": end, "error": own != ref_marks,
                    "consonant_error": consonant_error})
    return out


def token_offsets(tokenizer, raw: str, token_ids: Sequence[int]) -> list[tuple[int, int]]:
    enc = tokenizer(raw, add_special_tokens=False, return_offsets_mapping=True)
    if list(enc["input_ids"]) != list(token_ids):
        raise ValueError("re-tokenization differs from the scored tokens")
    return [tuple(o) for o in enc["offset_mapping"]]


def cluster_scores(labelled: list[dict], offsets: Sequence[tuple[int, int]],
                   logprob: Sequence[float], entropy: Sequence[float]) -> list[dict]:
    """Attach s_min (−lowest token log-prob) and s_ent (highest entropy) to each cluster."""
    out = []
    for c in labelled:
        hits = [k for k, (s, e) in enumerate(offsets) if s < c["end"] and e > c["start"]]
        if not hits:
            continue
        out.append({**c, "s_min": -min(logprob[k] for k in hits),
                    "s_ent": max(entropy[k] for k in hits)})
    return out


def auroc(scores: Sequence[float], labels: Sequence[bool]) -> float | None:
    """Probability a random error outranks a random correct cluster (ties count half)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    ranked = sorted(set(scores))
    rank_of, rank = {}, 1.0
    counts: dict[float, int] = {}
    for s in scores:
        counts[s] = counts.get(s, 0) + 1
    for s in ranked:
        rank_of[s] = rank + (counts[s] - 1) / 2
        rank += counts[s]
    rank_sum = sum(rank_of[s] for s in pos)
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def recall_at(scores: Sequence[float], labels: Sequence[bool], share: float = FLAG_SHARE) -> float | None:
    """Share of errors among the top `share` of clusters by score (ties by order)."""
    if not any(labels):
        return None
    k = max(1, round(share * len(scores)))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    return sum(labels[i] for i in order) / sum(labels)


def gate(items: list[list[dict]], key: str = "s_min", seed: int = SEED,
         resamples: int = RESAMPLES) -> dict[str, Any]:
    """AUROC and recall@5% over all clusters, with a page-cluster bootstrap."""
    def stats(groups):
        flat = [c for g in groups for c in g]
        s, y = [c[key] for c in flat], [c["error"] for c in flat]
        return auroc(s, y), recall_at(s, y)

    point = stats(items)
    rng = random.Random(seed)
    boots = [stats([items[rng.randrange(len(items))] for _ in items]) for _ in range(resamples)]
    def ci(i):
        values = sorted(b[i] for b in boots if b[i] is not None)
        if not values:
            return None
        return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]
    flat = [c for g in items for c in g]
    return {"auroc": point[0], "auroc_ci": ci(0), "recall_at_5pct": point[1],
            "recall_ci": ci(1), "clusters": len(flat), "errors": sum(c["error"] for c in flat),
            "items": len(items)}
