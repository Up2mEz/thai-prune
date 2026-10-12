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


def test_w3_copies_t2_unchanged():
    w3 = yaml.safe_load((ROOT / "configs/model_survey/w3_t2.yaml").read_text("utf-8"))
    t2 = yaml.safe_load((ROOT / "configs/thai_marks/t1_t2.yaml").read_text("utf-8"))
    for key in ("benchmark", "split", "runtime", "prompts"):
        assert w3[key] == t2[key], key
    for key in ("prompt", "dtype", "window_after_chars", "consistency_tolerance_nats"):
        assert w3["t2"][key] == t2["t2"][key], key
    m5 = yaml.safe_load((ROOT / "configs/model_survey/m5.yaml").read_text("utf-8"))
    for role, source in (("pathumma", m5), ("qwen3vl4b", M1)):
        for key in ("model_id", "revision"):
            assert w3["models"][role][key] == source["models"][role][key]
    assert (ROOT / w3["registration"]).is_file()


def test_w3_queues():
    import importlib.util

    spec = importlib.util.spec_from_file_location("w3k", ROOT / "scripts/model_survey_w3_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    w3 = yaml.safe_load((ROOT / "configs/model_survey/w3_t2.yaml").read_text("utf-8"))
    a = module.queues(w3, ["pathumma"])
    assert [len(q) for q in a] == [1, 1] and all("visible_devices" not in q[0] for q in a)
    (b,), = [module.queues(w3, ["qwen3vl4b"])]
    assert b[0]["visible_devices"] == "0,1" and b[0]["module"] == "labbs2026.model_survey.remote_w3"


def test_worker_lets_a_unit_see_both_gpus():
    worker = (ROOT / "infra/kaggle/model_survey_worker.py").read_text("utf-8")
    assert 'str(unit.get("visible_devices", gpu))' in worker


def test_m6b_config_is_m1s_but_the_model_and_attention():
    m6b = yaml.safe_load((ROOT / "configs/model_survey/m6b.yaml").read_text("utf-8"))
    validate(m6b)
    for key in ("benchmark", "split", "comparison", "scoring", "claim_level"):
        assert m6b[key] == M1[key], key
    assert {k: v for k, v in m6b["runtime"].items() if k != "attention"} == \
        {k: v for k, v in M1["runtime"].items() if k != "attention"}
    assert m6b["runtime"]["attention"] == "eager"
    assert m6b["runner_module"] == "labbs2026.model_survey.remote_m6b"
    assert m6b["models"]["deepseek"]["revision"] == "aaa02f3811945a91062062994c5c4a3f4c0af2b0"
    for path in m6b["extra_hashed"]:
        assert (ROOT / path).is_file()
    pins = (ROOT / "configs/model_survey/m6b_requirements.txt").read_text("utf-8")
    assert "transformers==4.46.3" in pins and "torch==2.6.0" in pins


def test_m6b_prepare_inputs_counts_image_tokens():
    import types

    import pytest

    torch = pytest.importorskip("torch")
    from PIL import Image, ImageOps

    from labbs2026.model_survey.remote_m6b import IMAGE_TOKEN_ID, content_for, prepare_inputs

    class Transform:
        mean = (0.5, 0.5, 0.5)

        def __init__(self, **_):
            pass

        def __call__(self, image):
            return torch.zeros((3, image.size[1], image.size[0]))

    def dynamic_preprocess(image):  # stands in for DeepSeek's: a 3 x 2 grid of 768-px crops
        return [image.crop((0, 0, 768, 768))] * 6, (3, 2)

    remote = types.SimpleNamespace(
        format_messages=lambda conversations, sft_format, system_prompt: "<|User|>: "
        + conversations[0]["content"] + "\n\n<|Assistant|>:",
        BasicImageTransform=Transform, dynamic_preprocess=dynamic_preprocess, ImageOps=ImageOps,
        text_encode=lambda tok, text, bos, eos: [7] * len(text.split()))
    content = content_for("CARD_PROMPT", "q?", {"CARD_PROMPT": "Free OCR. "})
    assert content == "<image>\nFree OCR. "
    big = prepare_inputs(remote, None, Image.new("RGB", (1800, 1200)), content, torch.float16, torch, "cpu")
    assert big["visual_tokens"] == 16 * 16 + 1 + (12 * 3) * (12 * 2)     # 256 + 1 + 6 x 144
    ids, mask = big["input_ids"][0], big["images_seq_mask"][0]
    assert ids[0] == 0 and int((ids == IMAGE_TOKEN_ID).sum()) == big["visual_tokens"] == int(mask.sum())
    crops, ori = big["images"][0]
    assert crops.shape == (6, 3, 768, 768) and ori.shape == (1, 3, 1024, 1024) and ori.dtype == torch.float16
    assert big["images_spatial_crop"].tolist() == [[3, 2]]
    small = prepare_inputs(remote, None, Image.new("RGB", (600, 400)), content, torch.float16, torch, "cpu")
    assert small["visual_tokens"] == 257 and small["images"][0][0].shape == (1, 3, 1024, 1024)
