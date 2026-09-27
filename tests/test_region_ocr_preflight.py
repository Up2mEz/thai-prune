"""Preflight tests with a fake processor: the failure paths are what matter."""

from __future__ import annotations

import math

import pytest

torch = pytest.importorskip("torch")

from labbs2026.region_ocr.run import preflight_processor_contract

PATCH, MERGE = 14, 2


def smart_resize(height, width, *, factor, min_pixels, max_pixels):
    h = max(factor, int(math.ceil(height / factor)) * factor)
    w = max(factor, int(math.ceil(width / factor)) * factor)
    if h * w > max_pixels:
        s = math.sqrt(max_pixels / (h * w))
        h = max(factor, int(math.floor(h * s / factor)) * factor)
        w = max(factor, int(math.floor(w * s / factor)) * factor)
    if h * w < min_pixels:
        s = math.sqrt(min_pixels / (h * w))
        h = max(factor, int(math.ceil(h * s / factor)) * factor)
        w = max(factor, int(math.ceil(w * s / factor)) * factor)
    return h, w


GEOMETRY = dict(smart_resize=smart_resize, patch=PATCH, merge=MERGE,
                min_pixels=112896, max_pixels=1003520)


class FakeProcessor:
    """Returns the grid a faithful processor would, unless told to misbehave."""

    def __init__(self, *, full_override=None, reduced_override=None, ignore_forcing=False):
        self.full_override = full_override
        self.reduced_override = reduced_override
        self.ignore_forcing = ignore_forcing

    def apply_chat_template(self, messages, **kwargs):
        forced = (kwargs.get("processor_kwargs") or {}).get("min_pixels")
        if forced is None or self.ignore_forcing:
            bounds = (GEOMETRY["min_pixels"], GEOMETRY["max_pixels"])
            override = self.full_override
        else:
            bounds = (forced, forced)
            override = self.reduced_override
        h, w = smart_resize(64, 256, factor=PATCH * MERGE,
                            min_pixels=bounds[0], max_pixels=bounds[1])
        grid = [1, h // PATCH, w // PATCH]
        if override is not None:
            grid = [1, override * MERGE, MERGE]  # force a specific placeholder count
        return {"image_grid_thw": torch.tensor([grid])}


def test_faithful_processor_passes() -> None:
    result = preflight_processor_contract(FakeProcessor(), GEOMETRY)
    assert result["geometry_prediction_matches"] is True
    assert result["resolution_reduction_effective"] is True
    assert result["reduced_placeholders"] < result["full_placeholders"]


def test_geometry_mismatch_is_caught() -> None:
    """A processor whose grid disagrees with our prediction must fail fast."""
    with pytest.raises(RuntimeError, match="processor geometry contract broken"):
        preflight_processor_contract(FakeProcessor(full_override=999), GEOMETRY)


def test_ignored_forcing_is_caught() -> None:
    """The bug that mattered: RR kwargs silently ignored, so nothing reduces."""
    with pytest.raises(RuntimeError, match="did not reduce|Resolution Reduction contract"):
        preflight_processor_contract(FakeProcessor(ignore_forcing=True), GEOMETRY)


def test_wrong_reduced_count_is_caught() -> None:
    with pytest.raises(RuntimeError, match="Resolution Reduction contract broken"):
        preflight_processor_contract(FakeProcessor(reduced_override=7), GEOMETRY)
