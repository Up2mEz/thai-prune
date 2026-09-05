"""Thai renderer using explicit HarfBuzz shaping and FreeType rasterization."""

from __future__ import annotations

import hashlib
import importlib.metadata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image


@dataclass(frozen=True)
class GlyphRun:
    placements: tuple[tuple[int, int, int, int, bytes], ...]
    bbox: tuple[int, int, int, int]
    glyph_ids: tuple[int, ...]
    clusters: tuple[int, ...]
    missing_glyph: bool


@dataclass(frozen=True)
class PairRenderMetadata:
    shared_origin: tuple[int, int]
    bbox_a: tuple[int, int, int, int]
    bbox_b: tuple[int, int, int, int]
    glyph_ids_a: tuple[int, ...]
    glyph_ids_b: tuple[int, ...]
    glyph_clusters_a: tuple[int, ...]
    glyph_clusters_b: tuple[int, ...]
    missing_glyph: bool
    ink_pixels_a: int
    ink_pixels_b: int
    critical_pixel_area: int
    critical_bbox: tuple[int, int, int, int]
    critical_centroid: tuple[float, float]
    difference_mask_rule: str
    difference_threshold: int
    anti_aliasing_representation: str
    max_coverage_delta: int
    coverage_delta_sum: int
    shared_origin_policy: str
    actual_origin_delta: tuple[int, int]
    separately_centered_origin_delta: tuple[int, int]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _shape(text: str, font_path: Path, font_size: int) -> GlyphRun:
    font_data = font_path.read_bytes()
    hb_face = hb.Face(font_data)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (font_size * 64, font_size * 64)
    hb.ot_font_set_funcs(hb_font)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.direction = "ltr"
    buffer.script = "Thai"
    buffer.language = "th"
    hb.shape(hb_font, buffer, {"kern": True, "mark": True, "mkmk": True})

    face = freetype.Face(str(font_path))
    face.set_pixel_sizes(0, font_size)
    placements: list[tuple[int, int, int, int, bytes]] = []
    glyph_ids: list[int] = []
    clusters: list[int] = []
    pen_x = 0
    pen_y = 0
    bounds: list[tuple[int, int, int, int]] = []
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        glyph_id = int(info.codepoint)
        face.load_glyph(glyph_id, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        bitmap = face.glyph.bitmap
        width = int(bitmap.width)
        rows = int(bitmap.rows)
        pitch = abs(int(bitmap.pitch))
        raw = bytes(bitmap.buffer)
        x = round((pen_x + position.x_offset) / 64) + int(face.glyph.bitmap_left)
        y = -round((pen_y + position.y_offset) / 64) - int(face.glyph.bitmap_top)
        placements.append((x, y, width, rows, raw))
        if width and rows:
            bounds.append((x, y, x + width, y + rows))
        glyph_ids.append(glyph_id)
        clusters.append(int(info.cluster))
        pen_x += int(position.x_advance)
        pen_y += int(position.y_advance)
        if pitch < width:
            raise RuntimeError("FreeType bitmap pitch is smaller than width")
    if not bounds:
        bbox = (0, 0, 0, 0)
    else:
        bbox = (
            min(value[0] for value in bounds),
            min(value[1] for value in bounds),
            max(value[2] for value in bounds),
            max(value[3] for value in bounds),
        )
    return GlyphRun(
        placements=tuple(placements),
        bbox=bbox,
        glyph_ids=tuple(glyph_ids),
        clusters=tuple(clusters),
        missing_glyph=any(glyph_id == 0 for glyph_id in glyph_ids),
    )


def _rasterize(run: GlyphRun, canvas: tuple[int, int], origin: tuple[int, int]) -> np.ndarray:
    width, height = canvas
    mask = np.zeros((height, width), dtype=np.uint8)
    for x, y, glyph_width, rows, raw in run.placements:
        if not glyph_width or not rows:
            continue
        pitch = len(raw) // rows
        glyph = np.frombuffer(raw, dtype=np.uint8).reshape(rows, pitch)[:, :glyph_width]
        left = origin[0] + x
        top = origin[1] + y
        right = left + glyph_width
        bottom = top + rows
        if left < 0 or top < 0 or right > width or bottom > height:
            raise ValueError("SHAPED_GLYPH_OUTSIDE_CANVAS")
        mask[top:bottom, left:right] = np.maximum(mask[top:bottom, left:right], glyph)
    return mask


def _rgb(mask: np.ndarray, foreground: str, background: str) -> Image.Image:
    def color(value: str) -> np.ndarray:
        value = value.lstrip("#")
        if len(value) != 6:
            raise ValueError("colors must use six-digit hex notation")
        return np.array([int(value[index : index + 2], 16) for index in (0, 2, 4)])

    fg = color(foreground)
    bg = color(background)
    alpha = mask.astype(np.float32)[..., None] / 255.0
    pixels = np.rint(bg * (1 - alpha) + fg * alpha).astype(np.uint8)
    return Image.fromarray(pixels, mode="RGB")


def render_pair(
    text_a: str,
    text_b: str,
    *,
    font_path: Path,
    font_size: int,
    canvas: tuple[int, int],
    position_offset: tuple[int, int],
    foreground: str,
    background: str,
    difference_threshold: int = 1,
) -> tuple[Image.Image, Image.Image, Image.Image, PairRenderMetadata]:
    if not 1 <= difference_threshold <= 255:
        raise ValueError("difference_threshold must be between 1 and 255")
    run_a = _shape(text_a, font_path, font_size)
    run_b = _shape(text_b, font_path, font_size)
    union = (
        min(run_a.bbox[0], run_b.bbox[0]),
        min(run_a.bbox[1], run_b.bbox[1]),
        max(run_a.bbox[2], run_b.bbox[2]),
        max(run_a.bbox[3], run_b.bbox[3]),
    )
    origin = (
        round(canvas[0] / 2 - (union[0] + union[2]) / 2 + position_offset[0]),
        round(canvas[1] / 2 - (union[1] + union[3]) / 2 + position_offset[1]),
    )
    mask_a = _rasterize(run_a, canvas, origin)
    mask_b = _rasterize(run_b, canvas, origin)
    coverage_delta = np.abs(mask_a.astype(np.int16) - mask_b.astype(np.int16))
    difference = coverage_delta >= difference_threshold
    ys, xs = np.where(difference)
    if not len(xs):
        critical_bbox = (0, 0, 0, 0)
        centroid = (0.0, 0.0)
    else:
        critical_bbox = (int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1))
        centroid = (float(xs.mean()), float(ys.mean()))
    metadata = PairRenderMetadata(
        shared_origin=origin,
        bbox_a=tuple(value + (origin[index % 2]) for index, value in enumerate(run_a.bbox)),
        bbox_b=tuple(value + (origin[index % 2]) for index, value in enumerate(run_b.bbox)),
        glyph_ids_a=run_a.glyph_ids,
        glyph_ids_b=run_b.glyph_ids,
        glyph_clusters_a=run_a.clusters,
        glyph_clusters_b=run_b.clusters,
        missing_glyph=run_a.missing_glyph or run_b.missing_glyph,
        ink_pixels_a=int(np.count_nonzero(mask_a)),
        ink_pixels_b=int(np.count_nonzero(mask_b)),
        critical_pixel_area=int(np.count_nonzero(difference)),
        critical_bbox=critical_bbox,
        critical_centroid=centroid,
        difference_mask_rule="abs(freetype_coverage_a-freetype_coverage_b)>=threshold",
        difference_threshold=difference_threshold,
        anti_aliasing_representation="FreeType 8-bit grayscale coverage",
        max_coverage_delta=int(coverage_delta.max()),
        coverage_delta_sum=int(coverage_delta[difference].sum()),
        shared_origin_policy="one union-bbox origin for both pair members",
        actual_origin_delta=(0, 0),
        separately_centered_origin_delta=(
            round((run_b.bbox[0] + run_b.bbox[2] - run_a.bbox[0] - run_a.bbox[2]) / 2),
            round((run_b.bbox[1] + run_b.bbox[3] - run_a.bbox[1] - run_a.bbox[3]) / 2),
        ),
    )
    diff_image = Image.fromarray((difference * 255).astype(np.uint8), mode="L")
    return (
        _rgb(mask_a, foreground, background),
        _rgb(mask_b, foreground, background),
        diff_image,
        metadata,
    )


def renderer_versions() -> dict[str, Any]:
    return {
        "uharfbuzz": hb.__version__,
        "freetype_py": importlib.metadata.version("freetype-py"),
        "freetype_library": list(freetype.version()),
        "engine": "uharfbuzz+freetype-py",
    }


def metadata_dict(metadata: PairRenderMetadata) -> dict[str, Any]:
    return asdict(metadata)
