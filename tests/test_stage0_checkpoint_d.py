from labbs2026.stage0.checkpoint_d import (
    _blank_maps,
    _paired_effect,
    _prior_alignment,
    canonical_member_for_choice,
)


def _row(pair_id: str, orientation: str, choice: str, correct: bool | None) -> dict:
    return {
        "pair_id": pair_id,
        "orientation": orientation,
        "parsed_output": choice,
        "is_correct": correct,
    }


def test_canonical_member_mapping_is_distinct_from_display_position() -> None:
    assert canonical_member_for_choice(_row("p", "A_THEN_B", "A", True), "A") == "a"
    assert canonical_member_for_choice(_row("p", "A_THEN_B", "B", True), "B") == "b"
    assert canonical_member_for_choice(_row("p", "B_THEN_A", "A", True), "A") == "b"
    assert canonical_member_for_choice(_row("p", "B_THEN_A", "B", True), "B") == "a"


def test_prior_alignment_uses_matching_orientation_and_reports_pair_ties() -> None:
    blanks = [
        _row("p1", "A_THEN_B", "A", None),
        _row("p1", "B_THEN_A", "B", None),
        _row("p2", "A_THEN_B", "A", None),
        _row("p2", "B_THEN_A", "A", None),
    ]
    matched, pair_summary = _blank_maps(blanks)
    assert pair_summary["p1"]["blank_preferred_member"] == "a"
    assert pair_summary["p2"]["blank_preferred_member"] == "TIE"

    errors = [
        _row("p1", "A_THEN_B", "A", False),
        _row("p2", "B_THEN_A", "A", False),
    ]
    result = _prior_alignment(errors, matched, pair_summary)
    assert result["matched_orientation_prior_aligned_error_rate"] == 1.0
    assert result["unique_pair_preference_eligible_error_count"] == 1
    assert result["unique_pair_preference_aligned_error_rate"] == 1.0


def test_paired_effect_bootstrap_keeps_replacement_multiplicity() -> None:
    rows = []
    for pair_id, low, high in (("p1", False, True), ("p2", False, False)):
        rows.extend(
            [
                {"pair_id": pair_id, "condition": "low", "is_correct": low},
                {"pair_id": pair_id, "condition": "high", "is_correct": high},
            ]
        )
    result = _paired_effect(
        rows,
        high_filter=lambda row: row["condition"] == "high",
        low_filter=lambda row: row["condition"] == "low",
        seed=7,
        resamples=200,
        confidence_level=0.95,
        label="test",
    )
    assert result["estimate"] == 0.5
    assert result["lower"] == 0.0
    assert result["upper"] == 1.0
