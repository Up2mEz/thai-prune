"""Analysis tests: the shared bootstrap plan and the paired DiD are what matter."""

from __future__ import annotations

import numpy as np
import pytest

from labbs2026.region_ocr.analysis import (
    analyse_population,
    bootstrap_matrix,
    delta_cer,
    eligible_regions,
    holm,
    per_region_cer,
    summarise,
)

BUDGETS = ("75", "50", "25")


def _records(n_regions=8, crops_per_photo=2):
    out = []
    for i in range(n_regions):
        image = f"img_{i:03d}"
        photo = f"ph_{i // crops_per_photo}"
        for cond in ["FULL"] + [f"{p}_{b}" for b in BUDGETS for p in ("PRUNE_GRID", "RR")]:
            hyp = "\u0e01\u0e35\u0e48" if cond == "FULL" else "\u0e01\u0e35"
            out.append({
                "image_id": image, "source_photo_id": photo,
                "reference": "\u0e01\u0e35\u0e48", "parsed_output": hyp,
                "condition_id": cond,
            })
    return out


def _clusters(records):
    return {r["image_id"]: r["source_photo_id"] for r in records}


def test_per_region_cer_rejects_duplicates() -> None:
    records = _records(1)
    with pytest.raises(RuntimeError, match="duplicate observation"):
        per_region_cer(records + [records[0]])


def test_eligible_regions_drops_incomplete_rows() -> None:
    records = [r for r in _records(3) if not (r["image_id"] == "img_001" and r["condition_id"] == "RR_50")]
    table = per_region_cer(records)
    conditions = [f"{p}_{b}" for b in BUDGETS for p in ("PRUNE_GRID", "RR")]
    assert "img_001" not in eligible_regions(table, conditions)
    assert len(eligible_regions(table, conditions)) == 2


def test_full_correct_filter_selects_only_zero_cer_regions() -> None:
    records = _records(4)
    for r in records:
        if r["image_id"] == "img_000" and r["condition_id"] == "FULL":
            r["parsed_output"] = "\u0e02"  # wrong at FULL
    table = per_region_cer(records)
    conditions = [f"{p}_{b}" for b in BUDGETS for p in ("PRUNE_GRID", "RR")]
    assert "img_000" in eligible_regions(table, conditions)
    assert "img_000" not in eligible_regions(table, conditions, full_correct_only=True)


def test_delta_is_paired_within_region() -> None:
    table = per_region_cer(_records(3))
    regions = ["img_000", "img_001", "img_002"]
    values = delta_cer(table, regions, "RR_50")
    expected = table[("img_000", "RR_50")] - table[("img_000", "FULL")]
    assert values[0] == pytest.approx(expected)


def test_bootstrap_plan_resamples_whole_clusters() -> None:
    """Crops from one photograph must move together, never independently."""
    records = _records(6, crops_per_photo=2)
    regions = sorted({r["image_id"] for r in records})
    clusters = _clusters(records)
    plan = bootstrap_matrix(regions, clusters, resamples=50, seed=1)
    assert len(plan) == 50
    for draw in plan:
        assert draw.size == len(regions)
        picked = [clusters[regions[i]] for i in draw]
        for cluster in set(picked):
            assert picked.count(cluster) % 2 == 0  # both crops or neither


def test_bootstrap_plan_is_deterministic_for_a_seed() -> None:
    records = _records(6)
    regions = sorted({r["image_id"] for r in records})
    clusters = _clusters(records)
    a = bootstrap_matrix(regions, clusters, resamples=20, seed=7)
    b = bootstrap_matrix(regions, clusters, resamples=20, seed=7)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))


def test_shared_plan_gives_zero_variance_for_identical_arms() -> None:
    """The reason one plan is shared: identical arms must difference to exactly zero."""
    records = _records(8)
    regions = sorted({r["image_id"] for r in records})
    clusters = _clusters(records)
    table = per_region_cer(records)
    plan = bootstrap_matrix(regions, clusters, resamples=100, seed=3)
    grid = delta_cer(table, regions, "PRUNE_GRID_50")
    rr = delta_cer(table, regions, "RR_50")
    contrast = grid - rr
    draws = np.array([contrast[idx].mean() for idx in plan])
    assert np.allclose(draws, 0.0)


def test_summarise_reports_mean_and_interval() -> None:
    values = np.array([0.1, 0.2, 0.3, 0.4])
    plan = [np.array([0, 1, 2, 3])] * 10
    out = summarise(values, plan)
    assert out["mean"] == pytest.approx(0.25)
    assert out["n_regions"] == 4
    assert out["ci_low"] <= out["mean"] <= out["ci_high"]


def test_holm_is_monotone_and_bounded() -> None:
    adjusted = holm([0.01, 0.04, 0.03])
    assert all(0.0 <= p <= 1.0 for p in adjusted)
    assert adjusted[0] <= adjusted[2] <= adjusted[1]
    assert holm([0.5]) == [0.5]


def test_analyse_population_reports_both_arms_and_did() -> None:
    records = _records(10)
    table = per_region_cer(records)
    result = analyse_population(
        table, _clusters(records), BUDGETS, resamples=100, seed=5, full_correct_only=False
    )
    assert result["population"] == "ALL_ELIGIBLE"
    assert result["regions"] == 10
    assert set(result["did"]) == set(BUDGETS)
    for budget in BUDGETS:
        assert "p_holm" in result["did"][budget]
        assert f"PRUNE_GRID_{budget}" in result["arms"]
        assert f"RR_{budget}" in result["arms"]


def test_analyse_population_raises_when_nothing_is_eligible() -> None:
    records = _records(2)
    for r in records:
        if r["condition_id"] == "RR_25":
            r["condition_id"] = "DROPPED"
    table = per_region_cer(records)
    with pytest.raises(RuntimeError, match="complete row"):
        analyse_population(table, _clusters(records), BUDGETS,
                           resamples=10, seed=1, full_correct_only=False)
