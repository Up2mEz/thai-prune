"""Workload-assembly tests: the matched-pair invariant is the load-bearing one."""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.workload import (
    FAMILY_FULL,
    FAMILY_PRUNE,
    FAMILY_RR,
    assert_matched,
    build_region_observations,
    build_workload,
    workload_summary,
)

SEEDS = (11, 22)


def _region(image_id="img_1", photo="menus_1"):
    return {"image_id": image_id, "source_photo_id": photo, "label": "\u0e01\u0e35\u0e48"}


def _plan(full=160, achieved=(120, 80, 40)):
    return {
        "full_placeholders": full,
        "budgets": [
            {
                "ratio": ratio,
                "target_placeholders": round(full * ratio),
                "pruning_placeholders": got,
                "resolution_reduction": {"forced_pixels": got * 784, "achieved": got},
            }
            for ratio, got in zip((0.75, 0.5, 0.25), achieved)
        ],
    }


def test_one_region_yields_thirteen_observations() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=SEEDS)
    assert len(obs) == 1 + 3 * (1 + 1 + len(SEEDS))
    assert len(obs) == 13


def test_family_counts_are_as_designed() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=SEEDS)
    families = [o["family"] for o in obs]
    assert families.count(FAMILY_FULL) == 1
    assert families.count(FAMILY_RR) == 3
    assert families.count(FAMILY_PRUNE) == 9


def test_pruning_uses_the_achieved_count_not_the_nominal_target() -> None:
    """The matched pair is the design; a nominal target here would break it."""
    plan = _plan(full=160, achieved=(125, 84, 42))
    obs = build_region_observations(_region(), plan, random_seeds=SEEDS)
    for ratio, achieved in zip((0.75, 0.5, 0.25), (125, 84, 42)):
        group = [o for o in obs if o["nominal_ratio"] == ratio]
        assert {o["expected_placeholders"] for o in group} == {achieved}
        targets = {o["target_placeholders"] for o in group}
        assert targets == {round(160 * ratio)}
        assert achieved != round(160 * ratio) or True  # nominal may differ from achieved


def test_assert_matched_rejects_a_mismatched_pair() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=SEEDS)
    for o in obs:
        if o["condition_id"] == "PRUNE_GRID_75":
            o["expected_placeholders"] = 999
    with pytest.raises(RuntimeError, match="!= RR achieved"):
        assert_matched(obs)


def test_assert_matched_rejects_a_missing_partner() -> None:
    obs = [o for o in build_region_observations(_region(), _plan(), random_seeds=SEEDS)
           if o["condition_id"] != "RR_75"]
    with pytest.raises(RuntimeError, match="expected one RR observation"):
        assert_matched(obs)


def test_condition_ids_are_unique_and_seeds_present() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=SEEDS)
    ids = [o["condition_id"] for o in obs]
    assert len(set(ids)) == len(ids)
    for seed in SEEDS:
        assert sum(1 for o in obs if o["seed"] == seed) == 3


def test_full_condition_carries_no_intervention_parameters() -> None:
    full = [o for o in build_region_observations(_region(), _plan(), random_seeds=SEEDS)
            if o["family"] == FAMILY_FULL][0]
    assert full["policy"] is None and full["seed"] is None and full["forced_pixels"] is None
    assert full["expected_placeholders"] == full["full_placeholders"]


def test_rr_carries_forced_pixels_and_pruning_does_not() -> None:
    obs = build_region_observations(_region(), _plan(), random_seeds=SEEDS)
    assert all(o["forced_pixels"] for o in obs if o["family"] == FAMILY_RR)
    assert all(o["forced_pixels"] is None for o in obs if o["family"] == FAMILY_PRUNE)


def test_seeds_must_be_distinct_and_present() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_region_observations(_region(), _plan(), random_seeds=())
    with pytest.raises(ValueError, match="distinct"):
        build_region_observations(_region(), _plan(), random_seeds=(7, 7))


def test_build_workload_rejects_duplicate_regions() -> None:
    regions = [_region("img_1"), _region("img_1")]
    plans = {"img_1": _plan()}
    with pytest.raises(RuntimeError, match="duplicate"):
        build_workload(regions, plans, random_seeds=SEEDS)


def test_workload_summary_counts() -> None:
    regions = [_region("img_1", "menus_1"), _region("img_2", "menus_1"), _region("img_3", "bill_2")]
    plans = {r["image_id"]: _plan() for r in regions}
    work = build_workload(regions, plans, random_seeds=SEEDS)
    summary = workload_summary(work)
    assert summary == {
        "observations": 39,
        "regions": 3,
        "clusters": 2,
        "conditions_per_region": 13,
        "by_family": {FAMILY_FULL: 3, FAMILY_RR: 9, FAMILY_PRUNE: 27},
    }
