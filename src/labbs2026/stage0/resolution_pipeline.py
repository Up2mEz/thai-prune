"""Frozen deterministic INPUT RESOLUTION REDUCTION image pipeline."""

from __future__ import annotations

import hashlib
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


SOURCE_SIZE = (448, 448)
ALLOWED_OUTPUT_SIZES = {(448, 448), (392, 392), (308, 308), (224, 224)}
PILLOW_VERSION = "12.3.0"
RESAMPLE = Image.Resampling.BICUBIC
PNG_COMPRESS_LEVEL = 9


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pixel_sha256(image: Image.Image) -> str:
    return _sha256(np.asarray(image, dtype=np.uint8).tobytes(order="C"))


def materialize_budget_image(
    source_path: Path, output_path: Path, output_size: tuple[int, int]
) -> dict[str, Any]:
    """Create one registered budget PNG without overwriting existing evidence."""
    if version("Pillow") != PILLOW_VERSION:
        raise RuntimeError(
            f"Pillow version mismatch: expected {PILLOW_VERSION}, observed {version('Pillow')}"
        )
    if output_size not in ALLOWED_OUTPUT_SIZES:
        raise ValueError(f"unregistered output size: {output_size}")
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")

    source_bytes = source_path.read_bytes()
    with Image.open(source_path) as opened:
        opened.load()
        if opened.format != "PNG" or opened.size != SOURCE_SIZE or opened.mode != "RGB":
            raise RuntimeError("source must be a registered 448x448 RGB PNG")
        orientation = opened.getexif().get(274)
        if orientation not in (None, 1):
            raise RuntimeError("source PNG must not require EXIF orientation")
        source_pixels = opened.copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_size == SOURCE_SIZE:
        output_path.write_bytes(source_bytes)
    else:
        reduced = source_pixels.resize(output_size, RESAMPLE, reducing_gap=None)
        reduced.save(
            output_path,
            format="PNG",
            optimize=False,
            compress_level=PNG_COMPRESS_LEVEL,
        )

    output_bytes = output_path.read_bytes()
    with Image.open(output_path) as output_image:
        output_image.load()
        if output_image.size != output_size or output_image.mode != "RGB":
            raise RuntimeError("materialized PNG geometry or mode mismatch")
        output_pixel_hash = _pixel_sha256(output_image)

    return {
        "source_path": source_path.as_posix(),
        "output_path": output_path.as_posix(),
        "source_file_sha256": _sha256(source_bytes),
        "source_pixel_sha256": _pixel_sha256(source_pixels),
        "output_file_sha256": _sha256(output_bytes),
        "output_pixel_sha256": output_pixel_hash,
        "source_size": list(SOURCE_SIZE),
        "output_size": list(output_size),
        "mode": "RGB",
        "library": "Pillow",
        "library_version": PILLOW_VERSION,
        "resize_function": "PIL.Image.Image.resize",
        "interpolation": "Image.Resampling.BICUBIC",
        "antialias": "BICUBIC_KERNEL_NO_SEPARATE_BOOLEAN",
        "reducing_gap": None,
        "rounding": "NONE_EXACT_INTEGER_WIDTH_HEIGHT",
        "png_optimize": False,
        "png_compress_level": PNG_COMPRESS_LEVEL,
        "metadata_policy": "NO_METADATA_WRITTEN_FOR_REDUCED_IMAGES",
    }
