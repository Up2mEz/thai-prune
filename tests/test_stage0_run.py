from copy import deepcopy

from labbs2026.stage0.kaggle_workload import derive_workload
from labbs2026.stage0.run import calibration_readiness_issues, make_observation_plan


def _frozen_config() -> dict:
    return {
        "status": "FROZEN_CALIBRATION",
        "compression_family": "FULL_INFORMATION",
        "allocation": {
            "calibration_pair_ids": ["p1"],
            "locked_validation_pair_ids": ["p2"],
        },
        "render_condition_selection": {"selected_condition_ids": ["c1"]},
        "controls": {
            "language_candidate_bias_blank_image": True,
            "language_candidate_bias_blank_pair_ids": ["p1"],
        },
        "reproducibility": {"seed": 7, "exact_rerun": True},
        "gate_0": {"criteria": None},
        "locked_validation": {"authorized": False},
    }


def _review() -> dict:
    return {
        "decision": "APPROVED_FOR_CALIBRATION",
        "approved_pair_ids": ["p1", "p2"],
        "approved_condition_ids": ["c1"],
        "prompt_parser_approved": True,
    }


def test_current_unfrozen_design_is_fail_closed() -> None:
    config = _frozen_config()
    config["status"] = "PROPOSED_NOT_FROZEN"

    issues = calibration_readiness_issues(config, _review())

    assert "CALIBRATION_DESIGN_NOT_FROZEN" in issues


def test_pair_overlap_is_rejected() -> None:
    config = _frozen_config()
    config["allocation"]["locked_validation_pair_ids"] = ["p1"]

    assert "PAIR_SPLIT_OVERLAP" in calibration_readiness_issues(config, _review())


def test_observation_plan_balances_labels_and_separates_controls() -> None:
    config = _frozen_config()
    pairs = [{"pair_id": "p1", "component_type": "TONE_MARK", "text_a": "กา", "text_b": "ก่า", "lexical_status_a": "REAL", "lexical_status_b": "UNCERTAIN"}]
    renders = [{"pair_id": "p1", "condition_id": "c1", "image_a_path": "a.png", "image_b_path": "b.png"}]

    observations = make_observation_plan(config, pairs, renders, "A. {candidate_a}\nB. {candidate_b}")

    assert len(observations) == 4
    assert sum(row["control_type"] == "FULL_INFORMATION" for row in observations) == 2
    assert sum(row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK" for row in observations) == 2
    assert {row["expected_label"] for row in observations if row["control_type"] == "FULL_INFORMATION"} == {"A", "B"}
    assert {
        row["expected_label"]
        for row in observations
        if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
    } == {None}


def test_workload_is_not_exact_before_human_freeze() -> None:
    config = deepcopy(_frozen_config())
    config["allocation"]["calibration_pair_ids"] = None

    workload = derive_workload(config, _review(), [], [], "A. {candidate_a}\nB. {candidate_b}")

    assert workload["status"] == "BLOCKED_PENDING_HUMAN_FREEZE"
    assert workload["exact_observation_count"] is None


def test_workload_reports_exact_calls_after_freeze() -> None:
    config = _frozen_config()
    pairs = [{"pair_id": "p1", "component_type": "TONE_MARK", "text_a": "กา", "text_b": "ก่า", "lexical_status_a": "REAL", "lexical_status_b": "UNCERTAIN"}]
    renders = [{"pair_id": "p1", "condition_id": "c1", "image_a_path": "a.png", "image_b_path": "b.png"}]

    workload = derive_workload(config, _review(), pairs, renders, "A. {candidate_a}\nB. {candidate_b}")

    assert workload["status"] == "READY_FOR_CALIBRATION_SUBMISSION"
    assert workload["exact_observation_count"] == 4
    assert workload["total_model_calls_including_rerun"] == 8
    assert not workload["locked_validation_included"]
