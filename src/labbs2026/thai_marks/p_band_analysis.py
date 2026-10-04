"""P-BAND pilot: Typhoon read as three full-width bands (`docs/stage0/P_BAND_PILOT_DRAFT.md`).

Offline scoring, fixed before any new read was made. For each Full-page OCR calibration page
there are three reads of one page: the stored T1 whole-page read (`TYPHOON_CARD`) and the three
band reads (`bands100`: full-width bands, 15% overlap, read at page scale). Three text variants are
built from them and scored with order-free v2 mark precision/recall/F1
(`order_free.mark_counts(..., residual=True)`), which charges surplus text:

- `whole`: the stored whole-page read;
- `bands_concat`: the three band outputs one after another, nothing removed (shows what the
  overlap duplicates cost);
- `bands_dedup`: the same, with the lines that sit in the overlap removed from the later band.

Headline contrast: `bands_dedup` against `whole`, the variant that costs about what one more half
read costs. Nothing is adopted by this pilot; see `reading`.
"""

from __future__ import annotations

import collections
import math
import re
import statistics
from typing import Any, Sequence

from labbs2026.thai_marks.attribution import MIN_ELSEWHERE_CHARS, find_elsewhere
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.order_free import mark_counts, prf
from labbs2026.thai_marks.t5_analysis import paired_bootstrap_delta_f1

VARIANTS = ("whole", "bands_concat", "bands_dedup")
HEADLINE = "bands_dedup"
CONTROL = "whole"
# Judgements, not derived from data (draft §4). The ceiling is small: recovering the 31 marks
# P-ZOOM-3 found on 21 pages is +0.19 points of recall over 69 pages.
HELP_DELTA = 0.002          # 0.2 points of micro F1
PRECISION_FLOOR = -0.005    # the variant may lose at most 0.5 points of precision
OVERLAP_SHARE = 0.3         # lines compared at a band's head and the previous band's tail
MIN_OVERLAP_LINES = 3
BOOTSTRAP_SEED = 20261004

_FIGURE_BLOCK = re.compile(r"<figure\b[^>]*>.*?(?:</figure>|\Z)", re.DOTALL | re.IGNORECASE)


def output_lines(raw: str) -> list[str]:
    """Non-empty extracted lines of one read, with `<figure>` blocks removed first.

    Figure content is dropped as in `extract` (it is the prompt's own contract), but before the
    split, so a multi-line figure does not leak its inner lines.
    """
    text = _FIGURE_BLOCK.sub("\n", raw)
    return [line for line in (extract_text(part) for part in text.split("\n")) if line]


def concat_text(band_raws: Sequence[str]) -> str:
    return "\n".join(line for raw in band_raws for line in output_lines(raw))


def dedup_text(band_raws: Sequence[str]) -> str:
    """Bands one after another; a line in the head of a band that the tail of the previous band
    already holds (`find_elsewhere`: 8+ characters, CER < 0.2) is dropped.

    Head and tail are the first / last `OVERLAP_SHARE` of the band's lines (at least
    `MIN_OVERLAP_LINES`), so a line repeated elsewhere on the page is not mistaken for overlap.
    """
    bands = [output_lines(raw) for raw in band_raws]
    out: list[str] = []
    for k, lines in enumerate(bands):
        head = max(MIN_OVERLAP_LINES, math.ceil(OVERLAP_SHARE * len(lines)))
        tail_text = ""
        if k:
            previous = bands[k - 1]
            tail = max(MIN_OVERLAP_LINES, math.ceil(OVERLAP_SHARE * len(previous)))
            tail_text = " ".join(previous[-tail:])
        for position, line in enumerate(lines):
            if (k and position < head and len(line) >= MIN_ELSEWHERE_CHARS
                    and find_elsewhere(line, tail_text)[0] is not None):
                continue
            out.append(line)
    return "\n".join(out)


def variant_texts(whole_raw: str, band_raws: Sequence[str]) -> dict[str, str]:
    return {"whole": "\n".join(output_lines(whole_raw)), "bands_concat": concat_text(band_raws),
            "bands_dedup": dedup_text(band_raws)}


def reading(delta: float, ci_low: float, ci_high: float, delta_precision: float) -> str:
    """The registered label for one variant against `whole` (micro F1, paired over pages).

    `not_distinguishable` is inconclusive: with 69 pages and a ceiling of a few tenths of a point
    it is the expected outcome for a real but small effect.
    """
    if delta >= HELP_DELTA and ci_low > 0 and delta_precision >= PRECISION_FLOOR:
        return "helps"
    if delta <= -HELP_DELTA and ci_high < 0:
        return "hurts"
    return "not_distinguishable"


def analyze(pages: Sequence[dict], subgroups: dict[str, set] | None = None) -> dict[str, Any]:
    """Every registered number. `pages`: dicts with `id`, `category`, `reference`, `whole_raw`,
    `band_raws` (in band order), and the cost fields `whole_tokens`, `whole_seconds`,
    `band_tokens`, `band_seconds`, `whole_looped`, `band_looped`. `subgroups` (name -> page ids) are
    reported as micro precision/recall/F1 per variant, without a label."""
    counts: dict[str, list[dict]] = {v: [] for v in VARIANTS}
    for page in pages:
        texts = variant_texts(page["whole_raw"], page["band_raws"])
        for v in VARIANTS:
            counts[v].append(mark_counts(page["reference"], texts[v], residual=True))
    summary = {v: prf(counts[v]) for v in VARIANTS}
    contrasts = {}
    for v in VARIANTS:
        if v == CONTROL:
            continue
        boot = paired_bootstrap_delta_f1(counts[v], counts[CONTROL], seed=BOOTSTRAP_SEED)
        d_precision = (summary[v]["precision"] or 0.0) - (summary[CONTROL]["precision"] or 0.0)
        contrasts[v] = {**boot, "delta_precision": d_precision,
                        "delta_recall": (summary[v]["recall"] or 0.0) - (summary[CONTROL]["recall"] or 0.0),
                        "label": reading(boot["delta"], boot["ci_low"], boot["ci_high"], d_precision)}
    ids = [p["id"] for p in pages]
    per_page = []
    for i, page in enumerate(pages):
        base = counts[CONTROL][i]
        row = {"id": page["id"], "category": page["category"], "reference_marks": base["reference_marks"],
               "whole_correct": base["correct"]}
        for v in VARIANTS[1:]:
            row[f"{v}_correct"] = counts[v][i]["correct"]
            row[f"{v}_output_marks"] = counts[v][i]["output_marks"]
        row["whole_output_marks"] = base["output_marks"]
        per_page.append(row)
    delta_marks = [r["bands_dedup_correct"] - r["whole_correct"] for r in per_page]
    by_category: dict[str, dict] = {}
    for category in sorted({p["category"] for p in pages}):
        idx = [i for i, p in enumerate(pages) if p["category"] == category]
        by_category[category] = {
            "pages": len(idx),
            **{v: {k: prf([counts[v][i] for i in idx])[k] for k in ("recall", "precision", "f1")}
               for v in VARIANTS}}
    group_report = {}
    for name, members in (subgroups or {}).items():
        idx = [i for i, p in enumerate(pages) if p["id"] in members]
        if idx:
            group_report[name] = {"pages": len(idx), **{
                v: {k: prf([counts[v][i] for i in idx])[k] for k in ("recall", "precision", "f1")}
                for v in VARIANTS}}
    whole_tokens = sum(p["whole_tokens"] for p in pages)
    band_tokens = sum(p["band_tokens"] for p in pages)
    whole_seconds = sum(p["whole_seconds"] for p in pages)
    band_seconds = sum(p["band_seconds"] for p in pages)
    return {
        "pages": len(pages),
        "micro": summary,
        "contrasts_vs_whole": contrasts,
        "headline": {"variant": HEADLINE, **contrasts[HEADLINE]},
        "pages_better_equal_worse": [sum(d > 0 for d in delta_marks), sum(d == 0 for d in delta_marks),
                                     sum(d < 0 for d in delta_marks)],
        "worst_pages_marks": sorted(((d, r["id"]) for d, r in zip(delta_marks, per_page)))[:5],
        "best_pages_marks": sorted(((d, r["id"]) for d, r in zip(delta_marks, per_page)), reverse=True)[:5],
        "ci_halfwidth_headline": (contrasts[HEADLINE]["ci_high"] - contrasts[HEADLINE]["ci_low"]) / 2,
        "cost": {"generated_tokens": {"whole": whole_tokens, "bands": band_tokens,
                                      "ratio": band_tokens / whole_tokens if whole_tokens else None},
                 "generation_seconds": {"whole": whole_seconds, "bands": band_seconds,
                                        "ratio": band_seconds / whole_seconds if whole_seconds else None},
                 "looped_reads": {"whole": sum(p["whole_looped"] for p in pages),
                                  "bands": sum(p["band_looped"] for p in pages)}},
        "by_category": by_category, "subgroups": group_report,
        "per_page": per_page,
        "thresholds": {"help_delta": HELP_DELTA, "precision_floor": PRECISION_FLOOR,
                       "overlap_share": OVERLAP_SHARE, "min_overlap_lines": MIN_OVERLAP_LINES,
                       "bootstrap_seed": BOOTSTRAP_SEED},
        "page_ids": ids,
    }


def assemble_pages(whole: dict[str, dict], band_records: Sequence[dict], page_ids: Sequence[str],
                   bands: int = 3) -> list[dict]:
    """Join the stored whole-page reads with the band reads; raises on any missing or duplicate band."""
    by_page: dict[str, dict[int, dict]] = collections.defaultdict(dict)
    for r in band_records:
        if r["tile"] in by_page[r["id"]]:
            raise ValueError(f"duplicate band record {r['id']} tile {r['tile']}")
        by_page[r["id"]][r["tile"]] = r
    extra = set(by_page) - set(page_ids)
    if extra:
        raise ValueError(f"band records for pages outside the list: {sorted(extra)[:5]}")
    pages = []
    for page_id in page_ids:
        got = by_page.get(page_id, {})
        if sorted(got) != list(range(bands)):
            raise ValueError(f"page {page_id}: bands {sorted(got)}, expected 0..{bands - 1}")
        w = whole[page_id]
        reads = [got[t] for t in range(bands)]
        pages.append({
            "id": page_id, "category": w["category"], "reference": w["reference"],
            "whole_raw": w["raw_output"], "band_raws": [r["raw_output"] for r in reads],
            "whole_tokens": w["generated_tokens"], "whole_seconds": w["seconds_generate"],
            "whole_looped": bool(w["reached_max_new_tokens"]),
            "band_tokens": sum(r["generated_tokens"] for r in reads),
            "band_seconds": sum(r["seconds_generate"] for r in reads),
            "band_looped": sum(bool(r["reached_max_new_tokens"]) for r in reads)})
    return pages


def median_or_none(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None
