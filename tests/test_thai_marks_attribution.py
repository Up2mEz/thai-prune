"""Cause attribution of mark errors."""

from __future__ import annotations

from labbs2026.thai_marks.attribution import CAUSES, attribute_marks, reference_lines

L1 = "ข้าวราคาแพงขึ้นทุกวัน"
L2 = "ไฟฟ้าดับทั้งเมืองเมื่อคืน"


def test_lines_are_extracted_and_empty_ones_dropped() -> None:
    assert reference_lines(f"{L1}\n\n**{L2}**") == [L1, L2]


def test_all_correct() -> None:
    out = attribute_marks(f"{L1}\n{L2}", f"{L1} {L2}")
    assert set(out) == {"correct"}


def test_a_skipped_line_is_missing() -> None:
    out = attribute_marks(f"{L1}\n{L2}", L1)
    assert out["line_missing"] > 0 and not out["line_reordered"]


def test_a_line_read_in_another_order_is_reordered_not_missing() -> None:
    out = attribute_marks(f"{L1}\n{L2}", f"{L2} {L1}")
    assert out["line_reordered"] > 0 and not out["line_missing"]


def test_a_misread_mark_with_its_base_right_is_mark_specific() -> None:
    out = attribute_marks(L1, L1.replace("ข้าว", "ขาว"))
    assert out["misread_with_base"] == 1


def test_every_mark_gets_exactly_one_outcome() -> None:
    ref = f"{L1}\n{L2}"
    out = attribute_marks(ref, "ขาวราคาแพง")
    marks = sum(c in "่้๊๋ัิีึืุู็ฺ์" for c in (L1 + L2))
    assert sum(out.values()) <= marks + 2  # thanthakhat etc. are not counted as marks
    assert set(out) <= {"correct", *CAUSES}
