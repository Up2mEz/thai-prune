"""Markup audit of raw model outputs — run before any result is reported.

For every output: which structural markup it carries (HTML tags by name,
`<figure>` blocks, Markdown headings / list markers / bold / pipe tables / code
fences, LaTeX commands, HTML entities), and how many Thai characters each
normalization removes — T1's registered `normalize_text` (drops figure
blocks) and the structure-aware `structural_normalize` (keeps text-bearing
figures). A large Thai loss under T1 but not under the structure-aware rule
means a score is being decided by format, not reading
(`docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md` F1).
"""

from __future__ import annotations

import collections
import re
from typing import Any, Iterable

from labbs2026.output_diagnostics.structure import structural_normalize
from labbs2026.thai_marks.normalize import normalize_text

_TAG = re.compile(r"</?([a-zA-Z][a-zA-Z0-9_]*)\b[^>]*>")
_FIGURE = re.compile(r"<figure>(.*?)</figure>", re.S | re.I)
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M)
_LIST = re.compile(r"^[ \t]*(?:[-*+•]|\d{1,3}[.)])[ \t]+", re.M)
_BOLD = re.compile(r"\*\*|__")
_PIPE_ROW = re.compile(r"^[ \t]*\|.*\|[ \t]*$", re.M)
_FENCE = re.compile(r"^[ \t]*```", re.M)
_LATEX = re.compile(r"\\[a-zA-Z]+|\$[^$\n]+\$")
_ENTITY = re.compile(r"&(?:[a-zA-Z]+|#\d+);")
_THAI = re.compile(r"[\u0E00-\u0E7F]")


def audit(text: str) -> dict[str, Any]:
    figures = _FIGURE.findall(text)
    thai_raw = len(_THAI.findall(text))
    return {
        "tags": collections.Counter(t.lower() for t in _TAG.findall(text)),
        "figure_blocks": len(figures),
        "thai_inside_figures": sum(len(_THAI.findall(f)) for f in figures),
        "headings": len(_HEADING.findall(text)),
        "list_markers": len(_LIST.findall(text)),
        "bold": len(_BOLD.findall(text)),
        "pipe_rows": len(_PIPE_ROW.findall(text)),
        "code_fences": len(_FENCE.findall(text)),
        "latex": len(_LATEX.findall(text)),
        "entities": len(_ENTITY.findall(text)),
        "thai_raw": thai_raw,
        "thai_lost_t1": max(0, thai_raw - len(_THAI.findall(normalize_text(text)))),
        "thai_lost_structural": max(0, thai_raw - len(_THAI.findall(structural_normalize(text)))),
    }


def summarize(outputs: Iterable[str]) -> dict[str, Any]:
    """Aggregate audit for a set of outputs (one model x arm)."""
    rows = [audit(t) for t in outputs]
    n = len(rows)
    tags = collections.Counter()
    for r in rows:
        tags.update(r["tags"])
    has = lambda key: sum(1 for r in rows if r[key])  # noqa: E731
    thai_raw = sum(r["thai_raw"] for r in rows)
    return {
        "outputs": n,
        "with_any_tag": sum(1 for r in rows if r["tags"]),
        "top_tags": dict(tags.most_common(8)),
        "with_figure": has("figure_blocks"),
        "with_headings": has("headings"),
        "with_list_markers": has("list_markers"),
        "with_bold": has("bold"),
        "with_pipe_table": has("pipe_rows"),
        "with_code_fence": has("code_fences"),
        "with_latex": has("latex"),
        "with_entities": has("entities"),
        "thai_raw": thai_raw,
        "thai_lost_t1_share": (sum(r["thai_lost_t1"] for r in rows) / thai_raw) if thai_raw else 0.0,
        "thai_lost_structural_share": (sum(r["thai_lost_structural"] for r in rows) / thai_raw) if thai_raw else 0.0,
        "outputs_losing_over_10pct_thai_t1": sum(
            1 for r in rows if r["thai_raw"] and r["thai_lost_t1"] / r["thai_raw"] > 0.10),
    }
