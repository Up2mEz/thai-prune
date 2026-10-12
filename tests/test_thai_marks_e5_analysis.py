"""E5 readings and the synthetic page generator."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks import e5_analysis as e5

LINE = "ข้าวราคาแพงขึ้นทุกวัน"
LINE2 = "ไฟฟ้าดับทั้งเมืองเมื่อคืน"


def _page(output: str, count: int = 2, px: int = 32, name: str = "P") -> dict:
    return {"kind": "page", "page": name, "lines": count, "font_px": px,
            "reference": f"{LINE}\n{LINE2}", "raw_output": output}


def test_an_omitted_line_is_counted_by_its_marks() -> None:
    rows = e5.omitted_share_by_page([_page(LINE)])
    assert rows[0]["absent"] > 0 and rows[0]["found_marks"] > 0
    assert rows[0]["found_correct"] == rows[0]["found_marks"]


def test_cell_summary_has_one_row_per_cell() -> None:
    recs = [_page(f"{LINE}\n{LINE2}", 2, 32, "a"), _page(LINE, 2, 32, "b"), _page(LINE, 4, 44, "c")]
    out = e5.cell_summary(recs)
    assert set(out) == {"L2-S32", "L4-S44"}
    assert out["L2-S32"]["omitted_share"] > 0


def test_pooled_contrast_detects_more_omission_at_higher_density() -> None:
    dense = [_page(LINE, 18, 32, f"d{i}") for i in range(8)]
    sparse = [_page(f"{LINE}\n{LINE2}", 4, 32, f"s{i}") for i in range(8)]
    out = e5.pooled_contrast(dense + sparse, {"lines": 18}, {"lines": 4})
    assert out["material"] and out["estimate"] > 0.2


def test_line_arms_and_reading() -> None:
    recs = [_page(LINE, 2, 32, "p0")]
    for kind in ("line_tight", "line_masked"):
        recs.append({"kind": kind, "page": "p0", "lines": 2, "font_px": 32, "line_index": 1,
                     "reference": LINE2, "raw_output": LINE2})
    arms = e5.line_arms(recs)
    assert arms["omitted_in_page"] == 1 and arms["omitted_found_masked"] == 1
    assert e5.reading(arms) == "too_few_omissions"  # one omission is not enough to read a mechanism
    big = {"omitted_in_page": 12, "omitted_found_masked": 9, "omitted_found_tight": 12}
    assert e5.reading(big) == "competing_content"
    assert e5.reading({"omitted_in_page": 12, "omitted_found_masked": 1,
                       "omitted_found_tight": 9}) == "image_size_or_zoom"
    assert e5.reading({"omitted_in_page": 12, "omitted_found_masked": 1,
                       "omitted_found_tight": 2}) == "not_readable_alone"


def test_synthetic_pages_are_deterministic_and_carry_marks() -> None:
    pytest.importorskip("matplotlib")
    from labbs2026.thai_marks import synthetic_pages as sp

    assert sp.n_marks("ข้าว") == 1 and sp.n_marks("ปั๊ม") == 2
    vocab = sp.vocabulary()
    assert len(vocab) > 1000
    font = "assets/fonts/noto/NotoSansThai-Regular.ttf"
    measure = sp.measurer(font)
    a = sp.compose_lines(1, 3, 32, vocab, measure)
    b = sp.compose_lines(1, 3, 32, vocab, measure)
    assert a == b and all(sp.n_marks(x) >= 4 for x in a)
    page, lines = sp.render_page(a, 32, font)
    assert page.size == sp.PAGE and len(lines) == 3
    assert lines[0].box[1] < lines[1].box[1] < lines[2].box[1]
