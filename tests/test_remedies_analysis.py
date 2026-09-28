import pytest

from labbs2026.remedies.analysis import item_rows, summarize

REF = "ไม้เอก ไม้โท ก่อน ข้าว"


def _arm(raw, seconds=1.0):
    return {"raw_output": raw, "seconds_generate": seconds, "generated_tokens": 10, "reached_max_new_tokens": False}


def _records():
    loop = REF + " " + "วนซ้ำอีกแล้วนะ " * 30
    return [
        {"id": "a", "task": "T", "reference": REF,
         "arms": {"FULL": _arm("ไมเอก ไม้โท กอน ข้าว"), "X": _arm(REF, 2.0), "Y": _arm(loop, 4.0)}},
        {"id": "b", "task": "T", "reference": REF,
         "arms": {"FULL": _arm(REF), "X": _arm(REF, 2.0), "Y": {"failed": True}}},
        {"id": "c", "task": "T", "reference": REF,
         "arms": {"FULL": _arm(loop), "X": _arm(REF, 2.0), "Y": _arm(loop, 4.0)}},
    ]


def test_marks_only_on_items_both_readable_and_transitions():
    s = summarize(item_rows(_records()), resamples=200)
    x = s["X"]
    assert x["items_compared"] == 3 and x["items_kept_for_marks"] == 2      # c: FULL loops
    assert x["cause_transitions"] == {"loop->misread": 1, "misread->misread": 2}
    tone = x["TONE_mark_specific_error_kept"]
    assert tone["FULL"] > 0 and tone["arm"] == 0
    assert tone["arm_minus_FULL"]["estimate"] < 0
    assert x["latency_ratio_geomean"] == pytest.approx(2.0)
    y = s["Y"]
    assert y["items_failed"] == 1 and y["items_compared"] == 2
    assert y["items_kept_for_marks"] == 0 and y["TONE_mark_specific_error_kept"] is None
    assert y["cause_transitions"] == {"loop->loop": 1, "misread->loop": 1}
