"""T3 boundary construction."""

from __future__ import annotations

from labbs2026.thai_marks.line_skip import boundaries

L1 = "ประกาศกรมราชทัณฑ์ ฉบับที่หนึ่ง"
L2 = "ผู้ต้องขังทุกคนต้องปฏิบัติตาม"
L3 = "ระเบียบของเรือนจำอย่างเคร่งครัด"
L4 = "หากฝ่าฝืนจะถูกลงโทษทางวินัย"


def _record(output: str) -> dict:
    return {"id": "p1", "reference": "\n".join([L1, L2, L3, L4]), "raw_output": output}


def test_a_skipped_line_gives_one_skip_boundary_after_the_last_line_read() -> None:
    cases = boundaries(_record(" ".join([L1, L3, L4])), controls_per_page=0)
    assert [c["kind"] for c in cases] == ["skip"]
    skip = cases[0]
    assert skip["line"] == 1
    assert skip["prefix"].rstrip().endswith(L1[-6:])
    assert skip["expected"] == L2[:12] and skip["actual"] == L3[:12]
    assert skip["marked"]


def test_a_fully_read_page_has_controls_and_no_skips() -> None:
    cases = boundaries(_record(" ".join([L1, L2, L3, L4])), controls_per_page=5)
    assert cases and all(c["kind"] == "control" for c in cases)
    for c in cases:
        assert c["expected"] != c["actual"]  # the next-next line, not the one read


def test_controls_are_seeded() -> None:
    record = _record(" ".join([L1, L2, L3, L4]))
    assert boundaries(record, controls_per_page=1) == boundaries(record, controls_per_page=1)


def test_a_line_read_in_another_order_is_not_a_skip() -> None:
    cases = boundaries(_record(" ".join([L1, L3, L4, L2])), controls_per_page=0)
    assert not [c for c in cases if c["kind"] == "skip"]
