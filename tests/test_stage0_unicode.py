import pytest

from labbs2026.stage0.unicode_checks import codepoints, validate_pair


@pytest.mark.parametrize(
    ("text_a", "text_b", "rule"),
    [
        ("กา", "ภา", "BASE_SUBSTITUTION"),
        ("กา", "ก่า", "MAI_EK_ADDITION"),
        ("กิ", "กี", "UPPER_VOWEL_SUBSTITUTION"),
        ("กุ", "กู", "LOWER_VOWEL_SUBSTITUTION"),
        ("กี", "กี่", "MAI_EK_IN_UPPER_CONTEXT"),
    ],
)
def test_candidate_difference_rules_accept_intended_thai_pairs(
    text_a: str, text_b: str, rule: str
) -> None:
    result = validate_pair(text_a, text_b, rule)

    assert result.valid
    assert result.issues == ()


def test_unicode_record_preserves_combining_mark_codepoints() -> None:
    result = validate_pair("กี", "กี่", "MAI_EK_IN_UPPER_CONTEXT")

    assert result.codepoints_a == ("U+0E01", "U+0E35")
    assert result.codepoints_b == ("U+0E01", "U+0E35", "U+0E48")
    assert codepoints("กี่") == result.codepoints_b


def test_wrong_component_rule_is_rejected() -> None:
    result = validate_pair("กิ", "กี", "MAI_EK_ADDITION")

    assert not result.valid
    assert "DIFFERENCE_RULE_MISMATCH" in result.issues


def test_non_thai_content_is_rejected() -> None:
    result = validate_pair("A", "B", "BASE_SUBSTITUTION")

    assert not result.valid
    assert "NON_THAI_CODEPOINT_A" in result.issues
    assert "NON_THAI_CODEPOINT_B" in result.issues
