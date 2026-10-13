"""W4 confirmatory tests: bootstrap clusters, Holm, S1, S2, R1."""

from __future__ import annotations

import collections
import math

from labbs2026.model_survey import w4


def _counts(correct: int, output: int, reference: int = 10) -> dict:
    return {"correct": correct, "output_marks": output, "reference_marks": reference}


def test_clusters_group_items_sharing_an_image() -> None:
    groups = w4.clusters(["a", "b", "c"], {"a": "h1", "b": "h1", "c": "h2"})
    assert groups == [["a", "b"], ["c"]]
    assert w4.clusters(["x", "y"], {}) == [["x"], ["y"]]  # no hash: every item is its own page


def test_holm_is_monotone_and_rejects_the_smallest_first() -> None:
    out = w4.holm({"a": 0.001, "b": 0.02, "c": 0.04, "d": None})
    assert abs(out["a"]["p_holm"] - 0.003) < 1e-12 and out["a"]["reject"]  # 3 tests: 3 * 0.001
    assert abs(out["b"]["p_holm"] - 0.04) < 1e-12 and out["b"]["reject"]  # 2 * 0.02
    assert out["c"]["p_holm"] >= out["b"]["p_holm"]  # step-down is monotone
    late = w4.holm({"a": 0.03, "b": 0.04})
    assert abs(late["a"]["p_holm"] - 0.06) < 1e-12 and not late["a"]["reject"]
    assert out["d"]["p"] is None and not out["d"]["reject"]


def test_s1_detects_a_clear_gain_and_not_a_null() -> None:
    ids = [f"i{k}" for k in range(40)]
    greedy = {i: _counts(3, 10) for i in ids}
    better = {i: _counts(8, 10) for i in ids}
    hashes = {i: f"h{i}" for i in ids}
    gain = w4.s1_difference(greedy, better, hashes, resamples=500)
    assert gain["difference"] > 0.3 and gain["ci95"][0] > 0 and gain["p_one_sided"] < 0.01
    null = w4.s1_difference(greedy, dict(greedy), hashes, resamples=500)
    assert null["difference"] == 0 and null["p_one_sided"] > 0.5


def test_s2_counts_only_ended_outputs() -> None:
    records = {"a": {"reached_max_new_tokens": False, "raw_output": "x"},
               "b": {"reached_max_new_tokens": True, "raw_output": "y"},
               "c": {"reached_max_new_tokens": False, "raw_output": "z"}}
    cut = {"a": "x", "b": "", "c": "zz"}  # the stop changed b (looping, not counted) and c (ended)
    eff = w4.stop_effects(records, cut)
    assert eff["ended"] == ["a", "c"] and eff["changed"] == ["c"]
    pooled = w4.s2_pooled({"m": eff}, {}, resamples=300)
    assert pooled["ended"] == 2 and pooled["changed"] == 1 and not pooled["passes_as_written"]
    clean = w4.s2_pooled({"m": {"ended": [f"i{k}" for k in range(300)], "changed": []}}, {}, resamples=200)
    assert clean["passes_as_written"] and clean["share"] == 0
    assert 0 < clean["upper95_binomial_one_sided"] < 0.011  # about 3 / 300 for zero events


def test_binomial_cdf_is_the_exact_tail() -> None:
    assert abs(w4.binomial_cdf(0, 100, 0.01) - 0.99 ** 100) < 1e-12
    assert abs(w4.binomial_cdf(100, 100, 0.01) - 1.0) < 1e-12


def test_binomial_upper_matches_the_rule_of_three() -> None:
    assert abs(w4.binomial_upper(0, 100) - 0.0295) < 0.001
    assert w4.binomial_upper(5, 5) == 1.0 and w4.binomial_upper(0, 0) is None


def test_r1_ratio_and_test() -> None:
    def row(absent: int, misread: int) -> collections.Counter:
        return collections.Counter({"line_missing": absent, "span_missing": 0, "misread_with_base": misread})

    ids = [f"i{k}" for k in range(30)]
    mostly_absent = {i: row(8, 1) for i in ids}
    assert w4.r1_ratio(mostly_absent, ids) == 8
    test = w4.r1_test(mostly_absent, {}, resamples=300)
    assert test["passes_as_written"] and test["ci95"][0] > 3
    balanced = {i: row(1, 1) for i in ids}
    assert not w4.r1_test(balanced, {}, resamples=300)["passes_as_written"]
    assert w4.r1_ratio({"a": row(2, 0)}, ["a"]) == math.inf
    assert w4.r1_ratio({"a": row(0, 0)}, ["a"]) is None


def test_loop_share() -> None:
    assert w4.loop_share([{"reached_max_new_tokens": True}, {"reached_max_new_tokens": False}]) == 0.5
    assert w4.loop_share([]) is None
