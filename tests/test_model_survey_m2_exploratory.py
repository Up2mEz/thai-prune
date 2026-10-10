"""MODEL_SURVEY_M2 exploratory readings: the stop's unit, what it removes, what loops repeat."""

from labbs2026.model_survey.m2_exploratory import (
    loop_content,
    loop_unit,
    split_by_loop,
    stop_effect,
    summarize_stops,
)


def test_loop_unit_is_variant_bs_onset():
    assert loop_unit("หัวเรื่อง " + "abcd " * 10).strip() == "abcd"
    assert loop_unit("ข้อความปกติที่ไม่ซ้ำ") is None
    assert loop_unit("abcd " * 7) is None                # 7 copies: below variant B's 8
    assert loop_unit("1234 " * 20) is None               # no letter: variant B never stops it


def test_stop_effect_counts_and_unit_in_reference():
    record = {"raw_output": "ok " + "วันที่ ๒ " * 10, "reference": "สวัสดีครับ"}
    effect = stop_effect(record, {"output_marks": 30, "correct": 7}, {"output_marks": 3, "correct": 1})
    assert effect == {"output_marks_removed": 27, "credited_marks_removed": 6,
                      "unit_in_reference": False, "unit_has_marks": True}
    record["reference"] = "ประกาศ\nวันที่ ๒ ตุลาคม"
    assert stop_effect(record, {"output_marks": 30, "correct": 7},
                       {"output_marks": 3, "correct": 1})["unit_in_reference"] is True


def test_summarize_stops_splits_by_unit_in_reference():
    effects = [{"output_marks_removed": 10, "credited_marks_removed": 4, "unit_in_reference": False},
               {"output_marks_removed": 5, "credited_marks_removed": 1, "unit_in_reference": True}]
    out = summarize_stops(effects)
    assert out["cut"] == 2
    assert out["all"] == {"n": 2, "output_marks_removed": 15, "credited_marks_removed": 5}
    assert out["unit_not_in_reference"] == {"n": 1, "output_marks_removed": 10, "credited_marks_removed": 4}


def test_loop_content_separates_thai_and_mark_free_units():
    records = [{"id": "a", "raw_output": "abc1 " * 20, "reached_max_new_tokens": True},
               {"id": "b", "raw_output": "ที่นี่ " * 20, "reached_max_new_tokens": True},
               {"id": "c", "raw_output": "อ่านจบ", "reached_max_new_tokens": False}]
    counts = {"a": {"output_marks": 0}, "b": {"output_marks": 60}, "c": {"output_marks": 2}}
    assert loop_content(records, counts) == {"n": 3, "reached_max": 2, "exact_repeat": 2, "unit_has_marks": 1,
                                             "output_marks_in_looping": 60, "output_marks_all": 62}


def test_split_by_loop():
    records = {"x": {"reached_max_new_tokens": True}, "y": {"reached_max_new_tokens": False},
               "z": {"reached_max_new_tokens": False}}
    assert split_by_loop(records) == {"looped": ["x"], "did_not_loop": ["y", "z"]}
