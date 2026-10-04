import pytest

from labbs2026.spec_decode.markup_check import (
    cut_partial_tag,
    divergence_thai_counts,
    drift,
    headline_flags,
    loops_at_budget,
    quantile_linear,
    strip_tags,
    thai_only_mark_share,
    TEXT_FORMS,
)

# a normal table: every row differs, but the closing tags repeat
TABLE = "<table>" + "".join(
    f"<tr>\n<td>รายการ {i}</td>\n</tr>\n" for i in ("ก", "ข", "ค", "ง", "จ", "ฉ")
) + "</table>"


def test_table_tags_trip_the_raw_repetition_rule_but_not_text():
    ref = {"reached_max_new_tokens": False, "text": TABLE}
    assert not headline_flags(ref, TEXT_FORMS["registered_raw"])     # flagged repetitive on raw HTML
    assert headline_flags(ref, TEXT_FORMS["tags_stripped"])
    assert headline_flags(ref, TEXT_FORMS["structural_text"])


def test_reaching_the_budget_is_degenerate_in_every_form():
    ref = {"reached_max_new_tokens": True, "text": "ข้อความ"}
    assert not any(headline_flags(ref, f) for f in TEXT_FORMS.values())


def test_strip_tags_and_cut_partial_tag():
    assert strip_tags("<td>ก</td>").split() == ["ก"]
    assert cut_partial_tag("58 58 58 <page") == "58 58 58"
    assert cut_partial_tag("ไม่มี tag ค้าง") == "ไม่มี tag ค้าง"


def test_loops_at_budget_recovers_loop_hidden_by_cut_tag():
    unit = "ยอดรวมทั้งสิ้น 58 บาท ชำระแล้ว "
    looped = unit * 12 + "<page"
    refs = [
        {"reached_max_new_tokens": True, "text": looped},
        {"reached_max_new_tokens": False, "text": looped},   # not at the budget: ignored
    ]
    out = loops_at_budget(refs)
    assert out["reached_max"] == 1
    assert out["loop_structural_cut_tag"] >= out["loop_structural"]
    assert out["loop_structural_cut_tag"] == 1


def test_drift_on_text_ignores_markup_only_changes():
    a = "<figure>ภาพคนยืน</figure>สวัสดีครับ"
    b = "<figure>ภาพต้นไม้สูง</figure>สวัสดีครับ"
    assert drift(a, b) > 0
    assert drift(a, b, TEXT_FORMS["tags_stripped"]) > 0          # description text still differs
    assert drift("<td>ก</td>", "<th>ก</th>", TEXT_FORMS["tags_stripped"]) == 0


def test_quantile_linear_matches_interpolation():
    assert quantile_linear([0, 10], 0.9) == pytest.approx(9.0)
    assert quantile_linear([1, 2, 3, 4, 5], 0.5) == 3


def test_thai_only_mark_share_and_counts():
    shares = {"other": 0.659, "thai_no_mark": 0.2198, "has_thai_mark": 0.1212}
    assert thai_only_mark_share(shares) == pytest.approx(0.1212 / 0.341, rel=1e-3)
    c = divergence_thai_counts({"has_thai_mark": 4 / 21, "thai_no_mark": 10 / 21, "other": 7 / 21}, 21)
    assert (c["has_thai_mark"], c["thai"], c["other"]) == (4, 14, 7)
    assert c["mark_share_thai"] == pytest.approx(4 / 14)
