"""E4b readings."""

from __future__ import annotations

from labbs2026.thai_marks import e4b_analysis as e4b


def _page(found: bool, control: bool = True) -> dict:
    return {"lines": [{"group": "absent", "marks": 10, "outcome": "text" if found else "not_found"},
                      {"group": "control", "marks": 10, "outcome": "text" if control else "not_found"}]}


def _view(flags: list[bool], control: bool = True) -> list[dict]:
    return [_page(f, control) for f in flags]


def _scores(whole: list[bool], masked: list[bool], control: bool = True) -> dict:
    out = {v: _view(whole) for v in e4b.W5}
    out[e4b.MASKED] = _view(masked, control)
    return out


def test_union_counts_a_line_found_by_any_read() -> None:
    rows = e4b.union_rows([_view([True, False]), _view([False, False])])
    assert [r["text"] for r in rows] == [10, 0] and [r["absent"] for r in rows] == [10, 10]


def test_masking_adds_beyond_read_count() -> None:
    pages = 21
    out = e4b.analyze(_scores([False] * pages, [True] * pages))
    assert out["reading"] == "masking_adds_beyond_read_count"
    assert out["D1_M3_minus_W3"]["material"]


def test_read_count_accounts_for_gain_when_whole_page_reads_match() -> None:
    pages = 21
    out = e4b.analyze(_scores([True] * pages, [True] * pages))
    assert out["reading"] == "read_count_accounts_for_gain"


def test_whole_page_reads_recover_more_and_qualified_masked() -> None:
    pages = 21
    out = e4b.analyze(_scores([True] * pages, [False] * pages))
    assert out["reading"] == "whole_page_reads_recover_more"
    damaged = e4b.analyze(_scores([False] * pages, [True] * pages, control=False))
    assert damaged["reading"].endswith("_qualified")


def test_k_read_curve_rises_with_reads() -> None:
    pages = 4
    scores = _scores([False] * pages, [False] * pages)
    scores["pad"] = _view([True, False, False, False])
    scores["scale90"] = _view([False, True, False, False])
    curve = e4b.k_read_curve(scores, e4b.W3)
    assert curve[1] < curve[2] < curve[3]
