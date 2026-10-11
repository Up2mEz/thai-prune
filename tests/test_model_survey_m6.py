"""MODEL_SURVEY_M6a: SEA-LION v4 4B-VL and InternVL3.5-2B (HF) under M1's protocol, unchanged but the models."""

from pathlib import Path

import yaml

from labbs2026.model_survey.plan import m1_commands, validate

ROOT = Path(__file__).resolve().parents[1]
M6A = yaml.safe_load((ROOT / "configs/model_survey/m6a.yaml").read_text("utf-8"))
M1 = yaml.safe_load((ROOT / "configs/model_survey/m1.yaml").read_text("utf-8"))


def test_config_is_valid_and_pinned():
    queues = validate(M6A)
    assert queues == [[("sealion", 0, 2), ("internvl", 0, 2)], [("sealion", 1, 2), ("internvl", 1, 2)]]
    assert M6A["models"]["sealion"]["revision"] == "d0734aa1b8113fce90997a83c1e4afe2c37c6205"
    assert M6A["models"]["internvl"]["revision"] == "3f301ffcf3dcbb47893afae6650ea3e78d96fb6d"
    assert len([u for q in m1_commands(queues) for u in q]) == 4


def test_everything_but_the_models_is_m1s():
    for key in ("benchmark", "split", "runtime", "comparison", "scoring", "claim_level"):
        assert M6A[key] == M1[key], key
    assert M6A["prompts"]["BENCHMARK_QUESTION"] == M1["prompts"]["BENCHMARK_QUESTION"]
    for model in M6A["models"].values():
        assert model["prompts"] == ["BENCHMARK_QUESTION"] == [model["primary_prompt"]]


def test_registered_and_cleared():
    assert (ROOT / M6A["registration"]).is_file() and (ROOT / M6A["clearance"]).is_file()
    assert M6A["run_label"] == "m6a" and M6A["kernel_slug"] == "labbs2026-model-survey-m6a"


def test_sealion_is_qwen3vl4b_but_the_weights():
    cards = ROOT / "docs/stage0/data/cards/qwen-sea-lion-v4-4b-vl@d0734aa1b811"
    config = yaml.safe_load((cards / "config.json").read_text("utf-8"))
    assert config["architectures"] == ["Qwen3VLForConditionalGeneration"]
    assert M1["models"]["qwen3vl4b"]["revision"] == "ebb281ec70b05090aa6165b016eac8ec08e71b17"
