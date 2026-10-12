"""W4: locked-split selection, image hash, decode-time stop, and the four configs."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from PIL import Image

from labbs2026.model_survey.plan import image_sha256, run_items, validate
from labbs2026.model_survey.stop import LoopStoppingCriteria, first_stop, replay
from labbs2026.thai_marks.loop_cut import variant_b

ROOT = Path(__file__).resolve().parents[1]
W4 = ["w4a", "w4b", "w4c", "w4c_deepseek"]
SOURCES = {"typhoon": None, "base": None, "wayu": "m1", "pathumma": "m5", "qwen3vl4b": "m1",
           "paddle": "m1", "sealion": "m6a", "deepseek": "m6b"}


def _config(name: str) -> dict:
    return yaml.safe_load((ROOT / "configs/model_survey" / f"{name}.yaml").read_text("utf-8"))


def test_run_items_splits_into_calibration_and_its_complement():
    ids = ["a", "b", "c", "d", "e"]
    ordered = [0, 1, 2, 3, 4]
    calibration = {"b", "d"}
    cal = run_items(ordered, calibration, ids, "calibration")
    locked = run_items(ordered, calibration, ids, "locked")
    assert [ids[i] for i in cal] == ["b", "d"]
    assert [ids[i] for i in locked] == ["a", "c", "e"]
    with pytest.raises(ValueError):
        run_items(ordered, calibration, ids, "everything")


def test_image_hash_depends_on_pixels_and_size_only():
    a = Image.new("RGB", (4, 3), (10, 20, 30))
    b = Image.new("RGB", (4, 3), (10, 20, 30))
    c = Image.new("RGB", (3, 4), (10, 20, 30))
    d = Image.new("RGB", (4, 3), (10, 20, 31))
    assert image_sha256(a) == image_sha256(b)
    assert len({image_sha256(a), image_sha256(c), image_sha256(d)}) == 3


class CharTokenizer:
    """One token per character: decoding a prefix is the prefix itself."""

    def encode(self, text):
        return [ord(ch) for ch in text]

    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i) for i in ids)


def _decode(ids):
    return "".join(chr(i) for i in ids)


@pytest.mark.parametrize("text", [
    "ข้อความ ก่อน " + "ซ้ำซ้ำ " * 12 + "ท้าย",
    "intro " + "abcd" * 20,
    "prefix " + ("long unit of text with a letter x " * 7) + "end",
    "no loop here at all, just ordinary text อ่านได้ปกติ",
])
def test_replay_matches_variant_b(text):
    record = {"raw_output": text, "reached_max_new_tokens": False}
    ids = CharTokenizer().encode(text)
    out = replay(ids, _decode, variant_b(record))
    assert out["equal"]
    loops = variant_b(record) != text
    assert (out["stopped_at"] is not None) == loops


def test_first_stop_is_the_earliest_firing_prefix():
    text = "start " + "abcd" * 10
    ids = CharTokenizer().encode(text)
    t = first_stop(ids, _decode)
    assert t is not None
    # a linear scan agrees with the bisection
    linear = next(n for n in range(1, len(ids) + 1)
                  if variant_b({"raw_output": _decode(ids[:n]), "reached_max_new_tokens": False})
                  != _decode(ids[:n]))
    assert t == linear


def test_criterion_fires_on_generated_tokens_only():
    torch = pytest.importorskip("torch")
    tok = CharTokenizer()
    prompt = tok.encode("abcd" * 10)              # a repeat in the prompt must not count
    criterion = LoopStoppingCriteria(tok, prompt_length=len(prompt))
    clean = torch.tensor([prompt + tok.encode("ordinary output")])
    assert not criterion(clean, None)
    looping = torch.tensor([prompt + tok.encode("x " + "wxyz" * 9)])
    assert criterion(looping, None)
    assert criterion.finish("x " + "wxyz" * 9) == "x wxyz"


@pytest.mark.parametrize("name", W4)
def test_w4_configs_run_on_locked_and_validate(name):
    config = _config(name)
    assert config["status"] == "APPROVED"
    assert config["split"] == {"seed": 20260927, "calibration_fraction": 0.30, "run_on": "locked"}
    assert config["registration"] == "docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md"
    validate(config)
    m1 = _config("m1")
    assert config["benchmark"] == m1["benchmark"]
    for key in ("dtype_preferred", "dtype_fallback", "image_policy", "max_new_tokens", "generation", "use_cache"):
        assert config["runtime"][key] == m1["runtime"][key], key
    assert config["scoring"]["order_free"] == m1["scoring"]["order_free"]
    assert config["scoring"]["bootstrap"] == {"resamples": 10000, "seed": 20261012, "cluster": "image_sha256"}


def test_w4_models_are_the_calibration_checkpoints_and_prompts():
    t1 = yaml.safe_load((ROOT / "configs/thai_marks/t1_t2.yaml").read_text("utf-8"))["models"]
    roles = {}
    for name in W4:
        config = _config(name)
        for role, model in config["models"].items():
            roles[role] = (name, model)
            source = SOURCES[role]
            if source is None:
                ref = t1[role]
            else:
                ref = _config(source)["models"][role]
                for kind in model["prompts"]:
                    assert config["prompts"][kind] == _config(source)["prompts"][kind], (role, kind)
            assert (model["model_id"], model["revision"]) == (ref["model_id"], ref["revision"]), role
    assert set(roles) == set(SOURCES)                 # eight models, InternVL excluded
    assert "internvl" not in roles
    assert roles["pathumma"][1]["prompts"] == ["CARD_PROMPT", "BENCHMARK_QUESTION"]
    assert {r for r, (n, _) in roles.items() if n == "w4a"} == {"typhoon", "base", "wayu", "pathumma"}


def test_w4_caps_sum_within_the_approved_total():
    caps = {name: _config(name)["budget_cap_t4_hours"] for name in W4}
    assert caps["w4a"] <= 18 and caps["w4b"] <= 10 and caps["w4c"] + caps["w4c_deepseek"] <= 15
    assert sum(caps.values()) <= 45
