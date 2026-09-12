from labbs2026.stage0.measurement_contract_pilot_run import classify_output, component_correct, normalize_output


def test_output_taxonomy_is_frozen_and_exact():
    assert classify_output(" กา\r\n", "กา", "ภา")["taxonomy"] == "correct_target"
    assert classify_output("ภา", "กา", "ภา")["taxonomy"] == "opposite_member_substitution"
    assert classify_output("", "กา", "ภา")["taxonomy"] == "deletion"
    assert classify_output("กา\nคำอธิบาย", "กา", "ภา")["taxonomy"] == "output_contract_failure"
    assert classify_output("ขา", "กา", "ภา")["taxonomy"] == "other_substitution"


def test_normalization_only_canonicalizes_line_endings_and_outer_space():
    assert normalize_output("  กา\r\nภา  ") == "กา\nภา"


def test_registered_component_scoring_rules():
    assert component_correct("กา", "กา", "BASE_CHARACTER")
    assert not component_correct("ขา", "กา", "BASE_CHARACTER")
    assert component_correct("ก่า", "ก่า", "TONE_MARK")
    assert component_correct("กิ", "กิ", "UPPER_VOWEL_VARIANT")
    assert component_correct("กู", "กู", "LOWER_VOWEL_VARIANT")
    assert component_correct("กี่", "กี่", "STACKED_TONE_MARK")
