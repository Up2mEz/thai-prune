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


# --- live decode-time stop check -------------------------------------------------

from labbs2026.model_survey.stop import live_items, stopped_output  # noqa: E402


@pytest.mark.parametrize("text", [
    "ข้อความ ก่อน " + "ซ้ำซ้ำ " * 12 + "ท้าย",
    "intro " + "abcd" * 20,
    "prefix " + ("long unit of text with a letter x " * 7) + "end",
    "no loop here at all, just ordinary text อ่านได้ปกติ",
])
@pytest.mark.parametrize("stride", [1, 3, 8])
def test_stride_with_stopped_output_equals_the_per_token_stop(text, stride):
    torch = pytest.importorskip("torch")
    tok = CharTokenizer()
    ids = tok.encode(text)
    criterion = LoopStoppingCriteria(tok, prompt_length=0, stride=stride)
    generated = []
    for token in ids:                      # greedy decoding replayed one token at a time
        generated.append(token)
        if criterion(torch.tensor([generated]), None):
            break
    if criterion.stopped_at is not None:
        assert criterion.stopped_at % stride == 0
    assert stopped_output(generated, _decode)["text"] == variant_b({"raw_output": text,
                                                                    "reached_max_new_tokens": False})


def test_live_items_take_every_looping_output_and_a_seeded_sample():
    rows = [{"id": f"{i:02d}", "raw_output": ("ab" * 20 if i % 3 == 0 else f"plain text {i}")}
            for i in range(30)]
    items = live_items(rows, sample=4, seed=1)
    looping = [i for i in items if i["looping_offline"]]
    assert [i["id"] for i in looping] == [f"{i:02d}" for i in range(0, 30, 3)]
    assert len(items) - len(looping) == 4
    assert items == live_items(list(reversed(rows)), sample=4, seed=1)


def test_live_stop_config_copies_the_w4_models_and_reads_calibration_only():
    config = _config("w4_live_stop")
    validate(config)
    assert config["split"]["run_on"] == "calibration"
    m1 = _config("m1")
    for key in ("dtype_preferred", "dtype_fallback", "image_policy", "max_new_tokens", "generation", "use_cache"):
        assert config["runtime"][key] == m1["runtime"][key], key
    w4 = {}
    for name in W4:
        source = _config(name)
        for role, model in source["models"].items():
            w4[role] = (model, {k: source["prompts"][k] for k in model["prompts"]})
    assert set(config["models"]) == set(w4)
    for role, model in config["models"].items():
        ref, ref_prompts = w4[role]
        for key in ("model_id", "revision", "prompts", "primary_prompt"):
            assert model[key] == ref[key], (role, key)
        texts = {**config["prompts"], **model.get("prompt_overrides", {})}
        assert {k: texts[k] for k in model["prompts"]} == ref_prompts, role
    assert config["models"]["deepseek"]["runner"] == "m6b"


def test_live_stop_items_are_the_stop_checks_loops():
    import gzip
    import json

    config = _config("w4_live_stop")
    check = json.loads((ROOT / "docs/stage0/data/W4_STOP_CHECK_ed02ad0.json").read_text("utf-8"))["cells"]
    total = 0
    for role, model in config["models"].items():
        archive = ROOT / "docs/stage0/data" / f"{model['calibration_archive']}.json.gz"
        rows = json.loads(gzip.open(archive, "rt", encoding="utf-8").read())["records"][role]
        for kind in model["prompts"]:
            items = live_items([r for r in rows if r["prompt_kind"] == kind],
                               config["live_stop"]["sample_non_looping"], config["live_stop"]["sample_seed"])
            looping = sum(i["looping_offline"] for i in items)
            assert looping == check[f"{role} | {kind}"]["looping"], (role, kind)
            total += looping
    assert total == 185
