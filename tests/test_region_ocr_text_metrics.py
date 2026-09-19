"""Tests for region-OCR CER metrics (no model inference)."""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.text_metrics import (
    cer_summary,
    classify_component,
    codepoint_edit_distance,
    component_error_counts,
    macro_cer,
    micro_cer,
    oracle_page_text,
    region_cer,
)

# ก + ี (upper vowel) + ่ (tone mark)
KI_TONE = "กี่"
KI = "กี"


def test_edit_distance_matches_frozen_implementations() -> None:
    """Pin the reimplementation to the frozen Stage-0 versions."""
    from labbs2026.stage0.measurement_contract_pilot_run import _levenshtein
    from labbs2026.stage0.paddle_wayu_s0 import codepoint_edit_distance as frozen

    cases = [
        ("", ""),
        ("", "abc"),
        ("abc", ""),
        ("abc", "abc"),
        ("kitten", "sitting"),
        (KI_TONE, KI),
        (KI, KI_TONE),
        ("ก่ี", KI_TONE),
    ]
    for left, right in cases:
        expected = frozen(left, right)
        assert codepoint_edit_distance(left, right) == expected
        assert _levenshtein(left, right) == expected


def test_edit_distance_known_values() -> None:
    assert codepoint_edit_distance("kitten", "sitting") == 3
    assert codepoint_edit_distance(KI_TONE, KI) == 1
    assert codepoint_edit_distance("abc", "abc") == 0


def test_region_cer_basic() -> None:
    assert region_cer(KI_TONE, KI) == pytest.approx(1 / 3)
    assert region_cer(KI_TONE, KI_TONE) == 0.0


def test_region_cer_exceeds_one_for_degenerate_output() -> None:
    """A repetition loop must not be silently capped."""
    value = region_cer("ก", "ขขขข")
    assert value == pytest.approx(4.0)
    assert region_cer("ก", "ขขขข", clamp=True) == pytest.approx(1.0)


def test_region_cer_empty_reference_raises() -> None:
    with pytest.raises(ValueError):
        region_cer("", "anything")
    with pytest.raises(ValueError):
        micro_cer([("", "anything")])


def test_macro_and_micro_diverge_when_region_lengths_differ() -> None:
    records = [("ก", ""), ("ก" * 10, "ก" * 10)]
    assert macro_cer(records) == pytest.approx(0.5)
    assert micro_cer(records) == pytest.approx(1 / 11)


def test_macro_micro_agree_when_lengths_equal() -> None:
    records = [("ab", "ab"), ("cd", "cx")]
    assert macro_cer(records) == pytest.approx(0.25)
    assert micro_cer(records) == pytest.approx(0.25)


def test_empty_records_raise() -> None:
    with pytest.raises(ValueError):
        macro_cer([])
    with pytest.raises(ValueError):
        micro_cer([])


def test_cer_summary_reports_degenerate_counts() -> None:
    records = [("ก", "ขขขข"), ("ก" * 4, ""), (KI_TONE, KI_TONE)]
    summary = cer_summary(records)
    assert summary["region_count"] == 3
    assert summary["regions_over_one"] == 1
    assert summary["empty_hypotheses"] == 1
    assert summary["macro_cer"] == pytest.approx((4.0 + 1.0 + 0.0) / 3)
    assert summary["macro_cer_clamped"] == pytest.approx((1.0 + 1.0 + 0.0) / 3)
    assert summary["micro_cer"] == pytest.approx((4 + 4 + 0) / (1 + 4 + 3))


def test_oracle_page_text_uses_ground_truth_order() -> None:
    assert oracle_page_text(["a", "b", "c"]) == "a\nb\nc"
    assert oracle_page_text(["a", "b"], separator=" ") == "a b"


def test_classify_component_covers_thai_classes() -> None:
    assert classify_component("่") == "TONE_MARK"
    assert classify_component("ี") == "UPPER_VOWEL"
    assert classify_component("ุ") == "LOWER_VOWEL"
    assert classify_component("ก") == "BASE_CONSONANT"
    assert classify_component("ฮ") == "BASE_CONSONANT"
    assert classify_component("A") == "OTHER"


def test_component_error_counts_attributes_dropped_tone_mark() -> None:
    counts = component_error_counts(KI_TONE, KI)["components"]
    assert counts["TONE_MARK"]["reference_total"] == 1
    assert counts["TONE_MARK"]["deletion"] == 1
    assert counts["UPPER_VOWEL"]["reference_total"] == 1
    assert counts["UPPER_VOWEL"]["deletion"] == 0
    assert counts["BASE_CONSONANT"]["reference_total"] == 1


def test_component_error_counts_attributes_substitution() -> None:
    # ่ (U+0E48) replaced by ้ (U+0E49): one tone-mark substitution.
    counts = component_error_counts(KI_TONE, "กี้")["components"]
    assert counts["TONE_MARK"]["substitution"] == 1
    assert counts["TONE_MARK"]["deletion"] == 0


def test_component_error_counts_attributes_spurious_insertion() -> None:
    """A hallucinated tone mark is an insertion, attributed to the hypothesis."""
    result = component_error_counts(KI, KI_TONE)
    counts = result["components"]
    assert counts["TONE_MARK"]["insertion"] == 1
    assert counts["TONE_MARK"]["reference_total"] == 0
    assert counts["TONE_MARK"]["hypothesis_total"] == 1
    assert counts["TONE_MARK"]["deletion"] == 0
    assert result["totals"]["insertion"] == 1


@pytest.mark.parametrize(
    ("reference", "hypothesis"),
    [
        (KI_TONE, KI),
        (KI, KI_TONE),
        (KI_TONE, "กี้"),
        (KI_TONE, ""),
        (KI_TONE, "กุ่้ี"),
        ("kitten", "sitting"),
        ("ก" * 5, "ข" * 3),
        (KI_TONE, KI_TONE),
    ],
)
def test_component_operations_sum_to_edit_distance(reference: str, hypothesis: str) -> None:
    """Every edit must be attributed exactly once.

    The earlier implementation silently dropped insertions, so this invariant
    is what pins the backtrace rather than the individual count assertions.
    """
    totals = component_error_counts(reference, hypothesis)["totals"]
    attributed = totals["substitution"] + totals["deletion"] + totals["insertion"]
    assert attributed == codepoint_edit_distance(reference, hypothesis)


def test_component_error_counts_is_deterministic() -> None:
    first = component_error_counts(KI_TONE, KI)
    second = component_error_counts(KI_TONE, KI)
    assert first == second


def test_component_error_counts_perfect_match_has_no_errors() -> None:
    result = component_error_counts(KI_TONE, KI_TONE)
    assert result["totals"] == {"substitution": 0, "deletion": 0, "insertion": 0}
    for entry in result["components"].values():
        assert entry["substitution"] == 0
        assert entry["deletion"] == 0
        assert entry["insertion"] == 0
