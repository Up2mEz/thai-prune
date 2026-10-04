"""Tests for T1 scoring version 2: extraction, anchored alignment, cell split."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from, mark_decomposition
from labbs2026.thai_marks.extract import extract, extract_text

MAI_THO = "้"
MAI_TRI = "๊"

# --- extraction ---------------------------------------------------------------


def test_figure_content_is_removed_per_the_prompt_contract() -> None:
    raw = "ข้อความ <figure>ภาพคนกำลังเดิน</figure> ต่อ"
    assert extract_text(raw) == "ข้อความ ต่อ"


def test_figure_content_is_kept_only_when_asked_for_the_diagnostic() -> None:
    raw = "ข้อความ <figure>ภาพคนกำลังเดิน</figure> ต่อ"
    assert extract_text(raw, keep_figures=True) == "ข้อความ ภาพคนกำลังเดิน ต่อ"


def test_table_cells_keep_their_text_and_stay_separate_words() -> None:
    raw = "<table><tr><td>ก่อน</td><td>หลัง</td></tr><tr><td>บน</td></tr></table>"
    assert extract_text(raw) == "ก่อน หลัง บน"


def test_code_fence_lines_and_their_language_tag_are_removed() -> None:
    raw = "```markdown\nอ่านหัวข้อ\n```"
    assert extract_text(raw) == "อ่านหัวข้อ"


def test_entities_are_decoded_and_page_numbers_kept() -> None:
    raw = "ก &amp; ข <page_number>14</page_number>"
    assert extract_text(raw) == "ก & ข 14"


def test_markdown_markers_latex_and_pipes_are_removed_content_kept() -> None:
    raw = "# หัวข้อ\n**ตัวหนา** `code` $x^2$ a | b"
    assert extract_text(raw) == "หัวข้อ ตัวหนา code x^2 a b"


def test_an_unclosed_figure_is_counted_and_runs_to_the_end() -> None:
    text, counts = extract("ก่อน <figure>คำบรรยาย ไม่ปิด")
    assert text == "ก่อน"
    assert counts == {"figures": 1, "unclosed_figures": 1}


def test_extraction_never_alters_thai_marks() -> None:
    text = "ไฟฟ้า  ผู้อำนวยการ\nกี่ คร๊าาา"
    assert extract_text(text) == "ไฟฟ้า ผู้อำนวยการ กี่ คร๊าาา"
    assert extract_text(extract_text(text)) == extract_text(text)


def test_plain_reference_is_unchanged_but_for_whitespace() -> None:
    reference = "- ข้อ 1\n- ข้อ 2 | Thank you"
    assert extract_text(reference) == "- ข้อ 1 - ข้อ 2 Thank you"


# --- anchored alignment ------------------------------------------------------------


def test_surrounding_text_is_not_a_reading_error() -> None:
    reference = "อ่านหัวข้อ"
    hypothesis = "เทคนิคการทำ conversation 1. อ่านหัวข้อ บทความประเภทโฆษณา"
    pairs, start, end = align_anchored(reference, hypothesis)
    assert edit_distance_from(pairs, reference, hypothesis) == 0
    assert hypothesis[start:end] == reference


def test_runaway_repetition_after_the_answer_costs_nothing() -> None:
    reference = "สวัสดีครับ"
    hypothesis = reference + " สวัสดีครับ" * 40
    pairs, start, end = align_anchored(reference, hypothesis)
    assert edit_distance_from(pairs, reference, hypothesis) == 0
    assert (start, end) == (0, len(reference))


def test_errors_inside_the_window_still_count() -> None:
    reference = "ไปพร้อมๆกันคร" + MAI_TRI + "า"
    hypothesis = "คำนำ ไปพร้อมๆกันคร" + MAI_THO + "า ท้าย"
    pairs, _, _ = align_anchored(reference, hypothesis)
    assert edit_distance_from(pairs, reference, hypothesis) == 1
    marks = mark_decomposition(reference, hypothesis, pairs)
    assert marks["TONE"]["n"] == 2  # ้ in พร้อม, read correctly, and ๊ in คร๊า
    assert marks["TONE"]["correct"] == 1
    assert marks["TONE"]["base_correct_error"] == 1
    assert marks["TONE"]["same_class"] == 1


def test_anchored_distance_is_bounded_by_reference_length() -> None:
    reference = "ข้าว"
    hypothesis = "abcdefghijklmnopqrstuvwxyz" * 5
    pairs, _, _ = align_anchored(reference, hypothesis)
    assert edit_distance_from(pairs, reference, hypothesis) <= len(reference)


def test_every_reference_character_is_aligned_exactly_once() -> None:
    reference = "ผู้อำนวยการ"
    hypothesis = "xx ผูอำนวยกา yy"
    pairs, _, _ = align_anchored(reference, hypothesis)
    assert [r for r, _ in pairs if r is not None] == list(range(len(reference)))


def test_empty_reference_has_an_empty_window() -> None:
    assert align_anchored("", "อะไรก็ได้") == ([], 0, 0)


# --- cell split -----------------------------------------------------------------------

pytest.importorskip("pythainlp")

from labbs2026.thai_marks.analysis import score_t1_record_v2, summarize_t1_cells, summarize_t1_v2  # noqa: E402


def _record(task: str, prompt: str, reference: str, output: str, id_: str = "x") -> dict:
    return {"id": id_, "task": task, "prompt_kind": prompt, "reference": reference,
            "raw_output": output, "reached_max_new_tokens": False,
            "seconds_per_generated_token": 0.01}


def test_contract_diagnostic_catches_transcription_inside_a_figure() -> None:
    record = _record("Full-page OCR", "TYPHOON_CARD", "ไฟฟ้าดับ",
                     "<figure><table><tr><td>ไฟฟ้าดับ</td></tr></table></figure>")
    scored = score_t1_record_v2(record)
    assert scored["cer"] == 1.0
    assert scored["ref_in_figure_share"] == 1.0


def test_an_output_not_better_than_chance_is_scored_as_reading_nothing() -> None:
    record = _record("Text recognition", "BENCHMARK_QUESTION", "อ่านหัวข้อ",
                     "ข้อที่ 1 มีข้อความว่า เทคนิคการทำ conversation")
    raw = score_t1_record_v2(record)
    assert 0 < raw["cer"] < 1  # chance matches alone give partial credit
    thresholded = score_t1_record_v2(record, located_below=raw["cer"])
    assert thresholded["located"] == 0
    assert thresholded["cer"] == 1.0 and thresholded["cer_raw"] == raw["cer"]
    assert thresholded["TONE_base_n"] == 0  # no mark credited through a chance match


def test_chance_threshold_is_seeded_and_below_wrong_answers() -> None:
    from labbs2026.thai_marks.analysis import chance_threshold
    refs = ["ไฟฟ้าดับทั้งเมือง", "ข้าวราคาแพงขึ้น", "ฝนตกหนักทั้งคืน", "รถติดยาวสามกิโล"]
    first = chance_threshold(refs, refs, seed=1)
    assert first == chance_threshold(refs, refs, seed=1)
    assert 0 < first["threshold"] <= 1


def test_summaries_refuse_to_pool_tasks_or_prompts() -> None:
    scored = [score_t1_record_v2(_record("Full-page OCR", "BENCHMARK_QUESTION", "ไฟฟ้า", "ไฟฟ้า")),
              score_t1_record_v2(_record("Text recognition", "BENCHMARK_QUESTION", "ไฟฟ้า", "ไฟฟ้า"))]
    with pytest.raises(ValueError):
        summarize_t1_v2(scored)
    cells = summarize_t1_cells(scored)
    assert set(cells) == {"Full-page OCR / BENCHMARK_QUESTION",
                          "Text recognition / BENCHMARK_QUESTION"}
