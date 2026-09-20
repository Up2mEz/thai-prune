"""Tests for the merge/coverage policies and the stage-resolved cost meter.

The merge arm is only interpretable if it keeps exactly the survivors and
positions that `PRUNE_GRID` keeps, so the properties asserted here are the ones
that make the two conditions a controlled contrast rather than two unrelated
interventions.
"""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.cost import CostMeter, analytic_compute
from labbs2026.region_ocr.pruning import (
    assign_to_representatives,
    select_coverage_indices,
    select_grid_indices,
    select_keep_indices,
)

torch = pytest.importorskip("torch")

from labbs2026.region_ocr.merge_runtime import (  # noqa: E402
    merge_features,
    token_ink_scores,
)


# --- partition -------------------------------------------------------------

def test_every_token_is_assigned_and_representatives_map_to_themselves() -> None:
    rows, cols, kept = 8, 10, 12
    reps = select_grid_indices(rows, cols, kept)
    assignment = assign_to_representatives(rows, cols, reps)
    assert len(assignment) == rows * cols
    assert set(assignment) == set(range(kept))
    for ordinal, rep in enumerate(reps):
        assert assignment[rep] == ordinal


def test_assignment_is_deterministic() -> None:
    reps = select_grid_indices(7, 9, 10)
    assert assign_to_representatives(7, 9, reps) == assign_to_representatives(7, 9, reps)


def test_assignment_picks_the_nearer_representative() -> None:
    # A 1x5 strip with representatives at the two ends: the split is at the
    # midpoint, and the tie at index 2 breaks toward the lower ordinal.
    assert assign_to_representatives(1, 5, (0, 4)) == (0, 0, 0, 1, 1)


def test_assignment_rejects_malformed_representatives() -> None:
    with pytest.raises(ValueError, match="at least one"):
        assign_to_representatives(4, 4, ())
    with pytest.raises(ValueError, match="distinct"):
        assign_to_representatives(4, 4, (1, 1))
    with pytest.raises(ValueError, match="outside"):
        assign_to_representatives(2, 2, (9,))


# --- coverage selection ----------------------------------------------------

def test_coverage_keeps_one_token_per_cell() -> None:
    rows, cols, kept = 6, 6, 9
    scores = [0.0] * (rows * cols)
    chosen = select_coverage_indices(rows, cols, kept, scores)
    assert len(chosen) == kept == len(set(chosen))
    assignment = assign_to_representatives(rows, cols, select_grid_indices(rows, cols, kept))
    assert sorted(assignment[i] for i in chosen) == list(range(kept))


def test_coverage_moves_the_survivor_onto_the_high_contrast_token() -> None:
    """The point of the policy: within a cell, prefer the token with signal."""
    rows, cols, kept = 4, 4, 4
    reps = select_grid_indices(rows, cols, kept)
    assignment = assign_to_representatives(rows, cols, reps)
    target = next(i for i in range(rows * cols) if assignment[i] == 0 and i != reps[0])
    scores = [0.0] * (rows * cols)
    scores[target] = 1.0
    chosen = select_coverage_indices(rows, cols, kept, scores)
    assert target in chosen
    assert reps[0] not in chosen


def test_coverage_requires_one_score_per_token() -> None:
    with pytest.raises(ValueError, match="expected 16 scores"):
        select_coverage_indices(4, 4, 4, [0.0] * 5)
    with pytest.raises(ValueError, match="requires per-token scores"):
        select_keep_indices(policy="COVERAGE", rows=4, cols=4, kept=4)


def test_merge_policy_selects_exactly_what_grid_selects() -> None:
    """If these ever diverge, the merge/prune contrast stops being controlled."""
    for rows, cols, kept in ((8, 10, 20), (5, 7, 9), (12, 3, 6)):
        assert select_keep_indices(
            policy="MERGE_GRID", rows=rows, cols=cols, kept=kept
        ) == select_grid_indices(rows, cols, kept)


# --- feature merging -------------------------------------------------------

def test_merge_averages_each_cell() -> None:
    features = torch.tensor([[0.0, 1.0], [2.0, 3.0], [4.0, 5.0], [6.0, 7.0]])
    merged = merge_features(features, (0, 0, 1, 1), 2)
    assert torch.allclose(merged, torch.tensor([[1.0, 2.0], [5.0, 6.0]]))


def test_merge_of_a_singleton_cell_is_the_identity() -> None:
    features = torch.randn(4, 3)
    merged = merge_features(features, (0, 1, 2, 3), 4)
    assert torch.allclose(merged, features)


def test_merge_rejects_inconsistent_shapes() -> None:
    features = torch.randn(4, 3)
    with pytest.raises(ValueError, match="assignment length"):
        merge_features(features, (0, 1), 2)
    with pytest.raises(ValueError, match="outside the kept range"):
        merge_features(features, (0, 1, 2, 3), 2)


def test_merge_leaves_no_empty_cell() -> None:
    features = torch.randn(4, 3)
    with pytest.raises(RuntimeError, match="no token"):
        merge_features(features, (0, 0, 0, 0), 2)


# --- ink scores ------------------------------------------------------------

def test_ink_score_is_higher_for_the_high_contrast_token() -> None:
    merge = 2
    flat = torch.zeros(2 * merge * merge, 3)
    flat[merge * merge:] = torch.tensor([-1.0, 1.0, -1.0]).repeat(merge * merge, 1)
    scores = token_ink_scores(flat, tokens=2, merge=merge)
    assert len(scores) == 2
    assert scores[1] > scores[0]


def test_ink_score_asserts_the_patch_grouping() -> None:
    with pytest.raises(RuntimeError, match="tokens\\*merge"):
        token_ink_scores(torch.zeros(7, 3), tokens=2, merge=2)


# --- cost meter ------------------------------------------------------------

def test_meter_records_each_stage_once() -> None:
    meter = CostMeter("cpu")
    with meter.stage("vision"):
        pass
    with meter.stage("generate"):
        pass
    record = meter.record()
    assert record["seconds_vision"] >= 0.0
    assert record["seconds_measured_total"] == pytest.approx(
        record["seconds_vision"] + record["seconds_generate"]
    )
    # On CPU there is no allocator peak to read, and claiming one would be worse
    # than reporting none.
    assert record["memory_measured"] is False
    assert record["peak_bytes_observation"] == 0


def test_meter_refuses_to_nest_or_repeat_a_stage() -> None:
    meter = CostMeter("cpu")
    stage = meter.stage("vision")
    stage.__enter__()
    with pytest.raises(RuntimeError, match="still open"):
        meter.stage("embed")
    stage.__exit__()
    with pytest.raises(RuntimeError, match="already measured"):
        meter.stage("vision")


def test_analytic_compute_is_invariant_to_post_encoder_budget() -> None:
    """Post-encoder work cannot shrink the encoder, and the record must say so."""
    full = analytic_compute(grid=[1, 20, 16], merge=2, llm_visual_positions=80,
                            prompt_length=90)
    pruned = analytic_compute(grid=[1, 20, 16], merge=2, llm_visual_positions=20,
                              prompt_length=30)
    assert full["vision_patches"] == pruned["vision_patches"] == 320
    assert full["vision_tokens_after_merge"] == 80
    assert pruned["llm_visual_positions"] == 20
    assert pruned["llm_prefill_positions"] == 30


# --- cost reporting --------------------------------------------------------

from labbs2026.region_ocr.report import (  # noqa: E402
    efficiency_profile,
    processor_geometry,
)


def _cost_record(condition, *, patches=320, positions=80, prefill=0.2, generate=0.5,
                 upsampled=True, scale=4.0):
    return {
        "image_id": "img_1", "condition_id": condition,
        "seconds_processor": 0.01, "seconds_vision": 0.1, "seconds_select": 0.0,
        "seconds_embed": 0.02, "seconds_prefill": prefill, "seconds_generate": generate,
        "seconds_decode": generate - prefill, "peak_bytes_observation": 1_000,
        "memory_measured": True, "vision_patches": patches,
        "llm_visual_positions": positions, "generated_tokens": 12,
        "native_processor_upsampled": upsampled, "native_processor_scale": scale,
        "native_source_height": 40, "native_source_width": 100,
        "native_processed_height": 80, "native_processed_width": 200,
    }


def test_efficiency_profile_confirms_the_encoder_cost_does_not_move() -> None:
    records = [
        _cost_record("FULL"),
        _cost_record("PRUNE_GRID_25", positions=20, prefill=0.05),
        _cost_record("MERGE_GRID_25", positions=20, prefill=0.05),
    ]
    profile = efficiency_profile(records)
    assert profile["post_encoder_vision_cost_invariant"] is True
    grid = profile["by_condition"]["PRUNE_GRID_25"]
    assert grid["median_vision_patches"] == 320
    assert grid["median_llm_visual_positions"] == 20
    assert grid["median_seconds_prefill"] == 0.05


def test_efficiency_profile_reports_an_absent_counter_as_unverified() -> None:
    """A missing measurement must not read as a satisfied invariant."""
    stale = _cost_record("PRUNE_GRID_25")
    del stale["vision_patches"]
    profile = efficiency_profile([_cost_record("FULL"), stale])
    assert profile["post_encoder_vision_cost_invariant"] == "UNKNOWN_NOT_RECORDED"
    assert profile["by_condition"]["PRUNE_GRID_25"]["median_vision_patches"] is None


def test_processor_geometry_exposes_upsampling() -> None:
    geometry = processor_geometry([
        _cost_record("FULL", upsampled=True, scale=4.0),
        _cost_record("RR_25", upsampled=False, scale=0.9),
    ])["by_condition"]
    assert geometry["FULL"]["upsampled_fraction"] == 1.0
    assert geometry["RR_25"]["upsampled_fraction"] == 0.0
    assert geometry["FULL"]["median_processor_scale"] == 4.0


# --- contrast families -----------------------------------------------------

from labbs2026.region_ocr.analysis import analyse_contrast  # noqa: E402


def _cer_table(merge_penalty: float):
    """Six regions, two photos; MERGE differs from GRID by a fixed amount."""
    table = {}
    for i in range(6):
        region = f"img_{i}"
        table[(region, "FULL")] = 0.10
        for budget in ("75", "50", "25"):
            table[(region, f"PRUNE_GRID_{budget}")] = 0.20
            table[(region, f"MERGE_GRID_{budget}")] = 0.20 + merge_penalty
    clusters = {f"img_{i}": f"photo_{i % 2}" for i in range(6)}
    return table, clusters


def test_contrast_family_recovers_a_planted_difference() -> None:
    table, clusters = _cer_table(merge_penalty=-0.05)
    result = analyse_contrast(
        table, clusters, ("75", "50", "25"), treatment="MERGE_GRID",
        reference="PRUNE_GRID", resamples=200, seed=7,
    )
    assert result["status"] == "ANALYSED"
    assert result["regions"] == 6 and result["clusters"] == 2
    for budget in ("75", "50", "25"):
        assert result["contrasts"][budget]["estimate"] == pytest.approx(-0.05)
        assert "p_holm" in result["contrasts"][budget]


def test_contrast_family_reports_absent_conditions_instead_of_raising() -> None:
    """A report over an earlier run must stay readable, not fail."""
    table, clusters = _cer_table(merge_penalty=0.0)
    for key in [k for k in table if k[1].startswith("MERGE_GRID")]:
        del table[key]
    result = analyse_contrast(
        table, clusters, ("75", "50", "25"), treatment="MERGE_GRID",
        reference="PRUNE_GRID", resamples=50, seed=7,
    )
    assert result["status"] == "CONDITIONS_NOT_PRESENT"
    assert "MERGE_GRID_75" in result["missing"]
