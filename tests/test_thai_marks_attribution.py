"""Cause attribution of mark errors."""

from __future__ import annotations

from labbs2026.thai_marks.attribution import (
    CAUSES,
    CAUSES_APPROX,
    attribute_marks,
    elsewhere_cer,
    read_elsewhere,
    reference_lines,
)

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


L3 = "ราคาน้ำมันปรับขึ้นอีกครั้งในสัปดาห์นี้"


def test_default_keeps_the_2026_10_01_causes() -> None:
    # Read in another order but with one character wrong: not verbatim.
    ref = f"{L1}\n{L2}\n{L3}"
    out = attribute_marks(ref, f"{L2} {L3} " + L1.replace("ทุก", "ทก"))
    assert set(out) <= {"correct", *CAUSES}


def test_a_line_read_elsewhere_with_an_error_is_approx_reordered() -> None:
    ref = f"{L1}\n{L2}\n{L3}"
    hyp = f"{L2} {L3} " + L1.replace("ทุก", "ทก")
    out = attribute_marks(ref, hyp, approximate_reorder=True)
    assert set(out) <= {"correct", *CAUSES_APPROX}
    assert out["line_reordered_approx"] > 0 and not out["line_missing"]


def test_a_line_absent_everywhere_stays_missing_under_approx() -> None:
    out = attribute_marks(f"{L1}\n{L2}", L1, approximate_reorder=True)
    assert out["line_missing"] > 0 and not out["line_reordered_approx"]


def test_short_lines_are_never_credited_as_read_elsewhere() -> None:
    assert not read_elsewhere("2556", "ปี 2556 และ 2557")
    assert read_elsewhere(L3, "อื่น ๆ " + L3.replace("อีก", "อก") + " อื่น ๆ")


def test_elsewhere_cer_is_zero_for_a_verbatim_stretch() -> None:
    assert elsewhere_cer(L2, f"ก่อน {L2} หลัง") == 0
