"""Cause attribution of mark errors."""

from __future__ import annotations

from labbs2026.thai_marks.attribution import (
    CAUSES,
    CAUSES_APPROX,
    attribute_marks,
    elsewhere_cer,
    find_elsewhere,
    read_elsewhere,
    reference_lines,
    whole_line_causes,
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


def test_a_stretch_already_credited_is_not_credited_twice() -> None:
    # L3 appears twice in the reference and once in the output: one copy is
    # read, the other is missing, not "read elsewhere" from the same text.
    out = attribute_marks(f"{L3}\n{L1}\n{L3}", f"{L3} {L1}", approximate_reorder=True)
    assert out["line_missing"] > 0 and not out["line_reordered_approx"]


def test_read_elsewhere_respects_used_indices() -> None:
    hyp = f"ก่อน {L3} หลัง"
    assert read_elsewhere(L3, hyp)
    assert not read_elsewhere(L3, hyp, used=set(range(len(hyp))))


def test_a_credited_stretch_cannot_be_found_again() -> None:
    hyp, used = f"ก่อน {L3} หลัง", set()
    found, stretch = find_elsewhere(L3, hyp, used)
    assert found == "verbatim"
    used.update(stretch)  # as attribute_marks does after crediting a line
    assert find_elsewhere(L3, hyp, used)[0] is None
    assert find_elsewhere(L3.replace("อีก", "อก"), hyp, used)[0] is None


def test_short_verbatim_lines_are_not_credited_under_approx() -> None:
    assert find_elsewhere("2556", "ปี 2556") == (None, range(0))


def test_whole_line_causes_per_line() -> None:
    ref = f"{L1}\n{L2}\n{L3}"
    hyp = f"{L2} {L3} " + L1.replace("ทุก", "ทก")
    assert whole_line_causes(ref, hyp) == ["line_reordered_approx", None, None]
    assert whole_line_causes(f"{L1}\n{L2}", L1) == [None, "line_missing"]
