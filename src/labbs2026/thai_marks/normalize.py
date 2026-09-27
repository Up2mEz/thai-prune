"""Output normalization registered for T1, applied identically to both sides.

Typhoon emits Markdown, HTML tables, `<figure>` descriptions and
`<page_number>` tags; ThaiOCRBench references are plain text, some joined with
` | `. Scoring the raw strings would measure formatting conventions rather than
reading. Every rule removes structure only; no Thai character is ever altered.
"""

from __future__ import annotations

import re

_FIGURE = re.compile(r"<figure>.*?</figure>", re.S | re.I)
_PAGE_NUMBER = re.compile(r"<page_number>(.*?)</page_number>", re.S | re.I)
_BREAK = re.compile(r"<br\s*/?>", re.I)
_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    text = _FIGURE.sub(" ", text)
    text = _PAGE_NUMBER.sub(r" \1 ", text)
    text = _BREAK.sub(" ", text)
    text = _TAG.sub(" ", text)
    text = _HEADING.sub("", text)
    for token in ("**", "__", "`", "$"):
        text = text.replace(token, "")
    text = text.replace("|", " ")
    return _WHITESPACE.sub(" ", text).strip()


def collapse_whitespace(text: str) -> str:
    """The only change made to a reference before T2 site extraction."""
    return _WHITESPACE.sub(" ", text).strip()
