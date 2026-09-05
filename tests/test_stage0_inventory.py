from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _yaml(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_expanded_inventory_has_pair_level_granularity_floor() -> None:
    inventory = _yaml("configs/stage0/candidate_pairs.yaml")
    pairs = inventory["pairs"]
    counts = Counter(pair["component_type"] for pair in pairs)

    assert counts == {
        "BASE_CHARACTER": 40,
        "TONE_MARK": 40,
        "UPPER_VOWEL_VARIANT": 40,
        "LOWER_VOWEL_VARIANT": 40,
        "STACKED_TONE_MARK": 40,
    }
    assert len({pair["pair_id"] for pair in pairs}) == len(pairs)
    assert len({tuple(sorted((pair["text_a"], pair["text_b"]))) for pair in pairs}) == len(pairs)
    assert all(
        pair[f"lexical_status_{member}"] in {"REAL", "CONSTRUCTED", "UNCERTAIN"}
        for pair in pairs
        for member in ("a", "b")
    )


def test_base_pairs_do_not_reuse_members_within_proposed_split() -> None:
    pairs = [
        pair
        for pair in _yaml("configs/stage0/candidate_pairs.yaml")["pairs"]
        if pair["component_type"] == "BASE_CHARACTER"
    ]

    for split in ("CALIBRATION", "LOCKED_VALIDATION"):
        members = [
            pair[f"text_{member}"]
            for pair in pairs
            if pair["proposed_split"] == split
            for member in ("a", "b")
        ]
        assert len(members) == 40
        assert len(set(members)) == 40
    assert all(
        pair["stage2_size_match_status"] == "NOT_ASSESSED_NOT_ASSUMED"
        for pair in pairs
    )


def test_proposed_design_is_disjoint_and_has_exact_precalibration_workload() -> None:
    design = _yaml("configs/stage0/calibration_design.yaml")
    calibration = design["allocation"]["calibration_pair_ids"]
    locked = design["allocation"]["locked_validation_pair_ids"]
    conditions = design["render_condition_selection"]["selected_condition_ids"]
    blank = design["controls"]["language_candidate_bias_blank_pair_ids"]

    assert len(calibration) == len(locked) == 100
    assert not set(calibration) & set(locked)
    assert blank == calibration
    assert len(conditions) == 4
    assert len(calibration) * len(conditions) * 2 == 800
    assert len(blank) * 2 == 200
    assert (800 + 200) * 2 == 2000
    assert design["gate_0"]["criteria"] is None
    assert design["locked_validation"]["authorized"] is False
