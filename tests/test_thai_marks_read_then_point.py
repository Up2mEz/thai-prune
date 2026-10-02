"""Read-then-point picks the TC stretch the BQ answer points at."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.read_then_point import point, similarity, transcription_lines

TC = "ร้านอาหารครัวไทย\nเปิดทุกวัน 08.00 - 20.00 น.\nโทร 02-123-4567\nยินดีต้อนรับ"


def test_similarity_bounds() -> None:
    assert similarity("", "") == 1.0
    assert similarity("abc", "abc") == 1.0
    assert similarity("abc", "xyz") == 0.0


def test_lines_are_extracted_and_empty_ones_dropped() -> None:
    assert transcription_lines("# หัวข้อ\n\n**ตัวหนา**") == ["หัวข้อ", "ตัวหนา"]


def test_a_misread_pointer_is_replaced_by_the_better_tc_reading() -> None:
    out = point("เปิดทุกวน 08.00 - 20.00 น", TC)
    assert out["answer"] == "เปิดทุกวัน 08.00 - 20.00 น." and not out["fell_back"]


def test_a_pointer_spanning_two_lines_picks_both() -> None:
    out = point("เปิดทุกวัน 08.00 - 20.00 น. โทร 02-123-4567", TC)
    assert out["lines"] == (1, 3)


def test_no_match_falls_back_to_the_pointer() -> None:
    out = point("I do not know what Thai text is in the image", TC)
    assert out["fell_back"] and out["answer"] == "I do not know what Thai text is in the image"


def test_empty_tc_falls_back() -> None:
    out = point("ร้านอาหาร", "")
    assert out["fell_back"] and out["similarity"] is None


def test_ties_go_to_the_shorter_then_earlier_candidate() -> None:
    out = point("abc", "abc\nabc")
    assert out["lines"] == (0, 1)


@pytest.mark.parametrize("bq", ["ร้านอาหารครัวไทย", "ยินดีต้อนรับ"])
def test_an_exact_pointer_returns_its_own_line(bq: str) -> None:
    assert point(bq, TC)["answer"] == bq
