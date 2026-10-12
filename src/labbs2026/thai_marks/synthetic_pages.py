"""Synthetic Thai pages with known lines and boxes (E5, `docs/stage0/E5_SYNTHETIC_OMISSION_DRAFT.md`).

A page is a white canvas of lines of random Thai words, rendered with matplotlib >= 3.11, whose
text layout shapes stacked vowels and tone marks (Pillow without Raqm does not). Everything is
deterministic given a seed. This is a controlled probe, not real-world evidence: the words come
from a dictionary list and the lines carry no meaning.

Per page, the module also gives each line's tight box, so a line can be read in the page, alone
in a tight crop, or alone on a page-sized canvas at its place (the `masked` arm).
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass

PAGE = (1240, 1754)  # A4 at 150 dpi
MARGIN_X = 100
MARGIN_TOP = 110
LINE_PITCH = 1.6  # line height as a multiple of the font size in pixels
WORDS_PER_GROUP = (2, 4)
MIN_WORD, MAX_WORD = 2, 8
MARK_CODES = {0x0E31} | set(range(0x0E34, 0x0E3A)) | set(range(0x0E47, 0x0E4C))  # upper/lower vowels, tone marks


@dataclass(frozen=True)
class Line:
    text: str
    box: tuple[int, int, int, int]  # left, top, right, bottom, in page pixels


def vocabulary() -> list[str]:
    """Dictionary words of 2-8 Thai characters (consonants, vowels and marks only), sorted."""
    from pythainlp.corpus import thai_words

    allowed = (set(range(0x0E01, 0x0E2F)) | set(range(0x0E30, 0x0E3A)) | set(range(0x0E40, 0x0E46))
               | set(range(0x0E47, 0x0E4C)))
    words = {w for w in thai_words()
             if MIN_WORD <= len(w) <= MAX_WORD and all(ord(c) in allowed for c in w)}
    return sorted(words)


def n_marks(text: str) -> int:
    return sum(ord(c) in MARK_CODES for c in text)


def compose_lines(seed: int, count: int, font_px: int, vocab: list[str], measure) -> list[str]:
    """`count` lines, each filled with word groups until `measure(text)` would pass the page's
    text width. Every line holds at least 4 marks so that no line is unscoreable."""
    rng = random.Random(seed)
    limit = PAGE[0] - 2 * MARGIN_X
    lines: list[str] = []
    while len(lines) < count:
        text = ""
        while True:
            group = "".join(rng.choice(vocab) for _ in range(rng.randint(*WORDS_PER_GROUP)))
            candidate = (text + " " + group).strip()
            if measure(candidate, font_px) > limit:
                break
            text = candidate
        if n_marks(text) >= 4:
            lines.append(text)
    return lines


def render_page(lines: list[str], font_px: int, font_path: str):
    """(PIL image, [Line]) for the given lines; the image is PAGE pixels, RGB."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    from PIL import Image

    fm.fontManager.addfont(font_path)
    family = fm.FontProperties(fname=font_path).get_name()
    dpi = 100
    fig = plt.figure(figsize=(PAGE[0] / dpi, PAGE[1] / dpi), dpi=dpi)
    fig.patch.set_facecolor("white")
    size_pt = font_px * 72 / dpi
    pitch = round(font_px * LINE_PITCH)
    artists = []
    for i, text in enumerate(lines):
        y = PAGE[1] - (MARGIN_TOP + i * pitch)
        artists.append(fig.text(MARGIN_X / PAGE[0], y / PAGE[1], text, fontname=family,
                                fontsize=size_pt, va="top", ha="left", color="black"))
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    out_lines = []
    for text, art in zip(lines, artists):
        bb = art.get_window_extent(renderer)
        out_lines.append(Line(text, (round(bb.x0), round(PAGE[1] - bb.y1), round(bb.x1),
                                     round(PAGE[1] - bb.y0))))
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB"), out_lines


def measurer(font_path: str):
    """`measure(text, font_px)` in pixels, with the same engine that renders the page."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm

    fm.fontManager.addfont(font_path)
    family = fm.FontProperties(fname=font_path).get_name()
    fig = plt.figure(figsize=(PAGE[0] / 100, 1), dpi=100)
    renderer = fig.canvas.get_renderer()

    def measure(text: str, font_px: int) -> float:
        art = fig.text(0, 0.5, text, fontname=family, fontsize=font_px * 72 / 100)
        width = art.get_window_extent(renderer).width
        art.remove()
        return width

    return measure


def line_views(page, line: Line, pad: int = 14):
    """The tight crop of a line (with `pad` px around it) and the page-sized canvas holding only it."""
    from PIL import Image

    left, top, right, bottom = line.box
    box = (max(0, left - pad), max(0, top - pad), min(page.width, right + pad), min(page.height, bottom + pad))
    crop = page.crop(box)
    canvas = Image.new("RGB", page.size, "white")
    canvas.paste(crop, box[:2])
    return crop, canvas
