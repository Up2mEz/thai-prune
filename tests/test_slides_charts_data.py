"""The slide charts read docs/paper/figure_data.json; check the data they rely on is consistent."""

import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parents[1] / "docs/paper/figure_data.json").read_text(encoding="utf-8"))


def test_locked_stop_never_below_greedy():
    d = DATA["locked_eight_models_mark_f1"]
    n = len(d["models"])
    for task in ("full_page", "text_recognition"):
        assert len(d[f"{task}_greedy"]) == len(d[f"{task}_stop"]) == n == 8
        assert all(s >= g for g, s in zip(d[f"{task}_greedy"], d[f"{task}_stop"]))


def test_r1_ratios_sit_inside_their_intervals_and_pass_the_threshold():
    d = DATA["locked_r1_ratio_fullpage"]
    assert len(d["models"]) == len(d["ratio"]) == len(d["ci_low"]) == len(d["ci_high"]) == 8
    for ratio, low, high in zip(d["ratio"], d["ci_low"], d["ci_high"]):
        assert low < ratio < high
        assert low > 3  # R1 passes only when the lower bound is above 3


def test_generation_is_not_above_the_forced_choice_test():
    d = DATA["tone_accuracy_generation_vs_test_fullpage_correct_base"]
    assert len(d["models"]) == len(d["generation"]) == len(d["test"])
    assert all(g <= t for g, t in zip(d["generation"], d["test"]))


def test_attribution_and_f1_use_the_same_model_order():
    attribution = DATA["attribution_cross_model_fullpage_stopped_pct_of_all_marks"]
    f1 = DATA["five_models_mark_f1"]
    assert len(attribution["models"]) == len(f1["models"]) == len(f1["full_page"]) == 6
    assert attribution["models"][0].startswith("Typhoon") and f1["models"][0].startswith("Typhoon")
    assert attribution["models"][-1] == "Qwen3-VL-2B" and f1["models"][-1] == "Qwen3-VL-2B"


def test_image_gain_matches_its_models():
    d = DATA["image_gain_fullpage_tone_calibration"]
    assert len(d["models"]) == len(d["gain"]) == 4
