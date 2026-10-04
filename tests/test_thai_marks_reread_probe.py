"""E2 per-view status."""

from __future__ import annotations

from labbs2026.thai_marks.reread_probe import view_status

LINE = "ข้าวราคาแพงขึ้นทุกวัน"


def test_right_wrong_and_not_found() -> None:
    i = LINE.index("ข")  # ข้
    assert view_status(LINE, i, ["อื่น ๆ\n" + LINE]) == "right"
    assert view_status(LINE, i, [LINE.replace("ข้าว", "ขาว")]) == "wrong"
    assert view_status(LINE, i, ["อะไรก็ไม่รู้ที่ไม่เกี่ยวกันเลยสักนิด"]) == "not_found"
    assert view_status(LINE, i, []) == "not_found"


def test_the_best_matching_read_of_a_view_is_used() -> None:
    i = LINE.index("ข")
    reads = [LINE.replace("ข้าว", "ขาว").replace("แพง", "แพม"), "ท้ายหน้า " + LINE]
    assert view_status(LINE, i, reads) == "right"
