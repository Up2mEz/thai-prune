import json
from pathlib import Path

import pytest
import yaml

from labbs2026.stage0.resolution_geometry import candidate_resolution_table, square_resolution_record


def test_frozen_budget_geometry():
    expected = {448: 256, 392: 196, 308: 121, 224: 64}
    for resolution, positions in expected.items():
        row = square_resolution_record(resolution)
        assert row["pre_merge_patch_count"] == (resolution // 14) ** 2
        assert row["projector_output_positions"] == positions
        assert row["actual_llm_image_placeholders"] == positions


def test_candidate_table_is_monotonic_and_complete():
    table = candidate_resolution_table()
    assert [row["input_dimensions"][0] for row in table] == [448, 420, 392, 364, 336, 308, 280, 252, 224]
    positions = [row["actual_llm_image_placeholders"] for row in table]
    assert positions == sorted(positions, reverse=True)


def test_invalid_resolution_fails_closed():
    with pytest.raises(ValueError):
        square_resolution_record(300)


def test_frozen_config_and_processor_evidence_match_geometry():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(
        (root / "configs/stage0/overall_model_budget_design.yaml").read_text("utf-8")
    )
    evidence = json.loads(
        (root / config["intervention"]["processor_geometry_evidence"]).read_text("utf-8")
    )
    assert not evidence["model_weights_loaded"]
    assert not evidence["locked_validation_access"]
    evidence_by_resolution = {
        row["input_dimensions"][0]: row for row in evidence["candidate_mapping"]
    }
    for budget in config["intervention"]["budgets"]:
        resolution = budget["input_resolution"][0]
        row = evidence_by_resolution[resolution]
        assert budget["image_grid_thw"] == row["image_grid_thw"]
        assert budget["pre_merge_patches"] == row["pre_merge_patch_count"]
        assert budget["llm_image_placeholders"] == row["actual_llm_image_placeholders"]


def test_locked_panel_counts_and_authorization_are_fail_closed():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(
        (root / "configs/stage0/overall_model_budget_design.yaml").read_text("utf-8")
    )
    design = yaml.safe_load(
        (root / config["dataset"]["allocation_source"]).read_text("utf-8")
    )
    assert len(design["allocation"]["locked_validation_pair_ids"]) == 100
    assert config["dataset"]["gate0_full_information_calls"] == 100 * 2 * 4 * 2
    assert config["dataset"]["complete_four_budget_calls"] == 100 * 2 * 4 * 2 * 4
    assert config["dataset"]["reuse_locked_pairs_in_future_budget_experiment"]
    assert not config["authorization"]["locked_inference"]
    assert not config["authorization"]["resolution_reduction_inference"]
