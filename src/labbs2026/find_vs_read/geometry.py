"""Page preparation, box parsing and grid-aligned crops for FIND_VS_READ_F1.

The crop must differ from the whole page only in *not having to find* the
text. So both arms start from the same prepared page: T1's image policy, then
the processor's own size rule (`smart_resize`, factor 32 = 16-px patch x 2x2
merge) applied here, once, with the processor's resampling. A page already at
that size passes through the processor unchanged, so the crop's pixels are the
page's pixels. The crop rectangle is snapped outward to the 32-px grid, so
every 16-px patch and every merged token covers the same glyph pixels as in
the whole page. A crop below the processor's pixel floor is padded with white,
never enlarged, so magnification never changes (the TEMS lesson).
"""

from __future__ import annotations

import math
import re

from PIL import Image, ImageDraw

FACTOR = 32               # patch 16 x merge 2, both pinned processors
MIN_PIXELS = 65_536       # processor `size.shortest_edge`, both pinned processors
MAX_PIXELS = 16_777_216   # processor `size.longest_edge`
RESAMPLE = Image.Resampling.BICUBIC  # processor `resample` = 3

_BOX = re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]")


def parse_box(question: str) -> tuple[float, float, float, float]:
    """The item's box `[x1, y1, x2, y2]` in 0-1000 coordinates (checked on real items)."""
    found = _BOX.findall(question)
    if len(found) != 1:
        raise ValueError(f"expected exactly one box, found {len(found)}")
    x1, y1, x2, y2 = (float(v) for v in found[0])
    if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
        raise ValueError(f"box out of range or empty: {(x1, y1, x2, y2)}")
    return x1, y1, x2, y2


def processor_size(width: int, height: int) -> tuple[int, int]:
    """(width, height) the pinned processors resize an image to."""
    from transformers.models.qwen2_vl.image_processing_qwen2_vl import smart_resize

    h, w = smart_resize(height, width, factor=FACTOR, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)
    return w, h


def prepare_page(image: Image.Image) -> Image.Image:
    """T1's image policy, then the processor's size rule, applied once here."""
    from labbs2026.thai_marks.runtime import resize_policy

    page = resize_policy(image.convert("RGB"))
    size = processor_size(*page.size)
    return page if page.size == size else page.resize(size, RESAMPLE)


def crop_rect(box: tuple[float, float, float, float], size: tuple[int, int], *,
              margin: float) -> tuple[int, int, int, int]:
    """Pixel rectangle of `box` on a page of `size`, widened by `margin` x box height
    on every side (Thai marks sit above and below tight boxes), snapped outward to
    the 32-px grid and clipped to the page."""
    width, height = size
    x1, y1, x2, y2 = (box[0] * width / 1000, box[1] * height / 1000,
                      box[2] * width / 1000, box[3] * height / 1000)
    pad = margin * (y2 - y1)
    left = max(0, math.floor((x1 - pad) / FACTOR) * FACTOR)
    top = max(0, math.floor((y1 - pad) / FACTOR) * FACTOR)
    right = min(width, math.ceil((x2 + pad) / FACTOR) * FACTOR)
    bottom = min(height, math.ceil((y2 + pad) / FACTOR) * FACTOR)
    return left, top, right, bottom


def crop_padded(page: Image.Image, rect: tuple[int, int, int, int]) -> Image.Image:
    """The rectangle's pixels, padded right/bottom with white up to the pixel floor."""
    crop = page.crop(rect)
    side = math.ceil(math.sqrt(MIN_PIXELS) / FACTOR) * FACTOR  # 256
    canvas_size = (max(crop.width, side) if crop.width * crop.height < MIN_PIXELS else crop.width,
                   max(crop.height, side) if crop.width * crop.height < MIN_PIXELS else crop.height)
    if canvas_size == crop.size:
        return crop
    canvas = Image.new("RGB", canvas_size, (255, 255, 255))
    canvas.paste(crop, (0, 0))
    return canvas


def draw_rect(page: Image.Image, rect: tuple[int, int, int, int], *, width: int = 3) -> Image.Image:
    """A copy of the page with the rectangle outlined in red, outside the box itself."""
    marked = page.copy()
    ImageDraw.Draw(marked).rectangle(rect, outline=(255, 0, 0), width=width)
    return marked
