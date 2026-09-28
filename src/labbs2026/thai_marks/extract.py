"""Structure-aware text extraction for T1 scoring, version 2.

Model output and ThaiOCRBench references are not in the same format.
`TYPHOON_CARD` asks for Markdown with HTML tables, `<figure>` blocks that
*describe* an image, and `<page_number>` tags; references are plain text.
Version 1 (`normalize.normalize_text`) stripped this with regexes written
before any output existed. Version 2 parses HTML with a real parser, follows
the prompt's own output contract for `<figure>`, and is applied identically to
reference and hypothesis. No Thai character is altered.

`<figure>` policy: the `TYPHOON_CARD` prompt defines a figure's content as a
description of an image written in Thai, not a transcription, so it is removed.
A model that places transcribed text inside `<figure>` has broken the output
contract; that is measured separately (`keep_figures=True` gives the text with
figure content kept, for the contract-violation diagnostic), never scored as
reading.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_FENCE = re.compile(r"^[ \t]*```[^\n]*$", re.M)
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M)
_WHITESPACE = re.compile(r"\s+")

# Elements whose boundaries separate words: without a separator, the text of
# two adjacent table cells or list items would be glued into one token.
_SEPARATING = frozenset({
    "br", "p", "div", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "figure",
    "figcaption", "section", "article", "header", "footer", "blockquote",
    "pre", "hr", "caption", "page_number",
})


class _TextCollector(HTMLParser):
    def __init__(self, *, keep_figures: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.keep_figures = keep_figures
        self.parts: list[str] = []
        self.figure_depth = 0
        self.figures = 0
        self.unclosed_figures = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "figure":
            self.figure_depth += 1
            self.figures += 1
        if tag in _SEPARATING:
            self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag in _SEPARATING:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SEPARATING:
            self.parts.append(" ")
        if tag == "figure" and self.figure_depth:
            self.figure_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.figure_depth and not self.keep_figures:
            return
        self.parts.append(data)

    def close(self) -> None:
        super().close()
        self.unclosed_figures = self.figure_depth


def extract(text: str, *, keep_figures: bool = False) -> tuple[str, dict[str, int]]:
    """Plain text and structure counts for one string.

    Removes code-fence lines, HTML tags (keeping their text, entities decoded),
    `<figure>` content unless `keep_figures`, Markdown heading markers, `**`,
    `__`, backticks and `$` delimiters (content kept), and `|` separators; then
    collapses whitespace. An unclosed `<figure>` runs to the end of the text,
    which is what the markup says; such cases are counted so they can be
    reported.
    """
    text = _FENCE.sub(" ", text)
    collector = _TextCollector(keep_figures=keep_figures)
    collector.feed(text)
    collector.close()
    text = "".join(collector.parts)
    text = _HEADING.sub("", text)
    for token in ("**", "__", "`", "$"):
        text = text.replace(token, "")
    text = text.replace("|", " ")
    text = _WHITESPACE.sub(" ", text).strip()
    return text, {"figures": collector.figures, "unclosed_figures": collector.unclosed_figures}


def extract_text(text: str, *, keep_figures: bool = False) -> str:
    return extract(text, keep_figures=keep_figures)[0]
