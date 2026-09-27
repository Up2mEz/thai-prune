import pytest

from labbs2026.stage0.locked_panel_analysis import derive_outcomes
from labbs2026.stage0.paddle_wayu_locked_panel import (
    U_FFFD_FAILURE_REASON,
    build_workload,
    decode_generated_tokens,
    engineering_progress_message,
)


class _SyntheticTokenizer:
    eos_token_id = 2


class _SyntheticProcessor:
    tokenizer = _SyntheticTokenizer()

    def __init__(self) -> None:
        self.calls: list[list[int]] = []

    def decode(self, token_ids, **kwargs):
        assert kwargs == {
            "skip_special_tokens": True,
            "clean_up_tokenization_spaces": False,
        }
        ids = list(token_ids)
        self.calls.append(ids)
        if ids == [999]:
            raise ValueError("synthetic fatal decoder exception")
        return {94377: "\ufffd", 10: "ก"}[ids[0]]


def test_locked_panel_workload_is_exactly_6400_unique_calls() -> None:
    locked = [f"p{i:03d}" for i in range(100)]
    conditions = ["c1", "c2", "c3", "c4"]
    design = {
        "models": [
            {"role": "BASE", "model_id": "base", "revision": "r1"},
            {"role": "SPECIALIZED", "model_id": "specialized", "revision": "r2"},
        ],
        "dataset": {"members": ["a", "b"], "render_conditions": conditions},
        "intervention": {
            "budgets": [
                {"budget_id": "B256_FULL", "input_resolution": [448, 448], "min_pixels": 448**2, "max_pixels": 448**2, "image_grid_thw": [1, 32, 32], "pre_merge_patches": 1024, "llm_image_placeholders": 256},
                {"budget_id": "B196", "input_resolution": [392, 392], "min_pixels": 392**2, "max_pixels": 392**2, "image_grid_thw": [1, 28, 28], "pre_merge_patches": 784, "llm_image_placeholders": 196},
                {"budget_id": "B121", "input_resolution": [308, 308], "min_pixels": 308**2, "max_pixels": 308**2, "image_grid_thw": [1, 22, 22], "pre_merge_patches": 484, "llm_image_placeholders": 121},
                {"budget_id": "B64", "input_resolution": [224, 224], "min_pixels": 224**2, "max_pixels": 224**2, "image_grid_thw": [1, 16, 16], "pre_merge_patches": 256, "llm_image_placeholders": 64},
            ]
        },
        "prompt": "OCR:",
    }
    allocation = {"allocation": {"locked_validation_pair_ids": locked}}
    components = [
        "BASE_CHARACTER",
        "TONE_MARK",
        "UPPER_VOWEL_VARIANT",
        "LOWER_VOWEL_VARIANT",
        "STACKED_TONE_MARK",
    ]
    pairs = [
        {"pair_id": pair_id, "component_type": components[index // 20], "text_a": "ก", "text_b": "ข"}
        for index, pair_id in enumerate(locked)
    ]
    renders = []
    for pair_id in locked:
        for condition in conditions:
            renders.append({
                "pair_id": pair_id,
                "condition_id": condition,
                "font_id": condition,
                "font_size": 72,
                "image_a_path": f"{pair_id}/a.png",
                "image_a_sha256": "a" * 64,
                "image_b_path": f"{pair_id}/b.png",
                "image_b_sha256": "b" * 64,
            })
    workload = build_workload(design, allocation, pairs, renders)
    assert len(workload) == 6400
    assert len({row["call_id"] for row in workload}) == 6400
    assert sum(row["model_role"] == "BASE" for row in workload) == 3200
    assert sum(row["budget_id"] == "B64" for row in workload) == 1600


def test_u_fffd_is_retained_per_call_and_execution_can_continue_without_retry() -> None:
    processor = _SyntheticProcessor()
    first = decode_generated_tokens(processor, [94377], max_new_tokens=32)
    second = decode_generated_tokens(processor, [10, 2], max_new_tokens=32)

    assert first == {
        "raw_output": "\ufffd",
        "u_fffd_present": True,
        "output_contract_failure": True,
        "output_contract_failure_reason": U_FFFD_FAILURE_REASON,
        "generated_token_count": 1,
        "eos_reached": False,
        "max_new_tokens_reached": False,
    }
    assert second["raw_output"] == "ก"
    assert not second["output_contract_failure"]
    assert processor.calls == [[94377], [10, 2]]


def test_u_fffd_is_exact_zero_retained_in_denominator_and_cer_uses_codepoints() -> None:
    common = {
        "pair_id": "p001",
        "model_role": "BASE",
        "budget_id": "B256_FULL",
        "font_id": "font",
        "font_size": 72,
        "member": "a",
        "component_type": "BASE_CHARACTER",
        "target": "ก",
        "opposite_member": "ข",
    }
    rows = derive_outcomes([
        {**common, "call_id": "failed", "raw_output": "\ufffd"},
        {**common, "call_id": "next", "raw_output": "ก"},
    ])
    assert len(rows) == 2
    assert rows[0]["exact_correct"] == 0
    assert rows[0]["codepoint_cer"] == 1.0
    assert rows[0]["error_category"] == "output_contract_failure"
    assert rows[0]["output_contract_failure"]
    assert rows[0]["output_contract_failure_reason"] == U_FFFD_FAILURE_REASON
    assert rows[0]["u_fffd_present"]
    assert rows[1]["exact_correct"] == 1


def test_live_progress_is_blinded_and_fatal_decode_exceptions_remain_fatal() -> None:
    message = engineering_progress_message(100)
    assert message == "ENGINEERING_PROGRESS completed_calls=100/6400"
    for forbidden in ("U+FFFD", "94377", "model", "budget", "pair", "decoded"):
        assert forbidden not in message

    with pytest.raises(ValueError, match="synthetic fatal decoder exception"):
        decode_generated_tokens(_SyntheticProcessor(), [999], max_new_tokens=32)
