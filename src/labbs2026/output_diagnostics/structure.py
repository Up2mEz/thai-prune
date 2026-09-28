"""Structure-aware normalization and loop detection (sensitivity measures).

Found on this project's own smoke outputs (2026-09-28), all under T1's
registered normalization:

1. The base model wraps whole transcriptions — tables included — in
   `<figure>…</figure>`. T1 drops every figure block, because for Typhoon a
   figure holds a *description* of a picture, not text on the page. For the
   base this deletes the reading itself: 320 Thai characters inside figures
   against 312 in the reference became an empty hypothesis and CER 1.0.
2. It also invents table tags (`<row>`, `<cell>`) that T1 removes correctly,
   but only because its tag rule is generic.
3. Line-initial list markers differ in kind (`*` from Typhoon, `-` in
   references); T1 removes `**` but not a single `*`.
4. Loops whose period is longer than 200 characters escape T1's repetition
   rule (a 20-character substring three times in the last 200 characters), so
   a paragraph repeated until `max_new_tokens` is not flagged.

`structural_normalize` keeps figure content that carries a table or text
structure and drops figures that are only picture descriptions; it strips
list markers on both sides. `loop_period` finds long-period loops; `deloop`
cuts the hypothesis at the start of the second repetition. Both sides of every
comparison go through the same function.
"""

from __future__ import annotations

import re

from labbs2026.thai_marks.normalize import normalize_text

_FIGURE = re.compile(r"<figure>(.*?)</figure>", re.S | re.I)
_TABLE_LIKE = re.compile(r"<(table|tr|td|th|row|cell|caption)\b", re.I)
_CAPTION = re.compile(r"<caption>.*?</caption>", re.S | re.I)
_LIST_MARKER = re.compile(r"^[ \t]*(?:[-*+•▪◦]|\d{1,3}[.)])[ \t]+", re.M)
_CELL_END = re.compile(r"</(td|th|cell)>", re.I)


def _unwrap_figure(match: re.Match) -> str:
    inner = match.group(1)
    if not _TABLE_LIKE.search(inner):
        return " "                      # a picture description: dropped, as in T1
    inner = _CAPTION.sub(" ", inner)    # captions repeat the first cell
    return " " + _CELL_END.sub(" ", inner) + " "


def structural_normalize(text: str) -> str:
    """T1's normalization after unwrapping text-bearing figures and list markers."""
    text = _FIGURE.sub(_unwrap_figure, text)
    text = _LIST_MARKER.sub("", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", " ", text)  # a lone '*' that is not bold markup
    return normalize_text(text)


def loop_period(text: str, *, min_period: int = 20, max_period: int = 4000,
                min_repeats: int = 2) -> tuple[int, int] | None:
    """(period, start) of a loop running to the end of `text`, or None.

    A loop is a block of `period` characters repeated back to back at least
    `min_repeats` times up to the end (a truncated last copy allowed). The
    shortest such period is returned; `start` is where the first copy begins.
    """
    n = len(text)
    for period in range(min_period, min(max_period, n // min_repeats) + 1):
        # compare the tail against itself shifted by `period`
        j = n - 1
        while j - period >= 0 and text[j] == text[j - period]:
            j -= 1
        run = n - 1 - j                  # characters matching their copy one period earlier
        if run >= period * (min_repeats - 1):
            return period, j + 1 - period
    return None


def deloop(text: str, **kwargs) -> str:
    """`text` cut at the start of the second copy of a trailing loop, if any."""
    found = loop_period(text, **kwargs)
    if found is None:
        return text
    period, start = found
    return text[: start + period]
