"""Order-free mark precision/recall (diagnostic draft)."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.order_free import mark_counts, prf

L1 = "ข้าวราคาแพงขึ้นทุกวัน"
L2 = "ไฟฟ้าดับทั้งเมืองเมื่อคืน"
L3 = "ราคาน้ำมันปรับขึ้นอีกครั้งในสัปดาห์นี้"
REF = f"{L1}\n{L2}\n{L3}"


def _score(ref: str, out: str, mode: str = "line_matched") -> dict:
    return prf([mark_counts(ref, out, mode=mode)])


def test_a_perfect_read_scores_one_in_both_modes() -> None:
    for mode in ("line_matched", "global"):
        s = _score(REF, f"{L1} {L2} {L3}", mode)
        assert s["recall"] == s["precision"] == s["f1"] == 1


def test_reordered_lines_get_full_recall_only_when_order_free() -> None:
    out = f"{L3} {L1} {L2}"
    assert _score(REF, out)["recall"] == 1
    assert _score(REF, out, "global")["recall"] < 1


def test_a_duplicated_output_keeps_recall_and_halves_precision() -> None:
    s = _score(REF, f"{L1} {L2} {L3} {L1} {L2} {L3}")
    assert s["recall"] == 1
    assert s["precision"] == pytest.approx(0.5)


def test_one_output_stretch_never_credits_two_lines() -> None:
    s = _score(f"{L3}\n{L3}", L3)
    assert s["recall"] == pytest.approx(0.5)
    assert s["precision"] == 1


def test_a_missing_line_costs_recall_not_precision() -> None:
    s = _score(REF, f"{L1} {L3}")
    assert s["precision"] == 1 and s["recall"] < 1


def test_a_wrong_mark_costs_both() -> None:
    s = _score(REF, f"{L1.replace('ข้าว', 'ข่าว')} {L2} {L3}")
    assert s["precision"] < 1 and s["recall"] < 1


def test_short_lines_are_never_matched_and_are_reported() -> None:
    c = mark_counts(f"{L1}\nข่าว", f"{L1} ข่าว")
    assert c["short_line_marks"] == 1
    assert prf([c])["recall"] < 1


def test_a_line_far_from_the_output_is_not_matched() -> None:
    c = mark_counts(L3, "อะไรก็ไม่รู้ที่ไม่เกี่ยวกันเลยสักนิด")
    assert c["matched_lines"] == 0 and c["correct"] == 0


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        mark_counts(L1, L1, mode="anchored")
