from __future__ import annotations

from pathlib import Path

import yaml

from labbs2026.stage0.paddle_wayu_smoke import (
    audit_locked_set,
    build_workload,
    cross_model_prompt_consistency,
    repeat_consistency,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_engineering_smoke.yaml"
DESIGN = ROOT / "configs/stage0/calibration_design.yaml"


def _yaml(path: Path):
    return yaml.safe_load(path.read_text("utf-8"))


def test_frozen_workload_is_exactly_40_calls_and_reuses_images() -> None:
    calls = build_workload(_yaml(CONFIG))
    assert len(calls) == 40
    assert {row["prompt"] for row in calls} == {"OCR:"}
    assert len({row["pair_id"] for row in calls}) == 5
    assert len({(row["pair_id"], row["member"]) for row in calls}) == 10
    by_image = {}
    for row in calls:
        by_image.setdefault((row["pair_id"], row["member"]), set()).add(
            row["image_sha256"]
        )
    assert all(len(hashes) == 1 for hashes in by_image.values())


def test_selected_pairs_are_open_calibration_and_never_locked() -> None:
    result = audit_locked_set(_yaml(CONFIG), _yaml(DESIGN))
    assert result["valid"] is True
    assert result["locked_pair_count"] == 0
    assert len(result["already_exposed_open_calibration_pair_ids"]) == 5


def test_repeat_and_cross_model_checks_do_not_compare_model_outputs() -> None:
    records = []
    for role in ("BASE", "SPECIALIZED"):
        for repeat in (1, 2):
            records.append(
                {
                    "model_role": role,
                    "pair_id": "pair",
                    "member": "a",
                    "repeat": repeat,
                    "prompt": "OCR:",
                    "image_sha256": "same-image",
                    "input_token_ids": [1, 2, 3],
                    "generated_token_ids": [10] if role == "BASE" else [20],
                    "decoded_output": "wrong-a" if role == "BASE" else "wrong-b",
                    "image_grid_thw": [1, 32, 32],
                    "visual_token_counts": {
                        "pre_merge": 1024,
                        "projector_output": 256,
                        "llm_image_placeholders": 256,
                    },
                    "intermediate_shapes": {
                        "projector": [{"shape": [1, 256, 1024]}]
                    },
                }
            )
    assert repeat_consistency(records)["all_exact_repeats_consistent"] is True
    assert cross_model_prompt_consistency(records)["all_consistent"] is True


def test_repeat_check_fails_when_generated_ids_change() -> None:
    records = []
    for repeat, token in ((1, 10), (2, 11)):
        records.append(
            {
                "model_role": "BASE",
                "pair_id": "pair",
                "member": "a",
                "repeat": repeat,
                "input_token_ids": [1],
                "generated_token_ids": [token],
                "decoded_output": str(token),
                "image_grid_thw": [1, 1, 1],
                "visual_token_counts": {},
                "intermediate_shapes": {},
            }
        )
    assert repeat_consistency(records)["all_exact_repeats_consistent"] is False
