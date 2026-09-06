import math

import pytest

from labbs2026.stage0.margin_diagnostic import (
    _canonical_margin,
    _correct_margin,
    _enrich_image_gain,
    _paired_pair_contrast,
    _position_margin,
    _smoke_acceptance,
)


def test_registered_margin_sign_conventions() -> None:
    position = _position_margin(3.25, 1.0)

    assert position == 2.25
    assert _canonical_margin(position, "A_THEN_B") == 2.25
    assert _canonical_margin(position, "B_THEN_A") == -2.25
    assert _correct_margin(position, "A") == 2.25
    assert _correct_margin(position, "B") == -2.25
    assert _correct_margin(position, None) is None


def test_image_gain_uses_matched_pair_and_orientation_blank() -> None:
    full = {
        "observation_id": "full|p1|c1|a",
        "pair_id": "p1",
        "orientation": "B_THEN_A",
        "control_type": "FULL_INFORMATION",
        "expected_label": "B",
        "position_margin": -3.0,
        "canonical_member_margin": 3.0,
        "correct_margin": 3.0,
    }
    blank = {
        "observation_id": "blank_bias|p1|B_THEN_A",
        "pair_id": "p1",
        "orientation": "B_THEN_A",
        "control_type": "LANGUAGE_CANDIDATE_BIAS_BLANK",
        "expected_label": None,
        "position_margin": -1.0,
        "canonical_member_margin": 1.0,
        "correct_margin": None,
    }

    enriched = _enrich_image_gain([full, blank])

    assert enriched[0]["matched_blank_observation_id"] == blank["observation_id"]
    assert enriched[0]["matched_blank_correct_margin"] == 1.0
    assert enriched[0]["image_gain"] == 2.0
    assert enriched[1]["image_gain"] is None


def _smoke_row(observation_id: str, logit_a: float, logit_b: float) -> dict:
    return {
        "observation_id": observation_id,
        "output_contract": {"label_token_ids": {"A": 32, "B": 33}},
        "generate_direct_exact": True,
        "binary_reference_agrees": True,
        "binary_prediction": "A" if logit_a >= logit_b else "B",
        "logit_A": logit_a,
        "logit_B": logit_b,
        "llm_visual_token_count": 256,
    }


def test_smoke_requires_exact_margin_rerun_reproducibility() -> None:
    first = [_smoke_row(str(index), 2.0 + index, 1.0) for index in range(20)]
    second = [dict(row) for row in first]

    assert _smoke_acceptance(first, second)["status"] == "PASS"
    second[0]["logit_A"] = math.nextafter(second[0]["logit_A"], math.inf)
    assert _smoke_acceptance(first, second)["status"] == "FAIL"


def test_paired_contrast_uses_pair_as_independent_unit() -> None:
    rows = [
        {"pair_id": "p1", "size": 72, "value": 1.0},
        {"pair_id": "p1", "size": 96, "value": 3.0},
        {"pair_id": "p2", "size": 72, "value": 10.0},
        {"pair_id": "p2", "size": 96, "value": 11.0},
    ]

    result = _paired_pair_contrast(
        rows, outcome="value", grouping="size", positive=96, negative=72,
        seed=1, resamples=100, confidence=0.95,
    )

    assert result["estimate"] == 1.5
    assert result["pair_count"] == 2


@pytest.mark.parametrize("orientation", ["UNKNOWN", ""])
def test_unknown_orientation_fails_closed(orientation: str) -> None:
    with pytest.raises(ValueError):
        _canonical_margin(1.0, orientation)
