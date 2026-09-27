"""Tests for the arms that break the magnification confound.

Round 2 showed that these crops sit far below the processor's pixel floor, so
every condition is an upsample of the source and none of them loses source
information. Resolution Reduction therefore differs from post-encoder pruning in
magnification as well as in where tokens are removed, and the two cannot be told
apart. These arms exist to separate them, so what is asserted here is exactly
the separation: the restored image carries FULL's dimensions but a coarser
grid's detail, and the sweep reaches magnifications FULL cannot.
"""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.budget import plan_magnification_sweep, plan_region_budgets
from labbs2026.region_ocr.workload import (
    FAMILY_PRUNE,
    FAMILY_RESTORED,
    FAMILY_SWEEP,
    IDENTITY_FAMILIES,
    assert_matched,
    build_region_observations,
)

Image = pytest.importorskip("PIL.Image")

from labbs2026.region_ocr.execute import _apply_pre_resize  # noqa: E402


def _smart_resize(height, width, factor, min_pixels, max_pixels):
    """Stand-in for the processor's rule: round to `factor`, honour the bounds."""
    import math

    scale = 1.0
    if height * width < min_pixels:
        scale = math.sqrt(min_pixels / (height * width))
    elif height * width > max_pixels:
        scale = math.sqrt(max_pixels / (height * width))
    new_h = max(factor, int(round(height * scale / factor)) * factor)
    new_w = max(factor, int(round(width * scale / factor)) * factor)
    return new_h, new_w


GEOMETRY = dict(smart_resize=_smart_resize, patch=14, merge=2)


# --- pre-resize round trip -------------------------------------------------

def test_no_pre_resize_leaves_the_image_and_record_alone() -> None:
    image = Image.new("RGB", (100, 40), "white")
    result, record = _apply_pre_resize(image, None, 3)
    assert result is image and record is None


def test_pre_resize_returns_the_up_dimensions_and_records_both() -> None:
    image = Image.new("RGB", (176, 41), "white")
    result, record = _apply_pre_resize(
        image, {"down": [84, 364], "up": [168, 700]}, 3
    )
    assert result.size == (700, 168)
    assert record == {
        "pre_resize_down": [84, 364],
        "pre_resize_up": [168, 700],
        "pre_resize_resample": 3,
    }


def test_pre_resize_actually_destroys_detail() -> None:
    """A no-op round trip would make the restored arm a duplicate of FULL."""
    import itertools

    image = Image.new("RGB", (700, 168))
    pixels = image.load()
    for x, y in itertools.product(range(700), range(168)):
        pixels[x, y] = (255, 255, 255) if (x + y) % 2 else (0, 0, 0)

    # A one-pixel checkerboard cannot survive being rendered at a quarter area.
    restored, _ = _apply_pre_resize(image, {"down": [42, 175], "up": [168, 700]}, 3)
    original = list(image.convert("L").get_flattened_data())
    after = list(restored.convert("L").get_flattened_data())
    assert len(original) == len(after)
    assert sum(abs(a - b) for a, b in zip(original, after)) / len(after) > 10


# --- magnification sweep ---------------------------------------------------

def test_sweep_reaches_above_and_below_full() -> None:
    plan = plan_region_budgets(41, 176, [0.5], min_pixels=112896, max_pixels=1003520,
                               **GEOMETRY)
    full = plan["full_placeholders"]
    sweep = plan_magnification_sweep(41, 176, full, [2.0, 0.125], **GEOMETRY)
    above, below = sweep
    assert above["placeholders"] > full, "the sweep must exceed FULL's magnification"
    assert below["placeholders"] < full
    assert above["factor"] == 2.0


def test_sweep_rejects_a_non_positive_factor() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        plan_magnification_sweep(41, 176, 150, [0.0], **GEOMETRY)


# --- workload assembly -----------------------------------------------------

def _plan():
    return {
        "full_placeholders": 150,
        "budgets": [
            {
                "ratio": ratio,
                "target_placeholders": round(150 * ratio),
                "pruning_placeholders": achieved,
                "resolution_reduction": {"forced_pixels": achieved * 784},
                "restored": {
                    "down_height": 84, "down_width": 364,
                    "up_height": 168, "up_width": 700,
                    "forced_pixels": 117600, "placeholders": 150,
                },
            }
            for ratio, achieved in zip((0.75, 0.5, 0.25), (110, 72, 39))
        ],
        "sweep": [
            {"factor": f, "target_placeholders": t, "placeholders": a,
             "resolution": {"forced_pixels": a * 784}}
            for f, t, a in ((2.0, 300, 315), (1.5, 225, 217), (0.125, 19, 18))
        ],
    }


def _region():
    return {"image_id": "img_1", "source_photo_id": "photo_1", "label": "ก"}


def test_the_round_three_grid_is_twenty_eight_conditions() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=(11, 22))
    assert len(obs) == 28
    ids = [o["condition_id"] for o in obs]
    assert len(set(ids)) == 28
    for label in ("75", "50", "25"):
        assert f"RR_RESTORED_{label}" in ids
        assert f"PRUNE_GRID_RESTORED_{label}" in ids
    assert {"SWEEP_200", "SWEEP_150", "SWEEP_012"} <= set(ids)


def test_restored_arm_keeps_fulls_token_count_and_claims_no_budget_match() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=(11, 22))
    for label in ("75", "50", "25"):
        restored = [o for o in obs if o["condition_id"] == f"RR_RESTORED_{label}"][0]
        assert restored["family"] == FAMILY_RESTORED
        assert restored["family"] in IDENTITY_FAMILIES
        assert restored["expected_placeholders"] == 150
        assert restored["budget_matched"] is False
        assert restored["pre_resize"] == {"down": [84, 364], "up": [168, 700]}


def test_restored_pruning_arm_matches_its_resolution_reduction_partner() -> None:
    """Same budget as RR and the same pixel detail: that is the point of it."""
    obs = build_region_observations(_region(), _plan(), random_seeds=(11, 22))
    for label, achieved in zip(("75", "50", "25"), (110, 72, 39)):
        arm = [o for o in obs if o["condition_id"] == f"PRUNE_GRID_RESTORED_{label}"][0]
        rr = [o for o in obs if o["condition_id"] == f"RR_{label}"][0]
        assert arm["family"] == FAMILY_PRUNE
        assert arm["expected_placeholders"] == rr["expected_placeholders"] == achieved
        assert arm["budget_matched"] is True
        assert arm["pre_resize"] is not None


def test_sweep_arms_are_identity_and_exempt_from_budget_matching() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=(11, 22))
    sweep = [o for o in obs if o["family"] == FAMILY_SWEEP]
    assert len(sweep) == 3
    assert all(o["budget_matched"] is False for o in sweep)
    assert all(o["family"] in IDENTITY_FAMILIES for o in sweep)
    assert [o["expected_placeholders"] for o in sweep] == [315, 217, 18]
    # Nothing is exempted silently: assert_matched still runs over the whole set.
    assert_matched(obs)


def test_an_unmatched_restored_pruning_arm_is_still_caught() -> None:
    """The exemption must not become a hole in the matched-budget invariant."""
    obs = build_region_observations(_region(), _plan(), random_seeds=(11, 22))
    for o in obs:
        if o["condition_id"] == "PRUNE_GRID_RESTORED_50":
            o["expected_placeholders"] = 999
    with pytest.raises(RuntimeError, match="!= RR achieved"):
        assert_matched(obs)
