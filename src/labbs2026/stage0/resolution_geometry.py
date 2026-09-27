"""Pure processor-geometry calculations for the frozen Paddle/Wayu grid."""

from __future__ import annotations

from typing import Any


def square_resolution_record(resolution: int, full_positions: int = 256) -> dict[str, Any]:
    patch_size, merge_size = 14, 2
    factor = patch_size * merge_size
    if resolution <= 0 or resolution % factor:
        raise ValueError("resolution must be a positive multiple of patch_size * merge_size (28)")
    patch_axis = resolution // patch_size
    if patch_axis % merge_size:
        raise ValueError("patch grid must be divisible by spatial merge size")
    pre_merge = patch_axis**2
    llm_axis = patch_axis // merge_size
    positions = llm_axis**2
    return {
        "input_dimensions": [resolution, resolution],
        "min_pixels": resolution**2,
        "max_pixels": resolution**2,
        "image_grid_thw": [1, patch_axis, patch_axis],
        "pre_merge_patch_count": pre_merge,
        "projector_output_positions": positions,
        "actual_llm_image_placeholders": positions,
        "fraction_full_visual_positions_retained": positions / full_positions,
    }


def candidate_resolution_table() -> list[dict[str, Any]]:
    return [square_resolution_record(value) for value in range(448, 223, -28)]
