"""`remedies.remote.run_one` for every arm kind, on a random-weight Qwen3-VL (CPU).

A stand-in processor returns fixed toy inputs, so the arm plumbing (PAI context,
VCD noise, no-image contrast, generation pinning) is exercised end to end
without weights or data.
"""

import numpy as np
import pytest
import torch
import yaml
from pathlib import Path
from PIL import Image

from labbs2026.remedies.design import arm_names, noise_seed, pilot_ids
from labbs2026.remedies.remote import run_one

from test_remedies_contrastive import _image_inputs
from test_spec_decode_identity import _toy_qwen3vl

ROOT = Path(__file__).resolve().parents[1]
GEN = {"do_sample": False, "num_beams": 1, "repetition_penalty": 1.0, "no_repeat_ngram_size": 0}
MAX_NEW = 12


class FakeProcessor:
    def __init__(self):
        self.image_inputs = _image_inputs(0)
        ids = self.image_inputs["input_ids"][0]
        keep = (self.image_inputs["mm_token_type_ids"][0] == 0) & (ids != 502) & (ids != 503)
        self.text_ids = ids[keep][None]

    def apply_chat_template(self, messages, **_):
        has_image = any(part["type"] == "image" for part in messages[0]["content"])
        if has_image:
            return dict(self.image_inputs)
        return {"input_ids": self.text_ids, "attention_mask": torch.ones_like(self.text_ids)}

    def decode(self, ids, skip_special_tokens=True):
        return " ".join(str(i) for i in ids)


@pytest.fixture(scope="module")
def setup():
    model = _toy_qwen3vl()
    model.generation_config.eos_token_id = 511
    model.generation_config.pad_token_id = 511
    image = Image.fromarray(np.random.default_rng(0).integers(0, 256, (32, 48, 3), dtype=np.uint8))
    return model, FakeProcessor(), image


def _run(setup, arm):
    model, processor, image = setup
    return run_one(model, processor, image, "prompt", "item-1", arm, seed=20260927, generation=GEN,
                   max_new_tokens=MAX_NEW, eos_ids=[511], device="cpu")


def test_every_arm_runs_and_zero_strength_controls_match_full(setup):
    config = yaml.safe_load((ROOT / "configs/remedies/r1.yaml").read_text("utf-8"))
    arms = {**config["arms"], **config["smoke_controls"]}
    out = {name: _run(setup, arm) for name, arm in arms.items()}
    full = out["FULL"]["new_token_ids"]
    assert len(full) == MAX_NEW and out["FULL"]["reached_max_new_tokens"]
    for name in arms:
        assert out[name]["generated_tokens"] >= 1 and "raw_output" in out[name]
    # zero-strength controls: our machinery alone must not change greedy output (fp32)
    assert out["PAI_ALPHA0"]["new_token_ids"] == full
    assert out["CD_ALPHA0"]["new_token_ids"][:len(full)] == full
    assert out["CD_ALPHA0"]["changed_steps"] == 0
    assert "changed_steps" in out["VCD"] and "changed_steps" in out["M3ID"]


def test_pilot_ids_per_task_in_hash_order():
    items = [(f"a{i}", "Full-page OCR") for i in range(20)] + [(f"b{i}", "Text recognition") for i in range(20)]
    ids = pilot_ids(items, seed=20260927, per_task=3)
    assert len(ids) == 6 and all(i.startswith("a") for i in ids[:3]) and all(i.startswith("b") for i in ids[3:])
    assert ids == pilot_ids(list(reversed(items)), seed=20260927, per_task=3)
    with pytest.raises(ValueError):
        pilot_ids(items + [("a1", "Full-page OCR")], seed=1, per_task=1)


def test_arm_names_and_noise_seed():
    arms = {"VCD": {}, "FULL": {}, "PAI": {}}
    assert arm_names(arms, {"PAI_ALPHA0": {}}, smoke=False) == ["FULL", "VCD", "PAI"]
    assert arm_names(arms, {"PAI_ALPHA0": {}}, smoke=True) == ["FULL", "VCD", "PAI", "PAI_ALPHA0"]
    assert noise_seed("x", 1) == noise_seed("x", 1) != noise_seed("y", 1)


def test_config_pins_greedy_and_hashed_files_exist():
    import importlib.util

    config = yaml.safe_load((ROOT / "configs/remedies/r1.yaml").read_text("utf-8"))
    assert config["runtime"]["generation"] == GEN
    assert config["prompt"] == "BENCHMARK_QUESTION"
    spec = importlib.util.spec_from_file_location("rk", ROOT / "scripts/remedies_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in module.HASHED:
        assert (ROOT / path).is_file(), path


def test_r2_config_and_protected_arm_runs(setup):
    config = yaml.safe_load((ROOT / "configs/remedies/r2.yaml").read_text("utf-8"))
    assert config["status"] == "APPROVED" and set(config["arms"]) == {"FULL", "M3ID", "M3ID_MP"}
    assert config["arms"]["M3ID_MP"] == {**config["arms"]["M3ID"], "protect_marks": True}
    assert config["runtime"]["generation"] == GEN
    control = _run(setup, config["smoke_controls"]["MP_ALPHA0"])
    full = _run(setup, config["arms"]["FULL"])
    assert control["new_token_ids"][:len(full["new_token_ids"])] == full["new_token_ids"]
    protected = _run(setup, config["arms"]["M3ID_MP"])
    assert "protected_steps" in protected and "changed_steps" in protected
