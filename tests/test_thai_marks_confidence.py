"""E1 labelling and gate statistics."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.confidence import (
    aligned_pairs_full_page,
    auroc,
    build_cases,
    cluster_scores,
    clusters,
    gate,
    label_clusters,
    recall_at,
)

REF = "ข้าวราคาแพงขึ้นทุกวัน"


def test_clusters_keep_marks_with_their_consonant() -> None:
    assert [REF[s:e] for s, e in clusters(REF)][:3] == ["ข้", "า", "ว"]
    word = "ขึ้น"
    assert [word[s:e] for s, e in clusters(word)] == ["ขึ้", "น"]


def test_a_dropped_tone_mark_is_a_mark_error_and_correct_marks_are_not() -> None:
    raw = REF.replace("ข้าว", "ขาว")
    labelled = label_clusters(raw, aligned_pairs_full_page(REF, raw))
    errors = [raw[c["start"]:c["end"]] for c in labelled if c["error"]]
    assert errors == ["ข"]
    assert all(not c["error"] for c in labelled if raw[c["start"]:c["end"]] == "ขึ้")


def test_markup_and_figures_are_not_labelled() -> None:
    raw = "# " + REF + "\n<figure>ภาพข้าวในนา</figure>"
    labelled = label_clusters(raw, aligned_pairs_full_page(REF, raw))
    assert labelled and all(c["start"] < raw.index("<figure>") for c in labelled)
    assert not any(c["error"] for c in labelled)


def test_auroc_extremes_and_ties() -> None:
    assert auroc([3, 2, 1, 0], [True, True, False, False]) == 1.0
    assert auroc([0, 1, 2, 3], [True, True, False, False]) == 0.0
    assert auroc([1, 1, 1, 1], [True, False, True, False]) == 0.5
    assert auroc([1, 2], [False, False]) is None


def test_recall_at_flags_the_top_share() -> None:
    scores = list(range(100))
    labels = [i >= 95 for i in scores]
    assert recall_at(scores, labels, 0.05) == 1.0
    assert recall_at(scores, [i < 5 for i in scores], 0.05) == 0.0


def test_scores_take_the_weakest_overlapping_token() -> None:
    labelled = [{"start": 0, "end": 2, "error": True, "consonant_error": False}]
    offsets = [(0, 1), (1, 2), (2, 3)]
    out = cluster_scores(labelled, offsets, [-0.1, -2.0, -5.0], [0.1, 1.5, 3.0])
    assert out[0]["s_min"] == 2.0 and out[0]["s_ent"] == 1.5


def test_gate_reports_point_and_interval() -> None:
    items = [[{"s_min": 5.0, "error": True}, {"s_min": 0.1, "error": False}]] * 10
    result = gate(items, resamples=20)
    assert result["auroc"] == 1.0 and result["auroc_ci"] == (1.0, 1.0)
    assert result["clusters"] == 20 and result["errors"] == 10


def test_cases_come_from_greedy_only_in_a_fixed_order() -> None:
    rec = {"task": "Full-page OCR", "prompt_kind": "TYPHOON_CARD", "raw_output": "x",
           "reached_max_new_tokens": False}
    cases = build_cases([{**rec, "id": "B", "arm": "greedy"}, {**rec, "id": "A", "arm": "greedy"},
                         {**rec, "id": "A", "arm": "rep_penalty"}])
    assert [c["id"] for c in cases] == ["A", "B"]
    assert cases[0]["case"] == "Full-page OCR|TYPHOON_CARD|A"


def test_invalid_input_is_rejected_by_the_offsets_guard() -> None:
    from labbs2026.thai_marks.confidence import token_offsets

    class Tok:
        def __call__(self, text, add_special_tokens=False, return_offsets_mapping=True):
            return {"input_ids": [1, 2], "offset_mapping": [(0, 1), (1, 2)]}

    with pytest.raises(ValueError):
        token_offsets(Tok(), "ab", [1, 3])


def test_unmatched_lines_between_matched_ones_are_not_labelled() -> None:
    l1, l3 = "ข้าวราคาแพงขึ้นทุกวัน", "ไฟฟ้าดับทั้งเมืองเมื่อคืน"
    extra = "ข้อความที่ไม่มีในต้นฉบับเลยแม้แต่น้อย"
    raw = f"{l1}\n{extra}\n{l3}"
    labelled = label_clusters(raw, aligned_pairs_full_page(f"{l1}\n{l3}", raw))
    lo, hi = raw.index(extra), raw.index(extra) + len(extra)
    assert labelled and not any(lo <= c["start"] < hi for c in labelled)
    assert not any(c["error"] for c in labelled)
