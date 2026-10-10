"""MODEL_SURVEY_M3 loop escape: rollback point, watch, constraints, and the constraint processor."""

import pytest

from labbs2026.model_survey.escape import (
    EscapeState,
    TOP_K,
    _constraint,
    collapse_digits,
    completes_unit,
    extend_inputs,
    near_onset,
    rollback_index,
    starts_unit,
    unit_key,
    watch_fires,
    watch_fires_after_escape,
)


def _decode_chars(ids):            # a toy tokenizer: token id k decodes to PIECES[k]
    return "".join(PIECES[i] for i in ids)


PIECES = ["ยอด", "รวม", " 58 ", "บา", "ทย", "อด", "x", " ", "ก", "ข"]


def test_rollback_index_is_the_first_boundary_at_or_after_the_position():
    tokens = [0, 1, 2, 3, 4, 5]          # "ยอด" "รวม" " 58 " "บา" "ทย" "อด"
    assert rollback_index(tokens, 0, _decode_chars) == 0
    assert rollback_index(tokens, 3, _decode_chars) == 1          # boundary exactly at 3
    assert rollback_index(tokens, 4, _decode_chars) == 2          # inside "รวม": keep it whole
    assert rollback_index(tokens, 13, _decode_chars) == 5         # "บา|ท" straddled by "ทย": kept whole
    assert rollback_index(tokens, 99, _decode_chars) == len(tokens)


def test_watch_fires_on_a_completed_run_only():
    assert watch_fires("หัวเรื่อง " + "ยอดรวม 58 บาท " * 8)
    assert not watch_fires("หัวเรื่อง " + "ยอดรวม 58 บาท " * 7)
    assert not watch_fires("12345 " * 30)                         # no letter: variant B never stops it


def test_starts_unit_follows_the_unit_until_the_model_deviates():
    key = unit_key("ยอดรวมทั้งสิ้น 58 บาท")
    assert starts_unit("", "ยอด", key)                             # a second copy begins
    assert starts_unit("", " ยอดรวม", key)                         # whitespace is ignored
    assert starts_unit("ย", "อด", key)                             # continues a straddled start
    assert not starts_unit("", " ", key)                           # whitespace alone does not extend it
    assert not starts_unit("", "หมายเหตุ", key)                     # something else: allowed
    assert not starts_unit("ยา", "อด", key)                        # already deviated: the check is off
    assert starts_unit("", "ยอดรวมทั้งสิ้น 58 บาทถ้วน", key)         # a piece holding the whole unit


def test_completes_unit_counts_new_occurrences_only():
    key = unit_key("วันที่ ๒")
    assert completes_unit("ประกาศ วันที่ ", "๒", key)
    assert not completes_unit("ประกาศ วันที่ ๒ แล้ว", "ก", key)      # the old occurrence is not new
    assert completes_unit("ประกาศ วันที่ ", "๓", key)                # numbers count as one 0 (Addendum 1)
    assert not completes_unit("ประกาศ วันที่ ", "ก", key)


def test_escape_state_applies_after_its_rollback():
    state = EscapeState()
    state.add(10, 20, "ยอดรวม 58 บาท")
    first_copy = "x" * 7 + "ยอดรวม 58 บาท"        # output up to the end of the first copy (20 chars)
    assert not state.violates(9, "ยอด", text=lambda: first_copy, tail=first_copy)        # before the rollback
    assert state.violates(10, "ยอด", text=lambda: first_copy, tail=first_copy)           # starts it again
    assert not state.violates(10, "หมาย", text=lambda: first_copy, tail=first_copy)
    later = first_copy + " หมายเหตุ " + "ยอดรวม 58 บา"
    assert state.violates(40, "ท", text=lambda: later, tail=later)                      # completes it again
    assert not state.violates(40, "ง", text=lambda: later, tail=later)
    empty = EscapeState()
    empty.add(3, 3, "   ")                                                               # no key: no constraint
    assert empty.rollbacks == []


def test_constraint_processor_moves_the_greedy_choice_off_the_unit():
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    state = EscapeState()
    state.add(2, 6, "ยอดรวม")                       # rollback after "ยอด" "รวม" (6 chars)
    processor = _constraint(_decode_chars, 1, state, {})
    vocab = max(len(PIECES), TOP_K)
    scores = torch.full((1, vocab), -10.0)
    scores[0, 0] = 5.0                                # "ยอด": would start a second copy
    scores[0, 8] = 4.0                                # "ก": allowed
    input_ids = torch.tensor([[99, 0, 1]])            # one prompt token, then "ยอด" "รวม"
    out = processor(input_ids, scores.clone())
    assert out[0, 0] == float("-inf") and int(out[0].argmax()) == 8
    no_state = _constraint(_decode_chars, 1, EscapeState(), {})
    assert int(no_state(input_ids, scores.clone())[0].argmax()) == 0       # nothing before a first escape


def test_extend_inputs_appends_text_tokens():
    torch = pytest.importorskip("torch")
    inputs = {"input_ids": torch.tensor([[1, 2, 3]]), "attention_mask": torch.ones(1, 3, dtype=torch.long),
              "mm_token_type_ids": torch.tensor([[0, 1, 0]]), "pixel_values": torch.zeros(2, 2)}
    out = extend_inputs(inputs, [7, 8])
    assert out["input_ids"].tolist() == [[1, 2, 3, 7, 8]]
    assert out["attention_mask"].tolist() == [[1, 1, 1, 1, 1]]
    assert out["mm_token_type_ids"].tolist() == [[0, 1, 0, 0, 0]]
    assert out["pixel_values"] is inputs["pixel_values"]
    assert extend_inputs(inputs, []) is inputs


def test_collapse_digits_maps_back_to_the_text():
    norm, index = collapse_digits("ข้อ 12 และ ๓๔ จบ")
    assert norm == "ข้อ 0 และ 0 จบ"
    assert [norm[k] for k in range(len(norm)) if norm[k] != "0"] ==            ["ข้อ 12 และ ๓๔ จบ"[index[k]] for k in range(len(norm)) if norm[k] != "0"]
    assert index[norm.index("0")] == "ข้อ 12 และ ๓๔ จบ".index("1")


def test_near_onset_catches_numbered_copies_after_the_prefix():
    numbered = "หัว 4) เนื้อหา" + "".join(f" {k}) การทดสอบหนี้สิน - ข้อความ" for k in range(5, 20))
    assert loop_free(numbered)                                          # exact variant B misses it
    start, end = near_onset(numbered, 0)
    assert numbered[start:end] == " 5) การทดสอบหนี้สิน - ข้อความ"
    assert watch_fires_after_escape(numbered, 0)
    assert not watch_fires_after_escape(numbered, len(numbered) - 40)   # only text after the prefix counts
    assert near_onset("ข้อความปกติ 1 2 3 จบ", 0) is None


def loop_free(text):
    return not watch_fires(text)


def test_constraint_treats_numbered_copies_as_one_unit():
    state = EscapeState()
    first = "หัว 5) ข้อความซ้ำ"
    state.add(3, len(first), " 5) ข้อความซ้ำ")
    later = first + " หมายเหตุ 6) ข้อความซ้"
    assert state.violates(20, "ำ", text=lambda: later, tail=later)       # 6) ... completes it again
    assert not state.violates(20, "า", text=lambda: later, tail=later)
