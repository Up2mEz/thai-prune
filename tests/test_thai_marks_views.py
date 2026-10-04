"""P-ZOOM-2 views: what each feeds the model and how much zoom it buys."""

from __future__ import annotations

import pytest
from PIL import Image

from labbs2026.thai_marks.runtime import resize_policy
from labbs2026.thai_marks.tiling import padded, read_scale, view_images

PAGE = Image.new("RGB", (1000, 1400), "white")


def test_padding_adds_a_white_margin_and_keeps_the_page_whole() -> None:
    out = padded(PAGE, 0.04)
    assert out.size == (1000 + 112, 1400 + 112)
    assert out.getpixel((0, 0)) == (255, 255, 255)
    (view,) = view_images(PAGE, {"kind": "pad", "margin": 0.04})
    assert max(view["image"].size) == 1800
    assert view["tile"].box == (0, 0, 1112, 1512)
    assert view["zoom"] == pytest.approx(1400 / 1512, rel=1e-3)  # content a little smaller


def test_scale_view_is_the_policy_image_times_the_factor() -> None:
    (view,) = view_images(PAGE, {"kind": "scale", "factor": 0.9})
    assert view["image"].size == tuple(round(s * 0.9) for s in resize_policy(PAGE).size)
    assert view["zoom"] == pytest.approx(0.9, rel=1e-2)


def test_grid_view_zooms_every_tile_by_the_requested_factor() -> None:
    views = view_images(PAGE, {"kind": "grid", "rows": 3, "cols": 1, "overlap": 0.15, "zoom": 1.85})
    assert [v["tile"].index for v in views] == [0, 1, 2]
    for v in views:
        assert v["tile"].box[0] == 0 and v["tile"].box[2] == 1000  # full width: no vertical cut
        assert v["zoom"] == pytest.approx(1.85, rel=1e-2)
        scale = 1.85 * read_scale(PAGE.size)
        assert v["image"].width == round(1000 * scale)
    # every row of the page is covered
    assert views[0].get("tile").box[1] == 0 and views[-1]["tile"].box[3] == 1400


def test_a_band_is_not_capped_at_the_card_resolution() -> None:
    (top, *_) = view_images(PAGE, {"kind": "grid", "rows": 3, "cols": 1, "overlap": 0.15, "zoom": 1.85})
    assert top["image"].width > 1800  # the point of bypassing resize_policy


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValueError):
        view_images(PAGE, {"kind": "rotate"})


def test_whole_view_is_exactly_the_t1_input() -> None:
    (view,) = view_images(PAGE, {"kind": "whole"})
    assert view["image"].size == resize_policy(PAGE).size
    assert view["image"].tobytes() == resize_policy(PAGE).tobytes()
    assert view["zoom"] == pytest.approx(1.0, rel=1e-3)  # int() rounding of the policy resize


def test_a_grid_at_zoom_one_is_read_at_page_scale() -> None:
    views = view_images(PAGE, {"kind": "grid", "rows": 3, "cols": 1, "overlap": 0.15, "zoom": 1.0})
    for v in views:
        assert v["zoom"] == pytest.approx(1.0, rel=1e-2)
        assert v["image"].width == round(1000 * read_scale(PAGE.size))
