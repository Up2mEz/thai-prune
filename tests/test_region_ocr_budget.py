"""Budget-matching tests using a stand-in smart_resize (no processor needed)."""

from __future__ import annotations

import math

import pytest

from labbs2026.region_ocr.budget import (
    degenerate_budgets,
    find_pixel_budget_for_target,
    placeholders_for,
    plan_region_budgets,
)

PATCH, MERGE = 14, 2
MIN_PIXELS, MAX_PIXELS = 112896, 1003520


def smart_resize(height, width, *, factor, min_pixels, max_pixels):
    """Reimplementation of the processor's contract: round up to `factor`, clamp area."""
    h = max(factor, int(math.ceil(height / factor)) * factor)
    w = max(factor, int(math.ceil(width / factor)) * factor)
    if h * w > max_pixels:
        scale = math.sqrt(max_pixels / (h * w))
        h = max(factor, int(math.floor(h * scale / factor)) * factor)
        w = max(factor, int(math.floor(w * scale / factor)) * factor)
    if h * w < min_pixels:
        scale = math.sqrt(min_pixels / (h * w))
        h = max(factor, int(math.ceil(h * scale / factor)) * factor)
        w = max(factor, int(math.ceil(w * scale / factor)) * factor)
    return h, w


KW = dict(smart_resize=smart_resize, patch=PATCH, merge=MERGE,
          min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)


def test_small_crop_is_upsampled_to_the_floor() -> None:
    count, (h, w) = placeholders_for(49, 262, **KW)
    assert h * w >= MIN_PIXELS
    assert count >= MIN_PIXELS // (PATCH * MERGE) ** 2


def test_large_crop_is_clamped_to_the_ceiling() -> None:
    _, (h, w) = placeholders_for(4000, 4000, **KW)
    assert h * w <= MAX_PIXELS


def test_find_resize_returns_a_reachable_count() -> None:
    full, _ = placeholders_for(49, 262, **KW)
    target = round(full * 0.5)
    found = find_pixel_budget_for_target(49, 262, target, smart_resize=smart_resize, patch=PATCH, merge=MERGE)
    recomputed, _ = placeholders_for(
        49, 262, smart_resize=smart_resize, patch=PATCH, merge=MERGE,
        min_pixels=found["forced_pixels"], max_pixels=found["forced_pixels"],
    )
    assert found["achieved"] == recomputed
    assert found["target"] == target
    assert found["absolute_error"] == abs(found["achieved"] - target)


def test_find_resize_rejects_nonsense_target() -> None:
    with pytest.raises(ValueError):
        find_pixel_budget_for_target(49, 262, 0, smart_resize=smart_resize, patch=PATCH, merge=MERGE)


def test_plan_matches_pruning_to_what_rr_achieved_not_the_target() -> None:
    """The matched pair must use the achieved count, or the arms differ."""
    plan = plan_region_budgets(49, 262, [0.75, 0.5, 0.25], **KW)
    for budget in plan["budgets"]:
        assert budget["pruning_placeholders"] == budget["resolution_reduction"]["achieved"]
        assert budget["matched"] is True


def test_plan_budgets_are_ordered_and_below_full() -> None:
    plan = plan_region_budgets(49, 262, [0.75, 0.5, 0.25], **KW)
    counts = [b["pruning_placeholders"] for b in plan["budgets"]]
    assert all(c <= plan["full_placeholders"] for c in counts)
    assert counts == sorted(counts, reverse=True)


def test_plan_rejects_ratios_outside_the_open_unit_interval() -> None:
    for bad in (0.0, 1.0, 1.5, -0.2):
        with pytest.raises(ValueError, match="strictly between"):
            plan_region_budgets(49, 262, [bad], **KW)


@pytest.mark.parametrize(
    ("h", "w"),
    [(18, 47), (49, 262), (31, 260), (60, 360), (90, 600), (275, 1438), (66, 215)],
)
def test_real_tems_shapes_produce_non_degenerate_budgets(h: int, w: int) -> None:
    """Every observed TEMS crop shape must give four distinct budget levels."""
    plan = plan_region_budgets(h, w, [0.75, 0.5, 0.25], **KW)
    assert degenerate_budgets(plan) == []
    counts = [plan["full_placeholders"]] + [b["pruning_placeholders"] for b in plan["budgets"]]
    assert len(set(counts)) == 4


def test_degenerate_detection_flags_a_collision() -> None:
    plan = {
        "full_placeholders": 100,
        "budgets": [
            {"ratio": 0.75, "pruning_placeholders": 100},
            {"ratio": 0.5, "pruning_placeholders": 50},
            {"ratio": 0.25, "pruning_placeholders": 50},
        ],
    }
    assert degenerate_budgets(plan) == [0.75, 0.5, 0.25]
