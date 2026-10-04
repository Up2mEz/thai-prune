"""E3 method pieces."""

from __future__ import annotations

from labbs2026.thai_marks.reread_method import band_spans, choose_bands, flagged_lines, word_edits


def segment(text: str) -> list[str]:
    return text.split(" ") and [w for part in text.split(" ") for w in (part, " ")][:-1]


def _chars(text):
    return [(i, i + 1) for i in range(len(text))]


def test_band_spans_cover_the_page_with_overlap() -> None:
    spans = band_spans()
    assert len(spans) == 3 and spans[0][0] == 0 and abs(spans[-1][1] - 1) < 1e-9
    assert spans[0][1] > spans[1][0]  # overlap


def test_choose_bands_by_position() -> None:
    spans = [(0.0, 0.37), (0.31, 0.69), (0.63, 1.0)]
    assert choose_bands(0.05, spans) == [0]
    assert choose_bands(0.5, spans) == [1]
    assert choose_bands(0.34, spans) == [0, 1]


def test_flagged_lines_need_a_low_confidence_cluster_and_length() -> None:
    raw = "สั้น\nบรรทัดยาวพอสมควร"
    lp = [-0.001] * len(raw)
    lp[raw.index("ย")] = -2.0
    lines = flagged_lines(raw, _chars(raw), lp, _chars(raw))
    assert lines == [(5, len(raw), [raw.index("ย")])]


def test_a_more_confident_band_word_replaces_the_flagged_page_word() -> None:
    raw = "ข่าว ราคา แพง"
    band = "ข้าว ราคา แพง"
    page_lp = [-0.01] * len(raw)
    page_lp[1] = -3.0  # the tone mark of ข่าว
    band_lp = [-0.01] * len(band)
    line = (0, len(raw), [0])
    edits = word_edits(raw, line, _chars(raw), page_lp, [(band, _chars(band), band_lp)], segment)
    assert edits == [(0, 4, "ข้าว")]


def test_a_less_confident_band_word_is_not_used() -> None:
    raw = "ข่าว ราคา แพง"
    band = "ข้าว ราคา แพง"
    page_lp = [-0.5] * len(raw)
    band_lp = [-0.01] * len(band)
    band_lp[1] = -4.0
    edits = word_edits(raw, (0, len(raw), [0]), _chars(raw), page_lp,
                       [(band, _chars(band), band_lp)], segment)
    assert edits == []


def test_no_matching_band_means_no_edit() -> None:
    raw = "ข่าว ราคา แพง"
    edits = word_edits(raw, (0, len(raw), [0]), _chars(raw), [-3.0] * len(raw),
                       [("อะไรก็ไม่รู้ที่ไม่เกี่ยวกันเลยสักนิด", _chars("x" * 40), [-0.01] * 40)], segment)
    assert edits == []
