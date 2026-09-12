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
    assert config["execution"]["total_calls"] == 100 * 2 * 4 * 2 * 4
    assert config["execution"]["mode"] == "ONE_SHOT_LOCKED_CONFIRMATORY_PANEL"
    assert config["execution"]["gate0_full_only_run"] == "FORBIDDEN"
    assert config["execution"]["conditional_continuation"] == "FORBIDDEN"
    assert config["execution"]["intermediate_scientific_outcome_access"] == "FORBIDDEN"
    assert config["execution"]["registered_locked_pair_count"] == 100
    assert config["execution"]["unauthorized_or_out_of_workload_locked_pair_count"] == 0
    assert not config["authorization"]["locked_image_generation"]
    assert not config["authorization"]["locked_inference"]
    assert not config["authorization"]["resolution_reduction_inference"]


def test_primary_analysis_and_pipeline_amendments_are_machine_frozen():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(
        (root / "configs/stage0/overall_model_budget_design.yaml").read_text("utf-8")
    )
    primary = config["primary_analysis"]
    assert primary["budget_coding"] == "CATEGORICAL_WITH_B256_FULL_REFERENCE_NO_LINEAR_TREND"
    assert "(1 | pair_id:member)" in primary["full_formula"]
    assert "MODEL * BUDGET" in primary["full_formula"]
    assert "MODEL * BUDGET" not in primary["null_formula"]
    assert primary["confirmatory_test"]["reference_distribution"] == "CHI_SQUARE_DF_3"
    assert [entry["name"] for entry in primary["did_estimands"]] == [
        "DID_196",
        "DID_121",
        "DID_64",
    ]
    assert primary["multiplicity"]["method"] == "HOLM"
    assert primary["fallback"]["silent_switch"] == "FORBIDDEN"

    downsampling = config["intervention"]["downsampling"]
    assert downsampling["version"] == "12.3.0"
    assert downsampling["interpolation"] == "Image.Resampling.BICUBIC"
    assert downsampling["reducing_gap"] is None
    assert downsampling["forbidden"] == [
        "SHARPENING",
        "THRESHOLDING",
        "OCR_SPECIFIC_PREPROCESSING",
        "ADAPTIVE_PER_IMAGE_RESIZING",
        "EXIF_ROTATION",
    ]
    assert config["full_validity_condition"]["evaluated_after_complete_panel_is_immutable"]
    assert config["terminal_state"] == "FINAL_LOCKED_PANEL_AUTHORIZATION_READY"
    assert config["authorization"]["final_locked_panel_authorization_ready"]
    assert not config["authorization"]["locked_inference"]


def test_final_interpretation_and_execution_blinding_are_frozen():
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(
        (root / "configs/stage0/overall_model_budget_design.yaml").read_text("utf-8")
    )
    primary = config["primary_analysis"]
    assert primary["meaningful_effect"]["sesoi"] == 0.10
    assert not primary["confidence_intervals"]["holm_adjusted"]
    assert not primary["confidence_intervals"]["simultaneous"]
    logic = primary["interpretation_logic"]
    assert logic["meaningful_supported_label"] == "MEANINGFUL_MODEL_BUDGET_INTERACTION_SUPPORTED"
    assert logic["detected_below_sesoi_label"] == "INTERACTION_DETECTED_BELOW_PLANNED_SESOI"
    assert logic["suggestive_not_confirmed_label"] == "SUGGESTIVE_MEANINGFUL_INTERACTION_NOT_CONFIRMED"
    assert logic["no_confirmatory_evidence_label"] == "NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE"
    assert not logic["nonsignificant_is_equivalence"]
    assert not logic["nonsignificant_proves_equal_robustness"]
    execution = config["execution"]
    assert execution["scientific_output_unseal_requirements"] == [
        "ALL_6400_CALLS_COMPLETE",
        "ARTIFACTS_AND_CHECKSUMS_IMMUTABLE",
        "LOCAL_ARTIFACT_VERIFICATION_PASS",
    ]
