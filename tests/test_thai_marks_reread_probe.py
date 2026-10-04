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


def test_majority_needs_more_than_half_and_keeps_own_otherwise() -> None:
    from labbs2026.thai_marks.reread_probe import majority

    assert majority("ข", ["ข้", "ข้", None]) == "ข้"      # 2 of 3 cast
    assert majority("ข", ["ข้", "ข่", "ขี"]) == "ข"         # no majority
    assert majority("ข", [None, None]) == "ข"


def test_flagged_edits_change_only_low_confidence_clusters_the_views_agree_on() -> None:
    from labbs2026.thai_marks.reread_probe import apply_edits, flagged_edits

    raw = "ขาวราคาแพงขึ้นทุกวัน"
    good = "ข้าวราคาแพงขึ้นทุกวัน"
    # page "ข" + two views "ข้" + one abstaining view: 2 of 3 votes cast
    views = {"a": [good], "b": [good], "c": ["อะไรก็ไม่รู้ที่ไม่เกี่ยวกันเลยสักนิด"]}
    clusters = [(0, 1, 2.0), (10, 13, 0.01)]  # ข flagged; ขึ้ not
    edits = flagged_edits(raw, clusters, views, threshold=0.5)
    assert edits == [(0, 1, "ข้")]
    assert apply_edits(raw, edits) == good
    assert flagged_edits(raw, [(0, 1, 0.1)], views, threshold=0.5) == []


def test_an_alignment_landing_on_a_mark_is_moved_to_its_consonant() -> None:
    from labbs2026.thai_marks.reread_probe import view_vote

    raw, good = "ขาวราคาแพงขึ้นทุกวัน", "ข้าวราคาแพงขึ้นทุกวัน"
    assert view_vote(raw, 0, [good]) == "ข้"
    assert view_status(raw.replace("ขาว", "ข้าว"), 0, [good]) == "right"
