"""Exploratory check of SPEC_DECODE_S1 against the markup in its outputs (not registered).

`TYPHOON_CARD` asks for HTML tables, `<figure>` picture descriptions and
`<page_number>` tags. Three parts of the S1 analysis read raw output text and
can therefore be decided by markup rather than by the page text:

1. the headline/degenerate split uses T1's `is_repetitive` on the raw text
   (`analysis.item_rows`); a normal table ending in `</td></tr><tr><td>`
   repeats 20-character spans of tags;
2. the divergence-kind base rate (results §4) counted every REF token,
   HTML tags included;
3. the drift of diverged outputs was an edit distance on raw text.

This module recomputes each on text, so the sensitivity can be reported next
to the registered numbers. It never changes the registered analysis.
"""

from __future__ import annotations

import re
import statistics
from typing import Any, Callable, Iterable, Sequence

from labbs2026.output_diagnostics.distance import levenshtein
from labbs2026.output_diagnostics.structure import loop_period, structural_normalize
from labbs2026.thai_marks.decompose import is_repetitive

_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9_]*\b[^>]*>")
_TRAILING_PARTIAL_TAG = re.compile(r"<[^<>]*$")


def strip_tags(text: str) -> str:
    """Replace every complete HTML-like tag by a space."""
    return _TAG.sub(" ", text)


def cut_partial_tag(text: str) -> str:
    """Drop a tag cut off by `max_new_tokens` at the very end (e.g. `<page`).

    Normalization only removes complete tags, so a truncated one stays in the
    text and breaks `loop_period`'s run-to-the-end test.
    """
    return _TRAILING_PARTIAL_TAG.sub("", text).rstrip()


TEXT_FORMS: dict[str, Callable[[str], str]] = {
    "registered_raw": lambda t: t,
    "structural_text": structural_normalize,
    "tags_stripped": strip_tags,
}


def headline_flags(ref: dict, form: Callable[[str], str]) -> bool:
    """The registered headline rule (`analysis.item_rows`), applied to `form(text)`."""
    return not ref["reached_max_new_tokens"] and not is_repetitive(form(ref["text"]))


def with_population(rows: Sequence[dict], refs: dict[str, dict], form: Callable[[str], str]) -> list[dict]:
    """Copies of `item_rows` rows whose headline flag uses `form`; loop-aware equals headline."""
    out = []
    for r in rows:
        r2 = dict(r)
        r2["headline"] = headline_flags(refs[r["id"]], form)
        r2["headline_loop_aware"] = r2["headline"]
        out.append(r2)
    return out


def loops_at_budget(refs: Iterable[dict]) -> dict[str, int]:
    """Among REF outputs that reach `max_new_tokens`: loops found in raw text, in
    structure-aware text, and in structure-aware text after a cut-off tag is dropped."""
    n = raw = text = text_cut = 0
    for ref in refs:
        if not ref["reached_max_new_tokens"]:
            continue
        n += 1
        s = structural_normalize(ref["text"])
        raw += loop_period(ref["text"]) is not None
        text += loop_period(s) is not None
        text_cut += loop_period(cut_partial_tag(s)) is not None
    return {"reached_max": n, "loop_raw": raw, "loop_structural": text, "loop_structural_cut_tag": text_cut}


def drift(ref_text: str, arm_text: str, form: Callable[[str], str] = lambda t: t) -> float:
    """Character edit distance between REF and arm after `form`, over REF's length."""
    a, b = form(ref_text), form(arm_text)
    return levenshtein(a, b) / max(1, len(a))


def quantile_linear(values: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile (numpy's default), stated so tails are reproducible."""
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def thai_only_mark_share(kind_shares: dict[str, float]) -> float:
    """Share of mark-bearing tokens among Thai tokens, from shares over all tokens
    (`has_thai_mark`, `thai_no_mark`, `other`)."""
    thai = kind_shares["has_thai_mark"] + kind_shares["thai_no_mark"]
    return kind_shares["has_thai_mark"] / thai if thai else 0.0


def divergence_thai_counts(kind_shares: dict[str, float], n: int) -> dict[str, Any]:
    """Counts of divergences by REF token kind, and the mark share among the Thai ones."""
    counts = {k: round(kind_shares.get(k, 0.0) * n) for k in ("has_thai_mark", "thai_no_mark", "other")}
    thai = counts["has_thai_mark"] + counts["thai_no_mark"]
    return {**counts, "thai": thai, "mark_share_thai": counts["has_thai_mark"] / thai if thai else None}


def median_or_none(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None
