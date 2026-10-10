"""MODEL_SURVEY_M2 exploratory readings: the stop's unit and point, what it removes, what loops repeat."""

from labbs2026.model_survey.m2_exploratory import (
    loop_content,
    loop_unit,
    split_by_loop,
    stop_effect,
    stop_point,
    summarize_stops,
    symmetric_ids,
)


def test_loop_unit_is_variant_bs_onset():
    assert loop_unit("หัวเรื่อง " + "abcd " * 10).strip() == "abcd"
    assert loop_unit("ข้อความปกติที่ไม่ซ้ำ") is None
    assert loop_unit("abcd " * 7) is None                # 7 copies: below variant B's 8
    assert loop_unit("1234 " * 20) is None               # no letter: variant B never stops it


def test_stop_point_locates_copies_detection_and_tail():
    # the earliest run starts at the space after "หัว": unit " abcd", then " ab" (less than a unit) follows
    point = stop_point("หัว " + "abcd " * 10 + "ab")
    assert point["onset"] == 3 and point["unit_chars"] == 5 and point["copies"] == 10
    assert point["fires_at"] == 3 + 8 * 5 and point["chars_after_run"] == 3
    followed = stop_point("หัว " + "abcd " * 9 + "แล้วอ่านต่ออีกหลายคำ")
    assert followed["copies"] == 9 and followed["chars_after_run"] == 1 + len("แล้วอ่านต่ออีกหลายคำ")
    long_unit = "x" + "บรรทัดยาวที่ซ้ำกันหลายครั้งในหน้าเดียวกันของเอกสาร 1 " * 6
    assert stop_point(long_unit)["fires_at"] == 1 + 6 * stop_point(long_unit)["unit_chars"]
    assert stop_point("ไม่มีอะไรซ้ำ") is None


def _cut_record(reference="สวัสดีครับ", reached=True, tail=""):
    text = "ok " + "วันที่ ๒ " * 10 + tail
    return {"id": "a", "raw_output": text, "reference": reference, "reached_max_new_tokens": reached,
            "generated_tokens": len(text)}                # one token per character, for round numbers


def test_stop_effect_counts_unit_and_tokens():
    record = _cut_record()
    effect = stop_effect(record, {"output_marks": 30, "correct": 7}, {"output_marks": 3, "correct": 1})
    assert effect["output_marks_removed"] == 27 and effect["credited_marks_removed"] == 6
    assert effect["unit_in_reference"] is False and effect["unit_has_marks"] is True
    assert effect["reached_max_new_tokens"] is True and effect["runaway_to_end"] is True
    assert effect["tokens_to_first_copy"] == effect["onset"] + effect["unit_chars"]
    assert effect["tokens_to_detection"] == effect["onset"] + 8 * effect["unit_chars"]
    assert effect["tokens_to_first_copy"] < effect["tokens_to_detection"] < effect["generated_tokens"]
    counts = ({"output_marks": 30, "correct": 7}, {"output_marks": 3, "correct": 1})
    assert stop_effect(_cut_record("ประกาศ\nวันที่ ๒ ตุลาคม"), *counts)["unit_in_reference"] is True
    followed = stop_effect(_cut_record(reached=False, tail="แล้วอ่านต่ออีกหลายคำ"), *counts)
    assert followed["reached_max_new_tokens"] is False and followed["runaway_to_end"] is False


def test_summarize_stops_splits_as_the_review_asked():
    keys = ("output_marks_removed", "credited_marks_removed", "generated_tokens", "tokens_to_first_copy",
            "tokens_to_detection")
    effects = [{"reached_max_new_tokens": True, "runaway_to_end": True, "unit_in_reference": False,
                **dict(zip(keys, (10, 4, 100, 5, 40)))},
               {"reached_max_new_tokens": False, "runaway_to_end": False, "unit_in_reference": True,
                **dict(zip(keys, (5, 1, 50, 10, 30)))}]
    out = summarize_stops(effects)
    assert out["cut"] == 2
    assert out["all"] == {"n": 2, **dict(zip(keys, (15, 5, 150, 15, 70)))}
    assert out["ended_normally"] == {"n": 1, **dict(zip(keys, (5, 1, 50, 10, 30)))}
    assert out["not_runaway_to_end"]["n"] == 1
    assert out["unit_not_in_reference"] == {"n": 1, **dict(zip(keys, (10, 4, 100, 5, 40)))}
    assert summarize_stops([])["all"]["n"] == 0


def test_symmetric_ids_select_on_both_models():
    def rec(output, reached=False):
        return {"raw_output": output, "reference": "ข้อความอ้างอิง", "reached_max_new_tokens": reached}

    a = {"x": rec("ข้อความอ้างอิง"), "y": rec("ข้อความอ้างอิง"), "z": rec("ข้อความอ้างอิง" * 3), "w": rec("ก", True)}
    b = {"x": rec("ข้อความอ้างอิง"), "y": rec("ข้อความอ้างอิง" * 3), "z": rec("ข้อความอ้างอิง"), "w": rec("ก")}
    assert symmetric_ids(a, b) == ["x"]


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
