"""Overlapping tile grid for P-ZOOM (`docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`).

A page is cut into `rows` x `cols` tiles that overlap their neighbours by
`overlap` of a tile's side, so a line that straddles a cut is whole in at
least one tile. Each tile is then read like a page: `runtime.resize_policy`
scales its long side to the card's 1800 px, so the text is larger, in visual
tokens, than when the whole page is read. This is an input-resolution change:
the number of visual tokens per read stays about the same, but each read sees
a smaller region.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from labbs2026.thai_marks.runtime import TYPHOON_CARD_MAX_SIDE, TYPHOON_CARD_TRIGGER


@dataclass(frozen=True)
class Tile:
    index: int  # row-major
    row: int
    col: int
    box: tuple[int, int, int, int]  # left, top, right, bottom, in source pixels

    @property
    def size(self) -> tuple[int, int]:
        left, top, right, bottom = self.box
        return right - left, bottom - top


def _spans(length: int, count: int, overlap: float) -> list[tuple[int, int]]:
    """`count` equal spans covering [0, length) whose neighbours share `overlap` of a span."""
    if count == 1:
        return [(0, length)]
    side = min(length, math.ceil(length / (count - (count - 1) * overlap)))
    starts = [round(i * (length - side) / (count - 1)) for i in range(count)]
    return [(start, start + side) for start in starts]


def tile_boxes(size: tuple[int, int], rows: int = 2, cols: int = 2,
               overlap: float = 0.15) -> list[Tile]:
    """Tiles of an image of `size` = (width, height), in row-major order.

    The union of the tiles is the whole image; neighbouring tiles overlap by
    `overlap` of a tile's side (to within one pixel of rounding).
    """
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be at least 1")
    if not 0 <= overlap < 1:
        raise ValueError("overlap must lie in [0, 1)")
    width, height = size
    if width < 1 or height < 1:
        raise ValueError("image size must be positive")
    xs = _spans(width, cols, overlap)
    ys = _spans(height, rows, overlap)
    return [Tile(index=r * cols + c, row=r, col=c, box=(x0, y0, x1, y1))
            for r, (y0, y1) in enumerate(ys) for c, (x0, x1) in enumerate(xs)]


def crop_tiles(image, rows: int = 2, cols: int = 2, overlap: float = 0.15) -> list[tuple[Tile, object]]:
    """Tiles of a PIL image, cropped from the source pixels (no resampling yet)."""
    return [(tile, image.crop(tile.box)) for tile in tile_boxes(image.size, rows, cols, overlap)]


def read_scale(size: tuple[int, int]) -> float:
    """Pixel scale `runtime.resize_policy` applies to an image of `size`."""
    width, height = size
    if width > TYPHOON_CARD_TRIGGER or height > TYPHOON_CARD_TRIGGER:
        return TYPHOON_CARD_MAX_SIDE / float(max(width, height))
    return 1.0


def zoom_factor(page_size: tuple[int, int], tile_size: tuple[int, int]) -> float:
    """How much larger a source pixel is when the tile is read than when the page is.

    Both are read through `resize_policy`; the factor is the ratio of their scales.
    """
    return read_scale(tile_size) / read_scale(page_size)
