"""E5b readings and the sentence generator."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks import e5b_analysis as e5b

LINE = "ข้าวราคาแพงขึ้นทุกวัน"
LINE2 = "ไฟฟ้าดับทั้งเมืองเมื่อคืน"
TONE_WRONG = {"้": "่"}


def _page(output: str, px: int = 32, name: str = "P") -> dict:
    return {"kind": "page", "page": name, "lines": 2, "font_px": px,
            "reference": f"{LINE}\n{LINE2}", "raw_output": output}


def test_no_omission_and_no_difference() -> None:
    new = [_page(f"{LINE}\n{LINE2}", name=f"n{i}") for i in range(6)]
    old = [_page(f"{LINE}\n{LINE2}", name=f"o{i}") for i in range(6)]
    out = e5b.analyze(new, old)
    assert out["reading_omission"] == "clean_meaningful_text_almost_never_omitted"
    assert out["D3_reading"] == "no_difference_shown"


def test_more_misreads_in_meaningful_text() -> None:
    wrong = f"{LINE}\n{LINE2}".translate(str.maketrans(TONE_WRONG))
    assert wrong != f"{LINE}\n{LINE2}"
    new = [_page(wrong, name=f"n{i}") for i in range(10)]
    old = [_page(f"{LINE}\n{LINE2}", name=f"o{i}") for i in range(10)]
    out = e5b.analyze(new, old)
    assert out["D3_misread_meaningful_minus_words"]["estimate"] > 0
    assert out["D3_reading"] == "meaningful_text_more_misreads"


def test_sentence_lines_are_deterministic_and_carry_marks() -> None:
    pytest.importorskip("matplotlib")
    from labbs2026.thai_marks import synthetic_pages as sp
    from labbs2026.thai_marks import thai_sentences as ts

    measure = sp.measurer("assets/fonts/noto/NotoSansThai-Regular.ttf")
    a = ts.compose_sentence_lines(7, 6, 32, measure)
    assert a == ts.compose_sentence_lines(7, 6, 32, measure)
    assert len(a) == 6 and all(sp.n_marks(x) >= 4 for x in a)
    assert all(measure(x, 32) <= sp.PAGE[0] - 2 * sp.MARGIN_X for x in a)
