import random

import numpy as np
import pytest
from PIL import Image

from labbs2026.find_vs_read.geometry import (
    FACTOR,
    MIN_PIXELS,
    crop_padded,
    crop_rect,
    draw_rect,
    parse_box,
    prepare_page,
    processor_size,
)
from labbs2026.find_vs_read.scoring import best_window, chance_found_rate, score_answer
from labbs2026.output_diagnostics.distance import levenshtein

QUESTION = ("แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้วช่วยดึงข้อความที่อยู่ในพิกัด "
            "[274, 385, 573, 501] ของรูปภาพออกมาให้หน่อย")


def test_parse_box_real_template_and_errors():
    assert parse_box(QUESTION) == (274, 385, 573, 501)
    assert parse_box("พิกัด [1.5, 2, 3, 4.25]") == (1.5, 2, 3, 4.25)
    for bad in ("no box", "[1, 2, 3, 4] and [5, 6, 7, 8]", "[500, 10, 400, 20]", "[0, 0, 1001, 5]"):
        with pytest.raises(ValueError):
            parse_box(bad)


def _image(w, h, seed=0):
    return Image.fromarray(np.random.default_rng(seed).integers(0, 256, (h, w, 3), dtype=np.uint8))


@pytest.mark.parametrize("w,h", [(1080, 810), (257, 400), (4032, 3024), (300, 200)])
def test_prepared_page_is_a_fixed_point_of_the_processor_size_rule(w, h):
    page = prepare_page(_image(w, h))
    assert page.width % FACTOR == 0 and page.height % FACTOR == 0
    assert processor_size(*page.size) == page.size  # the processor will not resize it again


def test_crop_keeps_page_pixels_and_grid_phase():
    page = prepare_page(_image(1080, 810))
    rect = crop_rect((274, 385, 573, 501), page.size, margin=0.25)
    assert all(v % FACTOR == 0 for v in rect)
    crop = crop_padded(page, rect)
    content = np.asarray(crop)[: rect[3] - rect[1], : rect[2] - rect[0]]
    assert np.array_equal(content, np.asarray(page)[rect[1]:rect[3], rect[0]:rect[2]])
    assert crop.width % FACTOR == 0 and crop.height % FACTOR == 0
    assert crop.width * crop.height >= MIN_PIXELS
    assert processor_size(*crop.size) == crop.size  # no resize: magnification unchanged


def test_crop_margin_covers_the_box_and_clips_at_edges():
    size = (1792, 1280)
    x1, y1, x2, y2 = 100, 200, 300, 230
    rect = crop_rect((x1, y1, x2, y2), size, margin=0.25)
    box_h = (y2 - y1) * size[1] / 1000
    assert rect[1] <= y1 * size[1] / 1000 - 0.25 * box_h
    assert rect[3] >= y2 * size[1] / 1000 + 0.25 * box_h
    assert crop_rect((0, 0, 1000, 1000), size, margin=0.25) == (0, 0, 1792, 1280)


def test_small_crop_is_padded_not_enlarged():
    page = prepare_page(_image(1080, 810))
    crop = crop_padded(page, (64, 64, 128, 96))  # 64 x 32 content
    assert crop.size == (256, 256)
    arr = np.asarray(crop)
    assert np.all(arr[32:, :] == 255) and np.all(arr[:, 64:] == 255)


def test_draw_rect_changes_only_the_outline():
    page = prepare_page(_image(1080, 810))
    rect = (64, 64, 256, 128)
    diff = np.any(np.asarray(draw_rect(page, rect)).astype(int) != np.asarray(page).astype(int), axis=2)
    assert diff.any()
    assert not diff[rect[1] + 3: rect[3] - 3, rect[0] + 3: rect[2] - 3].any()


def _brute(ref, hyp):
    return min(levenshtein(ref, hyp[s:e]) for s in range(len(hyp) + 1) for e in range(s, len(hyp) + 1))


def test_best_window_matches_brute_force():
    rng = random.Random(1)
    alphabet = "กขค่้ัิ a"
    for _ in range(300):
        ref = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 6)))
        hyp = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        d, s, e = best_window(ref, hyp)
        assert d == _brute(ref, hyp)
        assert levenshtein(ref, hyp[s:e]) == d


def test_score_answer_found_read_and_overgeneration():
    page_dump = "หัวเรื่อง ทองเนื้อเก้า ราคาถูก โทร 02"
    s = score_answer("ทองเนื้อเก้า", page_dump)
    assert s["found"] and s["exact"] and s["extra_chars"] == len(page_dump) - len("ทองเนื้อเก้า")
    s = score_answer("ทองเนื้อเก้า", "ทองเนือเกา")  # found, two tone marks dropped
    assert s["found"] and not s["exact"] and s["TONE_error"] == 2
    assert not score_answer("ทองเนื้อเก้า", "รถไฟฟ้า")["found"]


def test_chance_found_rate():
    assert chance_found_rate(["ก", "ข", "ค"], ["ข ค", "ค ก", "ก ข"]) == 1.0
    # each hypothesis is its own item's correct answer, so the shifted pairing never matches
    assert chance_found_rate(["ทองเนื้อเก้า", "รถไฟฟ้า"], ["ทองเนื้อเก้า", "รถไฟฟ้า"]) == 0.0
    assert chance_found_rate(["ก"], ["ก"]) is None
