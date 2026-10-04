"""T5 summaries: paired against greedy, per cell."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.order_free import mark_counts
from labbs2026.thai_marks.t5_analysis import paired_bootstrap_delta_f1, summarize_t5

REF = "ข้าวราคาแพงขึ้นทุกวัน\nไฟฟ้าดับทั้งเมืองเมื่อคืน"
GOOD = "ข้าวราคาแพงขึ้นทุกวัน ไฟฟ้าดับทั้งเมืองเมื่อคืน"
LOOP = "ข้าวราคาแพงขึ้นทุกวัน " + "ไฟฟ้า " * 50


def _rec(i, arm, out, task="Full-page OCR", trunc=False, tokens=10):
    return {"id": i, "task": task, "prompt_kind": "BENCHMARK_QUESTION", "arm": arm,
            "reference": REF, "raw_output": out, "reached_max_new_tokens": trunc,
            "generated_tokens": tokens, "seconds_generate": tokens / 10,
            "seconds_per_generated_token": 0.1, "ngram_block": None}


def test_bootstrap_of_identical_arms_is_zero() -> None:
    c = [mark_counts(REF, GOOD)] * 5
    out = paired_bootstrap_delta_f1(c, c, resamples=50)
    assert out == {"delta": 0.0, "ci_low": 0.0, "ci_high": 0.0}


def test_bootstrap_rejects_unpaired_samples() -> None:
    with pytest.raises(ValueError):
        paired_bootstrap_delta_f1([mark_counts(REF, GOOD)], [], resamples=5)


def test_a_fixed_loop_raises_f1_and_lowers_the_loop_rate() -> None:
    records = [_rec("A", "greedy", GOOD), _rec("B", "greedy", LOOP, trunc=True, tokens=3072),
               _rec("A", "fix", GOOD), _rec("B", "fix", GOOD)]
    cell = summarize_t5(records)["Full-page OCR / BENCHMARK_QUESTION"]
    fix, greedy = cell["arms"]["fix"], cell["arms"]["greedy"]
    assert fix["loop_rate"] == 0 and greedy["loop_rate"] == 0.5
    assert fix["delta_f1_vs_greedy"]["delta"] > 0
    assert cell["loop_free_items"] == 1
    assert fix["loop_free_identical_to_greedy"] == 1.0
    assert fix["loop_free_delta_f1_vs_greedy"] == 0
    assert "mark_causes" in fix


def test_a_cell_without_greedy_is_rejected() -> None:
    with pytest.raises(ValueError):
        summarize_t5([_rec("A", "fix", GOOD)])


def test_greedy_is_compared_with_t1() -> None:
    records = [_rec("A", "greedy", GOOD), _rec("A", "fix", GOOD)]
    t1 = [{"id": "A", "task": "Full-page OCR", "prompt_kind": "BENCHMARK_QUESTION",
           "raw_output": GOOD}]
    assert summarize_t5(records, t1)["Full-page OCR / BENCHMARK_QUESTION"][
        "greedy_identical_to_t1"] == 1.0
