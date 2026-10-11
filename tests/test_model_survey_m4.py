"""MODEL_SURVEY_M4: windows, window scores, labels, AUROC, threshold, filter, config."""

import copy
import importlib.util
from pathlib import Path

import pytest
import yaml

from labbs2026.model_survey.m4 import (
    auroc,
    filtered_output,
    item_bootstrap_auroc,
    label,
    m4_commands,
    quantile,
    validate,
    window_scores,
    windows,
)

ROOT = Path(__file__).resolve().parents[1]
M4 = yaml.safe_load((ROOT / "configs/model_survey/m4.yaml").read_text("utf-8"))
M3 = yaml.safe_load((ROOT / "configs/model_survey/m3.yaml").read_text("utf-8"))


def test_registered_config_is_valid_and_matches_m3():
    assert validate(M4) == [[("score", 0, 2)], [("score", 1, 2)]]
    assert m4_commands(validate(M4))[0][0] == {"name": "m4_score_shard-0-of-2",
                                               "module": "labbs2026.model_survey.remote_m4",
                                               "args": ["--shard", "0", "--shards", "2"]}
    for key in ("models", "prompt_kind", "prompts", "benchmark", "split", "reference_arm", "comparison", "scoring"):
        assert M4[key] == M3[key], key
    assert M4["scoring_pass"]["outputs_archive"].endswith("M3_OUTPUTS_e970f61dc74c.json.gz")


@pytest.mark.parametrize("change", [{"window_min_chars": 0}, {"label_max_cer": 1.5}, {"threshold_quantile": 1},
                                    {"primary_score": "s_max"}, {"label_task": "Handwriting"}])
def test_validate_rejects(change):
    bad = copy.deepcopy(M4)
    bad["analysis"].update(change)
    with pytest.raises(ValueError):
        validate(bad)


def test_windows_merge_phrases_to_the_minimum_and_keep_them_whole():
    text = "หัวเรื่อง ab cd ประกาศกระทรวงสาธารณสุข x"
    spans = windows(text, 0, len(text), 10)
    assert [text[a:b] for a, b in spans] == ["หัวเรื่อง ab", "cd ประกาศกระทรวงสาธารณสุข x"]
    assert windows(text, 10, len(text), 10)[0][0] == text.index("ab")        # starts at the first phrase after start
    assert windows("สั้น", 0, 4, 10) == [(0, 4)]                              # a lone short remainder stands alone
    assert windows("   ", 0, 3, 10) == []


def test_window_scores_use_overlapping_tokens():
    offsets = [(0, 3), (3, 6), (6, 9), (9, 12)]
    out = window_scores([(0, 6), (5, 12), (20, 25)], offsets, [-1.0, -3.0, -0.5, -0.5], [0.1, 0.2, 0.3, 0.4])
    assert out[0]["s_mean"] == -2.0 and out[0]["s_min"] == -3.0 and out[0]["n_tokens"] == 2
    assert out[1]["n_tokens"] == 3 and out[1]["s_min"] == -3.0 and abs(out[1]["s_ent"] - 0.3) < 1e-9
    assert out[2]["s_mean"] is None


def test_label_locates_a_window_in_the_reference():
    reference = "ประกาศกระทรวงสาธารณสุข\nเรื่อง การตรวจคัดกรองโรคเบาหวาน"
    assert label("การตรวจคัดกรองโรคเบาหวาน", reference, 0.4)[0] == "read"
    assert label("การตรวจคัดกรองโรคเบาหวาร", reference, 0.4)[0] == "read"            # one wrong character
    assert label("ประกาศทางการเมืองกับพันธบัตรทั้งหมด", reference, 0.4)[0] == "invented"
    assert label("3 3 3 3 3 3", reference, 0.4) == ("no_letter", None)


def test_auroc_and_item_bootstrap():
    assert auroc([3, 4], [1, 2]) == 1.0 and auroc([1], [1]) == 0.5 and auroc([], [1]) is None
    rows = {"a": [(0.9, True), (0.1, False)], "b": [(0.8, True), (0.2, False)], "c": [(0.3, True), (0.7, False)]}
    out = item_bootstrap_auroc(rows, resamples=200, seed=1)
    assert out["items"] == 3 and out["positive"] == 3 and out["negative"] == 3
    assert abs(out["auroc"] - 8 / 9) < 1e-9 and out["ci95"][0] <= out["auroc"] <= out["ci95"][1]


def test_quantile():
    assert quantile([1, 2, 3, 4, 5], 0.5) == 3 and quantile([1, 2, 3, 4, 5], 0.1) == pytest.approx(1.4)
    with pytest.raises(ValueError):
        quantile([], 0.1)


def test_filtered_output_keeps_the_prefix_and_confident_windows():
    text = "ส่วนแรก ยาว ต่อ ข้อความจริง สิ่งที่แต่ง อ่านจริงอีก"
    p = text.index(" ข้อความจริง")
    spans = windows(text, p, len(text), 5)
    scored = [{"start": a, "end": b, "s_mean": s} for (a, b), s in zip(spans, [-0.1, -5.0, -0.2])]
    assert [text[a:b] for a, b in spans] == ["ข้อความจริง", "สิ่งที่แต่ง", "อ่านจริงอีก"]
    assert filtered_output(text, p, scored, -1.0) == "ส่วนแรก ยาว ต่อ ข้อความจริง อ่านจริงอีก"
    assert filtered_output(text, p, scored, 0.0) == text[:p]
    assert filtered_output(text, p, scored, -9.0) == text


def test_m4_script_hashes_existing_files():
    spec = importlib.util.spec_from_file_location("m4k", ROOT / "scripts/model_survey_m4_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert all((ROOT / p).is_file() for p in module.HASHED)
    assert M4["scoring_pass"]["outputs_archive"] in module.HASHED
