"""Patch-phase shifts of a grid-aligned crop, without any resampling (INPUT_SIDE_D1).

Starts from FIND_VS_READ_F1's page-scale crop rectangle (`find_vs_read.geometry`):
the boxed region on the prepared page, snapped to the 32-px token grid. For a
shift `d`, the crop window is moved **up** by `d` pixels, so every glyph sits `d`
pixels lower relative to the 16-px patch grid and the 32-px merged-token grid.

The window is the F1 rectangle **extended downward by `EXTRA_BELOW` = max(d)
pixels** (registration addendum 1): for every `d` the rectangle's own pixels
stay inside the window, so no shift clips the boxed text. The smoke showed that
without the extension a shift of 32 or 64 cut the bottom of the text and the
model read another line. Rows outside the page are white. The window has one
size for every `d` (a multiple of 32), and small windows are padded exactly as
in F1, so the processor never resizes it and no pixel is interpolated
(Up2mEz's edit 1).

- `d` in {0, 4, 8, 12}: patch phase (a 16-px period).
- `d = 16`: the same patch phase as 0, a different 2x2 merge pairing (32-px period).
- `d = 32`, `d = 64`: the same patch and merge phase as 0, one and two token
  rows further down — the phase-neutral controls (M-RoPE positions and edge
  context change); two of them, so the control is not a single count.
"""

from __future__ import annotations

from PIL import Image

from labbs2026.find_vs_read.geometry import FACTOR, MIN_PIXELS

SHIFTS = (0, 4, 8, 12, 16, 32, 64)
EXTRA_BELOW = max(SHIFTS)  # a multiple of 32, so the window stays on the token grid


def shifted_window(page: Image.Image, rect: tuple[int, int, int, int], d: int,
                   extra_below: int = EXTRA_BELOW) -> Image.Image:
    """Page rows `[top - d, bottom + extra_below - d)` over `rect`'s columns: the
    rectangle extended downward by `extra_below`, moved up by `d`; white outside the page."""
    if d < 0 or d > extra_below:
        raise ValueError("d must lie in [0, extra_below] so the rectangle is never clipped")
    left, top, right, bottom = rect
    if (right - left) % FACTOR or (bottom - top) % FACTOR or extra_below % FACTOR:
        raise ValueError("the rectangle and the extension must be multiples of the token grid")
    window = Image.new("RGB", (right - left, bottom - top + extra_below), (255, 255, 255))
    src_top = top - d
    visible_top = max(0, src_top)
    visible_bottom = min(page.height, bottom + extra_below - d)
    if visible_bottom > visible_top:
        strip = page.crop((left, visible_top, right, visible_bottom))
        window.paste(strip, (0, visible_top - src_top))
    return window


def pad_to_floor(window: Image.Image) -> Image.Image:
    """F1's padding: right/bottom white up to the processor's pixel floor; never resized."""
    if window.width * window.height >= MIN_PIXELS:
        return window
    side = 256
    canvas = Image.new("RGB", (max(window.width, side), max(window.height, side)), (255, 255, 255))
    canvas.paste(window, (0, 0))
    return canvas


def shifted_crop(page: Image.Image, rect: tuple[int, int, int, int], d: int) -> Image.Image:
    return pad_to_floor(shifted_window(page, rect, d))
