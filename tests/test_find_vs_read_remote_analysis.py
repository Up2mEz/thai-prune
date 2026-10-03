"""FIND_VS_READ_F1 arm plumbing on a random-weight Qwen3-VL (CPU) and the registered analysis."""

from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

from labbs2026.find_vs_read.analysis import item_rows, paired_fates, summarize
from labbs2026.find_vs_read.geometry import crop_rect, image_sha256, prepare_page
from labbs2026.find_vs_read.remote import arm_input, generate, geometry_record
from labbs2026.find_vs_read.scoring import mark_fates
from labbs2026.thai_marks.decompose import mark_decomposition

from test_remedies_contrastive import _image_inputs
from test_spec_decode_identity import _toy_qwen3vl

ROOT = Path(__file__).resolve().parents[1]
QUESTION = ("แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้วช่วยดึงข้อความที่อยู่ในพิกัด "
            "[274, 385, 573, 501] ของรูปภาพออกมาให้หน่อย")
BOX = (274, 385, 573, 501)


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


def _source(w=3024, h=2268):
    return Image.fromarray(np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8))


def test_arm_inputs_and_geometry_record():
    source = _source()
    page = prepare_page(source)
    rect = crop_rect(BOX, page.size, margin=0.25)
    kw = {"crop_prompt": "อ่าน", "margin": 0.25}
    whole, q = arm_input("WHOLE", source, page, QUESTION, rect, BOX, **kw)
    marked, q2 = arm_input("WHOLE_MARKED", source, page, QUESTION, rect, BOX, **kw)
    same, p1 = arm_input("CROP_SAME_SCALE", source, page, QUESTION, rect, BOX, **kw)
    rescaled, p2 = arm_input("CROP_RESCALED", source, page, QUESTION, rect, BOX, **kw)
    assert whole is page and q == q2 == QUESTION and p1 == p2 == "อ่าน"
    assert marked.size == page.size and image_sha256(marked) != image_sha256(page)
    assert same.size[0] >= rect[2] - rect[0]
    geo = geometry_record(source, page, BOX, rect, margin=0.25)
    # a 3024-px photo shrinks to ~1800 px as a page; its crop is enlarged as a "page" of its own
    assert geo["page_scale"] < 1 and geo["magnification_rescaled_vs_page"] > 2
    assert list(rescaled.size) == geo["crop_rescaled_size"]
    with pytest.raises(ValueError):
        arm_input("OTHER", source, page, QUESTION, rect, BOX, **kw)


def test_generate_records_hash_not_image():
    model = _toy_qwen3vl()
    proc = FakeProcessor()
    image = Image.new("RGB", (64, 64))
    out = generate(model, proc, image, "q", device="cpu", max_new_tokens=6,
                   generation={"do_sample": False, "num_beams": 1, "repetition_penalty": 1.0,
                               "no_repeat_ngram_size": 0, "eos_token_id": 511, "pad_token_id": 511,
                               "min_new_tokens": 6})
    assert out["generated_tokens"] == 6 and out["reached_max_new_tokens"]
    assert out["visual_tokens"] == 24 and out["image_sha256"] == image_sha256(image)
    assert not any(isinstance(v, Image.Image) for v in out.values())


def test_mark_fates_agree_with_t1_decomposition():
    for ref, hyp in (("ทองเนื้อเก้า", "ทองเนือเกา"), ("น้ำใจ ก่อน", "นำใจ กอน"), ("ครู่", "ครู่")):
        fates = mark_fates(ref, hyp)
        dec = mark_decomposition(ref, hyp)
        for kind in ("TONE", "UPPER", "LOWER"):
            mine = [m for m in fates if m["kind"] == kind]
            assert len(mine) == dec[kind].get("n", 0)
            assert sum(m["base_correct"] for m in mine) == dec[kind].get("base_correct_n", 0)
            assert sum(m["base_correct"] and m["fate"] != "correct" for m in mine) == dec[kind].get("base_correct_error", 0)


def _arm(raw, seconds=1.0, hit=False):
    return {"raw_output": raw, "reached_max_new_tokens": hit, "seconds_generate": seconds, "visual_tokens": 100}


def test_paired_fates_exact_counts_and_localisation():
    records = [
        {"id": "a", "task": "F", "reference": "ทองเนื้อเก้า",
         "arms": {"WHOLE": _arm("ทองเนือเก้า"), "CROP_SAME_SCALE": _arm("ทองเนื้อเก้า"),
                  "CROP_RESCALED": _arm("ทองเนื้อเกา"), "WHOLE_MARKED": {"failed": True}}},
        {"id": "b", "task": "F", "reference": "รถไฟฟ้า",
         "arms": {"WHOLE": _arm("ข้อความอื่น", hit=True), "CROP_SAME_SCALE": _arm("รถไฟฟ้า"),
                  "CROP_RESCALED": _arm("รถไฟฟ้า"), "WHOLE_MARKED": _arm("รถไฟฟ้า")}},
    ]
    rows = item_rows(records)
    finding = paired_fates(rows, "CROP_SAME_SCALE", "WHOLE")
    assert finding["fates"]["TONE"] == {"correct->correct": 1, "scored_only_in_CROP_SAME_SCALE": 1,
                                        "wrong->correct": 1}
    magnification = paired_fates(rows, "CROP_RESCALED", "CROP_SAME_SCALE")
    assert magnification["fates"]["TONE"] == {"correct->correct": 2, "correct->wrong": 1}
    s = summarize(rows)
    assert s["WHOLE"]["localisation_failures"] == 1 and s["WHOLE"]["reached_max_new_tokens"] == 1
    assert s["WHOLE_MARKED"]["failed"] == 1 and s["WHOLE_MARKED_vs_WHOLE"]["items"] == 1


def test_config_is_a_draft_until_both_researchers_agree():
    import hashlib
    import importlib.util

    config = yaml.safe_load((ROOT / "configs/find_vs_read/f1.yaml").read_text("utf-8"))
    assert config["status"] == "DRAFT_FOR_REVIEW" and config["authorization"] is None
    assert config["arms"] == ["WHOLE", "CROP_SAME_SCALE", "CROP_RESCALED", "WHOLE_MARKED"]
    assert config["runtime"]["generation"]["do_sample"] is False
    assert hashlib.sha256(config["crop_prompt"].encode("utf-8")).hexdigest() == config["crop_prompt_sha256"]
    spec = importlib.util.spec_from_file_location("fk", ROOT / "scripts/find_vs_read_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in module.HASHED:
        assert (ROOT / path).is_file(), path
