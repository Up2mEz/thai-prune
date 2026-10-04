"""E3: confidence-flagged band re-read with word-level choice (`E3_FLAGGED_BAND_REREAD_DRAFT.md`).

Offline. Inputs are the page read with its E1 token confidences and the band
re-reads with theirs. The reference is never used here.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence

from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from

THAI = re.compile(r"[฀-๿]")
FLAG_THRESHOLD = 0.043
MIN_LINE = 8
POSITION_MARGIN = 0.10
MATCH_CER = 0.4
LENGTH_RATIO = (0.5, 2.0)


def band_spans(rows: int = 3, overlap: float = 0.15) -> list[tuple[float, float]]:
    """Vertical spans of the bands as fractions of page height (`tiling` geometry)."""
    from labbs2026.thai_marks.tiling import tile_boxes

    height = 100_000
    return [(t.box[1] / height, t.box[3] / height)
            for t in tile_boxes((1, height), rows=rows, cols=1, overlap=overlap)]


def choose_bands(position: float, spans: Sequence[tuple[float, float]],
                 margin: float = POSITION_MARGIN) -> list[int]:
    """Bands whose span meets [position − margin, position + margin]."""
    lo, hi = position - margin, position + margin
    return [i for i, (a, b) in enumerate(spans) if a <= hi and b >= lo]


def _min_logprob(offsets: Sequence[tuple[int, int]], logprob: Sequence[float],
                 start: int, end: int) -> float | None:
    hits = [logprob[k] for k, (a, b) in enumerate(offsets) if a < end and b > start]
    return min(hits) if hits else None


def flagged_lines(raw: str, offsets: Sequence[tuple[int, int]], logprob: Sequence[float],
                  cluster_spans: Sequence[tuple[int, int]],
                  threshold: float = FLAG_THRESHOLD) -> list[tuple[int, int, list[int]]]:
    """(line start, line end, flagged cluster starts) for lines of ≥ MIN_LINE characters."""
    by_line: dict[tuple[int, int], list[int]] = {}
    for start, end in cluster_spans:
        lp = _min_logprob(offsets, logprob, start, end)
        if lp is None or -lp < threshold:
            continue
        line_start = raw.rfind("\n", 0, start) + 1
        line_end = raw.find("\n", end)
        line_end = len(raw) if line_end == -1 else line_end
        if line_end - line_start >= MIN_LINE:
            by_line.setdefault((line_start, line_end), []).append(start)
    return [(a, b, starts) for (a, b), starts in sorted(by_line.items())]


def _words(segment: Callable[[str], list[str]], text: str) -> list[tuple[int, int]]:
    spans, cursor = [], 0
    for word in segment(text):
        if word.strip():
            spans.append((cursor, cursor + len(word)))
        cursor += len(word)
    return spans


def word_edits(raw: str, line: tuple[int, int, list[int]],
               page_offsets: Sequence[tuple[int, int]], page_logprob: Sequence[float],
               bands: Sequence[tuple[str, Sequence[tuple[int, int]], Sequence[float]]],
               segment: Callable[[str], list[str]]) -> list[tuple[int, int, str]]:
    """Word replacements for one flagged line, from the best-matching band read.

    `bands`: (band raw output, its token offsets, its token log-probabilities)
    for the bands chosen for this line.
    """
    line_start, line_end, flagged = line
    text = raw[line_start:line_end]
    best = None
    for band_raw, band_offsets, band_logprob in bands:
        if not band_raw:
            continue
        pairs, _, _ = align_anchored(text, band_raw)
        cer = edit_distance_from(pairs, text, band_raw) / len(text)
        if cer < MATCH_CER and (best is None or cer < best[0]):
            best = (cer, pairs, band_raw, band_offsets, band_logprob)
    if best is None:
        return []
    _, pairs, band_raw, band_offsets, band_logprob = best
    to_band = {r: h for r, h in pairs if r is not None and h is not None}
    edits = []
    for ws, we in _words(segment, text):
        if not any(line_start + ws <= f < line_start + we for f in flagged):
            continue
        hs = [to_band[i] for i in range(ws, we) if i in to_band]
        if not hs:
            continue
        b0, b1 = min(hs), max(hs) + 1
        band_line_start = band_raw.rfind("\n", 0, b0) + 1
        band_line_end = band_raw.find("\n", b1 - 1)
        band_line_end = len(band_raw) if band_line_end == -1 else band_line_end
        band_line = band_raw[band_line_start:band_line_end]
        for a, b in _words(segment, band_line):  # widen to band word boundaries
            a, b = a + band_line_start, b + band_line_start
            if a < b1 and b > b0:
                b0, b1 = min(b0, a), max(b1, b)
        old, new = text[ws:we], band_raw[b0:b1]
        if new == old or not THAI.search(new):
            continue
        if not LENGTH_RATIO[0] <= len(new) / len(old) <= LENGTH_RATIO[1]:
            continue
        page_conf = _min_logprob(page_offsets, page_logprob, line_start + ws, line_start + we)
        band_conf = _min_logprob(band_offsets, band_logprob, b0, b1)
        if page_conf is None or band_conf is None or band_conf <= page_conf:
            continue
        edits.append((line_start + ws, line_start + we, new))
    return edits
