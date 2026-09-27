from labbs2026.stage0.backbone_calibration import (
    _exact_rerun,
    _smoke_acceptance,
    select_smoke_observations,
)


EXPECTED = {
    "original_image_shape": [448, 448],
    "preprocessed_image_shape": [448, 448],
    "image_grid_thw": [1, 28, 28],
    "premerge_patch_count": 784,
    "runtime_premerge_patch_count": 784,
    "llm_visual_token_count": 196,
    "input_image_token_count": 196,
    "runtime_vision_output_count": 196,
    "runtime_llm_input_position_count": 196,
}


def _row(index: int) -> dict:
    label = "A" if index % 2 == 0 else "B"
    return {
        "observation_id": str(index),
        "raw_output": label,
        "generated_token_ids": [32 if label == "A" else 33],
        "parse_status": "PARSED",
        "output_contract_conformance": True,
        "resolved_generation_config": {
            "do_sample": False,
            "max_new_tokens": 1,
            "min_new_tokens": 1,
        },
        "generate_direct_exact": True,
        "binary_prediction": label,
        "logit_A": float(index + (1 if label == "A" else 0)),
        "logit_B": float(index + (1 if label == "B" else 0)),
        "visual_stage_metadata": EXPECTED,
    }


def test_smoke_acceptance_requires_all_runtime_contracts_and_exact_rerun() -> None:
    first = [_row(index) for index in range(20)]
    second = [dict(row) for row in first]
    assert _smoke_acceptance(first, second, EXPECTED)["status"] == "PASS"
    second[0]["visual_stage_metadata"] = {**EXPECTED, "llm_visual_token_count": 195}
    assert _smoke_acceptance(first, second, EXPECTED)["status"] == "FAIL"


def test_full_rerun_requires_one_thousand_exact_observation_ids() -> None:
    first = [_row(index) for index in range(1000)]
    second = [dict(row) for row in first]
    assert _exact_rerun(first, second)["status"] == "EXACT"
    second[1]["logit_A"] += 0.01
    result = _exact_rerun(first, second)
    assert result["status"] == "MISMATCH"
    assert result["mismatch_count"] == 1


def test_smoke_selection_is_predeclared_deterministic_and_excludes_locked() -> None:
    observations = [
        {
            "observation_id": observation_id,
            "pair_id": pair_id,
            "condition_id": condition,
            "control_type": control,
        }
        for observation_id, pair_id, condition, control in (
            ("z", "open_a", "frozen", "FULL_INFORMATION"),
            ("a", "open_a", "NO_VISUAL_CONTENT", "LANGUAGE_CANDIDATE_BIAS_BLANK"),
            ("m", "open_a", "other", "FULL_INFORMATION"),
            ("b", "locked_a", "frozen", "FULL_INFORMATION"),
        )
    ]
    smoke = {"pair_ids": ["open_a"], "condition_id": "frozen"}

    selected = select_smoke_observations(observations, smoke)

    assert [row["observation_id"] for row in selected] == ["a", "z"]
    assert {row["pair_id"] for row in selected} == {"open_a"}
