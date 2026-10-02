"""P-ZOOM scoring: where an absent line was read, as text or inside a figure, and how well."""

from __future__ import annotations

from labbs2026.thai_marks.attribution import reference_lines
from labbs2026.thai_marks.p_zoom import mark_count
from labbs2026.thai_marks.p_zoom_analysis import chance_rate, reading, score_page, summarize

A = "ผู้ปกครองต้องพาเด็กไปรับวัคซีนตามกำหนดเวลาที่โรงพยาบาลแจ้งไว้"
B = "เจ้าหน้าที่สาธารณสุขจะออกเยี่ยมบ้านทุกสัปดาห์เพื่อติดตามผล"
C = "แผนภูมิแสดงสัดส่วนผู้ป่วยนอกที่เข้ารับบริการในแต่ละภูมิภาค"
D = "คณะกรรมการประชุมกันเพื่อพิจารณางบประมาณประจำปีอย่างละเอียด"
REFERENCE = "\n".join([A, B, C, D])


def _outcomes(tile_outputs, absent=(2,), control=(0,)):
    return {r["line"]: r for r in score_page(REFERENCE, tile_outputs, list(absent), list(control))["lines"]}


def test_an_absent_line_read_as_text_in_one_tile_is_recovered_with_its_marks() -> None:
    rows = _outcomes(["unrelated header", f"{B}\n{C}\n", "x"])
    assert rows[2]["outcome"] == "text" and rows[2]["tile"] == 1
    assert rows[2]["marks_correct"] == rows[2]["marks"] == mark_count(C) > 0


def test_text_written_inside_a_figure_is_a_policy_outcome_not_a_recovery() -> None:
    rows = _outcomes([f"<figure>{C}</figure>", "nothing here"])
    assert rows[2]["outcome"] == "figure_only" and rows[2]["marks_correct"] == 0


def test_a_line_absent_from_every_tile_is_not_found() -> None:
    assert _outcomes([A, B, D])[2]["outcome"] == "not_found"


def test_a_recovered_line_with_a_wrong_mark_is_charged_for_it() -> None:
    wrong = C.replace("ที่", "ทื่", 1)  # one upper vowel replaced by another
    row = _outcomes([wrong])[2]
    assert row["outcome"] == "text" and row["marks_correct"] == row["marks"] - 1


def test_control_lines_are_scored_like_absent_lines_but_grouped_apart() -> None:
    rows = _outcomes([A, "x"], absent=(2,), control=(0,))
    assert rows[0]["group"] == "control" and rows[0]["outcome"] == "text"
    assert rows[2]["group"] == "absent" and rows[2]["outcome"] == "not_found"


def test_one_stretch_is_credited_to_one_line_only() -> None:
    twin = "\n".join([A, A])  # the reference holds the same line twice
    lines = reference_lines(twin)
    assert len(lines) == 2
    scored = score_page(twin, [A], [0], [1])["lines"]
    assert sorted(r["outcome"] for r in scored) == ["not_found", "text"]


def test_summary_counts_lines_and_marks_per_outcome() -> None:
    page = score_page(REFERENCE, [f"{A}\n{C}", f"<figure>{B}</figure>"], [1, 2], [0, 3])
    summary = summarize([page])
    absent = summary["absent"]
    assert absent["lines_by_outcome"] == {"text": 1, "figure_only": 1, "not_found": 0}
    assert absent["marks"] == mark_count(B) + mark_count(C)
    assert absent["share_of_marks"]["text"] == mark_count(C) / absent["marks"]
    assert summary["control"]["lines_by_outcome"] == {"text": 1, "figure_only": 0, "not_found": 1}
    assert absent["correct_share_of_recovered_marks"] == 1.0


def _summary(text, figure, rest):
    total = text + figure + rest
    return {"absent": {"share_of_marks": {"text": text / total, "figure_only": figure / total,
                                         "not_found": rest / total}}}


def test_the_reading_follows_the_pre_registered_thresholds() -> None:
    gained, none = {"gain_share": 0.30}, {"gain_share": 0.05}
    assert reading(_summary(50, 10, 40), gained) == "resolution_attention_limit"
    assert reading(_summary(50, 50, 0), gained) == "resolution_attention_limit"  # text is checked first
    assert reading(_summary(49, 51, 0), gained) == "policy"
    assert reading(_summary(20, 30, 50), gained) == "beyond_typhoon_at_this_resolution"
    # tiles reach 50% but the whole-page read of the same prompt reaches almost as much:
    # the prompt, not the zoom, recovered the text
    assert reading(_summary(60, 10, 30), none) == "prompt_not_zoom"
    assert reading(_summary(60, 10, 30), {"gain_share": None}) == "prompt_not_zoom"


def test_the_gain_over_the_whole_page_read_counts_only_lines_tiles_alone_recovered() -> None:
    from labbs2026.thai_marks.p_zoom_analysis import compare_with_baseline

    def page(*outcomes):
        return {"lines": [{"line": i, "group": "absent", "marks": 10, "outcome": o, "marks_correct": 10}
                          for i, o in enumerate(outcomes)]}

    tiles = [page("text", "text", "text", "not_found")]
    whole = [page("text", "not_found", "not_found", "text")]
    result = compare_with_baseline(tiles, whole)
    assert result["gain_share"] == 20 / 40 and result["loss_share"] == 10 / 40
    assert result["baseline"]["absent"]["lines_by_outcome"]["text"] == 2
    import pytest
    with pytest.raises(ValueError):
        compare_with_baseline(tiles, [page("text", "text")])


def test_chance_rate_is_zero_for_unrelated_pages() -> None:
    pages = [{"reference": "\n".join([A, B]), "tile_outputs": [A, B], "absent": [0], "control": [1]},
             {"reference": "\n".join([C, D]), "tile_outputs": [C, D], "absent": [0], "control": [1]}]
    assert chance_rate(pages) == {"lines": 4, "found": 0, "rate": 0.0}
    assert chance_rate(pages[:1])["rate"] is None


def test_assemble_pages_orders_tiles_and_refuses_a_partial_run() -> None:
    import pytest

    from labbs2026.thai_marks.p_zoom_analysis import assemble_pages

    page = {"id": "P1", "absent_lines": [2], "control_lines": [0]}
    records = [{"id": "P1", "tile": t, "reference": REFERENCE, "raw_output": f"out{t}"}
               for t in (2, 0, 1, 3)]
    (assembled,) = assemble_pages(records, [page], 4)
    assert assembled["tile_outputs"] == ["out0", "out1", "out2", "out3"]
    assert assembled["absent"] == [2] and assembled["control"] == [0]
    with pytest.raises(ValueError, match="expected 0..3"):
        assemble_pages(records[:3], [page], 4)
    with pytest.raises(ValueError, match="outside the frozen list"):
        assemble_pages(records + [{"id": "LOCKED", "tile": 0, "reference": "", "raw_output": ""}],
                       [page], 4)
    with pytest.raises(ValueError, match="duplicate"):
        assemble_pages(records + records[:1], [page], 4)
