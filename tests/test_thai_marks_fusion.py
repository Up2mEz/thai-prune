"""R-FUSE merge rule."""

from __future__ import annotations

from labbs2026.thai_marks.fusion import concatenate, fuse

HEAD = "ประกาศกรมราชทัณฑ์ ฉบับที่ 1"
BODY = " ผู้ต้องขังทุกคนต้องปฏิบัติตามระเบียบ"


def test_a_block_only_the_second_read_has_is_inserted_where_it_belongs() -> None:
    assert fuse(BODY.strip(), HEAD + BODY) == (HEAD + BODY)


def test_short_differences_are_not_inserted() -> None:
    assert fuse("ไฟฟ้าดับ", "ไฟฟ้าดับนาน") == "ไฟฟ้าดับ"


def test_disagreeing_characters_keep_the_anchor() -> None:
    assert fuse("ข้าวราคาแพง", "ขาวราคาแพง") == "ข้าวราคาแพง"


def test_a_block_the_anchor_read_elsewhere_is_not_inserted_twice() -> None:
    anchor = BODY.strip() + " " + HEAD
    other = HEAD + BODY
    assert fuse(anchor, other).count("กรมราชทัณฑ์") == 1
    assert fuse(anchor, other, duplicate_core=None).count("กรมราชทัณฑ์") == 2


def test_an_empty_second_read_changes_nothing() -> None:
    assert fuse(HEAD, "") == HEAD


def test_identical_reads_change_nothing() -> None:
    assert fuse(HEAD + BODY, HEAD + BODY) == HEAD + BODY


def test_concatenation_keeps_both_reads() -> None:
    assert concatenate("ก", "ข") == "ก ข"
