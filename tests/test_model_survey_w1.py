"""MODEL_SURVEY W1: the stop's cell summary, surplus and attribution shares."""

import collections
import importlib.util
from pathlib import Path

import pytest

from labbs2026.model_survey.w1 import ATTRIBUTION_ROWS, attribution_shares, stop_summary, stopped, surplus

ROOT = Path(__file__).resolve().parents[1]
UNIT = "ยอดรวมทั้งสิ้น 58 บาท "


def _rec(i, text, reached):
    return {"id": i, "task": "Full-page OCR", "raw_output": text, "reached_max_new_tokens": reached}


def _counts(output_marks, correct):
    return {"output_marks": output_marks, "correct": correct, "reference_marks": 10}


def test_stopped_cuts_only_loops():
    loop = _rec("a", "หัวเรื่อง " + UNIT * 12, True)
    out = stopped(loop)
    assert out["stop_changed"] and out["raw_output"].count("ยอดรวม") == 1
    plain = _rec("b", "ข้อความปกติ", False)
    assert stopped(plain) == {**plain, "stop_changed": False}


def test_surplus():
    assert surplus(_counts(12, 9)) == 3


def test_stop_summary_counts_changes_and_surplus():
    records = {"a": _rec("a", "หัวเรื่อง " + UNIT * 12, True),
               "b": _rec("b", "ข้อความปกติ", False),
               "c": _rec("c", "x " + UNIT * 9, False)}   # a legitimate-looking repeat that ended: the stop still cuts it
    before = {"a": _counts(50, 5), "b": _counts(10, 8), "c": _counts(30, 10)}
    after = {"a": _counts(8, 5), "b": _counts(10, 8), "c": _counts(12, 10)}
    s = stop_summary(records, before, after)
    assert (s["items"], s["looping"], s["non_looping"]) == (3, 1, 2)
    assert (s["changed"], s["changed_looping"], s["changed_non_looping"]) == (3 - 1, 1, 1)
    assert s["changed_non_looping_share"] == 0.5
    assert s["surplus_marks"] == 45 + 2 + 20
    assert s["surplus_in_cut_outputs"] == 65 and s["loop_share_of_surplus"] == pytest.approx(65 / 67)
    assert s["surplus_removed_by_stop"] == 67 - (3 + 2 + 2)


def test_attribution_shares_pool_and_divide_by_all_marks():
    out = attribution_shares([collections.Counter(correct=6, line_missing=2),
                              collections.Counter(correct=1, misread_with_base=1)])
    assert out["reference_marks"] == 10 and out["wrong_share"] == pytest.approx(0.3)
    assert out["share"]["line_missing"] == pytest.approx(0.2) and out["share"]["span_missing"] == 0
    assert set(out["counts"]) == set(ATTRIBUTION_ROWS)
    assert attribution_shares([])["share"]["correct"] is None


def test_w1_script_imports():
    spec = importlib.util.spec_from_file_location("w1s", ROOT / "scripts/model_survey_w1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ATTRIBUTION_TASK == "Full-page OCR"
