"""INPUT_SIDE_D1: shifted crops never resample; flips counted against the d = 32 control."""

from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

from labbs2026.find_vs_read.geometry import FACTOR, MIN_PIXELS, crop_rect, prepare_page, processor_size
from labbs2026.input_side.analysis import item_rows, phase_variable_marks, summarize
from labbs2026.input_side.phase import SHIFTS, shifted_crop, shifted_window

ROOT = Path(__file__).resolve().parents[1]


def _page():
    rng = np.random.default_rng(0)
    return prepare_page(Image.fromarray(rng.integers(0, 256, (810, 1080, 3), dtype=np.uint8)))


@pytest.mark.parametrize("d", SHIFTS)
def test_shifted_crop_is_never_resized_and_keeps_pixels(d):
    page = _page()
    rect = crop_rect((274, 385, 573, 501), page.size, margin=0.25)
    crop = shifted_crop(page, rect, d)
    assert crop.width % FACTOR == 0 and crop.height % FACTOR == 0 and crop.width * crop.height >= MIN_PIXELS
    assert processor_size(*crop.size) == crop.size              # the processor will not resample it
    window = np.asarray(shifted_window(page, rect, d))
    left, top, right, bottom = rect
    src = np.asarray(page)
    # rows d.. of the window are the page rows top..bottom-d: content moved down by d, untouched
    assert np.array_equal(window[d:], src[top:bottom - d, left:right])


def test_rows_outside_the_page_are_white():
    page = _page()
    rect = (0, 0, 256, 64)
    window = np.asarray(shifted_window(page, rect, 12))
    assert np.all(window[:12] == 255)
    assert np.array_equal(window[12:], np.asarray(page)[0:52, 0:256])


def test_d32_moves_content_one_token_row():
    page = _page()
    rect = (64, 128, 320, 256)
    w0, w32 = np.asarray(shifted_window(page, rect, 0)), np.asarray(shifted_window(page, rect, 32))
    assert np.array_equal(w32[32:], w0[:-32])                  # same pixels, one 32-px row lower


def test_bad_inputs():
    page = _page()
    with pytest.raises(ValueError):
        shifted_window(page, (0, 0, 100, 64), 0)               # not a multiple of the grid
    with pytest.raises(ValueError):
        shifted_window(page, (0, 0, 64, 64), -4)


def _arm(raw):
    return {"raw_output": raw, "reached_max_new_tokens": False, "seconds_generate": 1.0, "visual_tokens": 96}


def test_flips_and_phase_variable_marks():
    ref = "ทองเนื้อเก้า"
    records = [{"id": "a", "task": "F", "reference": ref, "arms": {
        "D0": _arm(ref), "D4": _arm("ทองเนือเก้า"), "D8": _arm(ref), "D12": _arm(ref),
        "D16": _arm(ref), "D32": _arm(ref), "D64": _arm(ref)}}]
    rows = item_rows(records)
    s = summarize(rows)
    assert s["flips_vs_D0"]["D4"]["TONE"]["flips"] == 1        # the first tone mark lost at d = 4
    assert s["flips_vs_D0"]["D32"]["TONE"]["flips"] == 0       # controls: no change
    assert s["flips_vs_D0"]["D64"]["TONE"]["flips"] == 0
    assert s["flips_vs_D0"]["D8"]["TONE"] == {"flips": 0, "scored_in_both": 2}
    assert phase_variable_marks(rows)["TONE"] == {"scored_in_all": 2, "not_constant": 1}
    assert s["found_per_shift"]["D0"] == 1


def test_config_draft_and_hashed_files():
    import hashlib
    import importlib.util

    config = yaml.safe_load((ROOT / "configs/input_side/d1.yaml").read_text("utf-8"))
    assert config["status"] == "APPROVED" and config["authorization"].startswith("docs/DECISION_LOG.md")
    assert tuple(config["shifts"]) == SHIFTS
    f1 = yaml.safe_load((ROOT / "configs/find_vs_read/f1.yaml").read_text("utf-8"))
    assert config["crop_prompt"] == f1["crop_prompt"] and config["crop_margin"] == f1["crop_margin"]
    assert hashlib.sha256(config["crop_prompt"].encode("utf-8")).hexdigest() == config["crop_prompt_sha256"]
    spec = importlib.util.spec_from_file_location("ik", ROOT / "scripts/input_side_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for path in module.HASHED:
        assert (ROOT / path).is_file(), path
