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


def test_the_raw_prefix_keeps_the_newline_the_model_wrote() -> None:
    raw = f"{L1}\n{L3}\n{L4}"
    skip = [c for c in boundaries(_record(raw), controls_per_page=0) if c["kind"] == "skip"][0]
    assert skip["raw_prefix"] == L1 + "\n"
    assert skip["raw_actual"] == L3[:12]


def test_a_prefix_that_cannot_be_placed_in_the_raw_text_is_unscorable() -> None:
    from labbs2026.thai_marks.line_skip import raw_position
    assert raw_position("abc", "xyz") is None
    assert raw_position("ก ข\nค", "ก ข") == 3
