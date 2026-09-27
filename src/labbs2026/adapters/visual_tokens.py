"""Shared arithmetic for adapters with grid-based spatial merging."""

from __future__ import annotations


def visual_counts_from_grid(
    grid_thw: tuple[int, int, int], spatial_merge_size: int
) -> tuple[int, int]:
    """Return pre-merge patch count and post-merge LLM visual positions."""

    if len(grid_thw) != 3 or any(value <= 0 for value in grid_thw):
        raise ValueError("image_grid_thw must contain three positive integers")
    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    premerge = grid_thw[0] * grid_thw[1] * grid_thw[2]
    merge_area = spatial_merge_size**2
    if premerge % merge_area:
        raise ValueError("image grid is not divisible by the spatial merge area")
    return premerge, premerge // merge_area
