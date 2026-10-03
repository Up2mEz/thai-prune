"""FIND_VS_READ_F1 arm plumbing on a random-weight Qwen3-VL (CPU) and the registered analysis."""

import numpy as np
import pytest
import torch
import yaml
from pathlib import Path
from PIL import Image

from labbs2026.find_vs_read.analysis import item_rows, summarize
from labbs2026.find_vs_read.geometry import crop_rect, prepare_page
from labbs2026.find_vs_read.remote import arm_input, generate

from test_remedies_contrastive import _image_inputs
from test_spec_decode_identity import _toy_qwen3vl

ROOT = Path(__file__).resolve().parents[1]
QUESTION = "แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้วช่วยดึงข้อความที่อยู่ในพิกัด [274, 385, 573, 501] ของรูปภาพออกมาให้หน่อย"


class FakeProcessor:
    """Records the image it was given; returns fixed toy inputs."""

    def __init__(self):
        self.seen = []

    def apply_chat_template(self, messages, **_):
        for part in messages[0]["content"]:
            if part["type"] == "image":
                self.seen.append(part["image"].size)
        return dict(_image_inputs(0))

    def decode(self, ids, skip_special_tokens=True):
        return " ".join(str(i) for i in ids)


def test_arm_inputs_share_one_page():
    page = prepare_page(Image.fromarray(np.random.default_rng(0).integers(0, 256, (810, 1080, 3), dtype=np.uint8)))
    rect = crop_rect((274, 385, 573, 501), page.size, margin=0.25)
    whole, q = arm_input("WHOLE", page, QUESTION, rect, "อ่าน")
    marked, q2 = arm_input("WHOLE_MARKED", page, QUESTION, rect, "อ่าน")
    crop, p = arm_input("CROP", page, QUESTION, rect, "อ่าน")
    assert whole is page and q == q2 == QUESTION and p == "อ่าน"
    assert marked.size == page.size and marked is not page
    assert crop.size[0] >= rect[2] - rect[0]
    with pytest.raises(ValueError):
        arm_input("OTHER", page, QUESTION, rect, "อ่าน")


def test_generate_records_on_toy_model():
    model = _toy_qwen3vl()
    proc = FakeProcessor()
    image = Image.new("RGB", (64, 64))
    out = generate(model, proc, image, "q", device="cpu", max_new_tokens=6,
                   generation={"do_sample": False, "num_beams": 1, "repetition_penalty": 1.0,
                               "no_repeat_ngram_size": 0, "eos_token_id": 511, "pad_token_id": 511,
                               "min_new_tokens": 6})
    assert out["generated_tokens"] == 6 and out["reached_max_new_tokens"]
    assert out["visual_tokens"] == 24 and out["image_size"] == [64, 64] and proc.seen == [(64, 64)]


def _arm(raw, seconds=1.0, hit=False):
    return {"raw_output": raw, "reached_max_new_tokens": hit, "seconds_generate": seconds, "visual_tokens": 100}


def test_analysis_found_transitions_and_marks_on_found_only():
    records = [
        {"id": "a", "task": "F", "reference": "ทองเนื้อเก้า",
         "arms": {"WHOLE": _arm("ทองเนือเกา"), "CROP": _arm("ทองเนื้อเก้า"), "WHOLE_MARKED": _arm("ทองเนือเก้า")}},
        {"id": "b", "task": "F", "reference": "รถไฟฟ้า",
         "arms": {"WHOLE": _arm("ข้อความอื่นทั้งหน้า ไม่เกี่ยวเลย", hit=True), "CROP": _arm("รถไฟฟ้า"),
                  "WHOLE_MARKED": {"failed": True}}},
    ]
    s = summarize(item_rows(records), resamples=200)
    c = s["CROP_vs_WHOLE"]
    assert c["found_transitions"] == {"found->found": 1, "missed->found": 1}
    assert c["found_in_both"] == 1
    tone = c["TONE_mark_specific_error_found_in_both"]
    assert tone["WHOLE"] == 1.0 and tone["CROP"] == 0.0     # both tone marks lost in WHOLE, none in CROP
    assert s["WHOLE"]["reached_max_new_tokens"] == 1
    assert s["WHOLE_MARKED_vs_WHOLE"]["items"] == 1          # the failed arm is left out, not scored


def test_config_is_a_draft_until_both_researchers_agree():
    config = yaml.safe_load((ROOT / "configs/find_vs_read/f1.yaml").read_text("utf-8"))
    assert config["status"] == "DRAFT_FOR_REVIEW" and config["authorization"] is None
    assert config["arms"] == ["WHOLE", "CROP", "WHOLE_MARKED"]
    assert config["runtime"]["generation"]["do_sample"] is False
    import importlib.util

    spec = importlib.util.spec_from_file_location("fk", ROOT / "scripts/find_vs_read_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in module.HASHED:
        assert (ROOT / path).is_file(), path
