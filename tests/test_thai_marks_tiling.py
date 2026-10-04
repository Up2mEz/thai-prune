"""Tile grid for P-ZOOM: coverage, overlap, order and the zoom it buys."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.tiling import crop_tiles, read_scale, tile_boxes, zoom_factor

SIZES = [(1000, 1400), (1240, 1754), (2480, 3508), (301, 300), (977, 613), (7, 5)]


@pytest.mark.parametrize("size", SIZES)
def test_tiles_stay_inside_the_image_and_cover_every_pixel(size) -> None:
    width, height = size
    tiles = tile_boxes(size)
    assert len(tiles) == 4
    covered_x, covered_y = set(), set()
    for tile in tiles:
        left, top, right, bottom = tile.box
        assert 0 <= left < right <= width and 0 <= top < bottom <= height
        covered_x.update(range(left, right))
        covered_y.update(range(top, bottom))
    assert covered_x == set(range(width)) and covered_y == set(range(height))


def test_neighbours_overlap_by_the_requested_share_of_a_tile() -> None:
    tiles = tile_boxes((1000, 1400), overlap=0.15)
    left, right = tiles[0], tiles[1]
    tile_width = left.size[0]
    shared = left.box[2] - right.box[0]
    assert abs(shared / tile_width - 0.15) < 0.01
    top, bottom = tiles[0], tiles[2]
    assert abs((top.box[3] - bottom.box[1]) / top.size[1] - 0.15) < 0.01


def test_a_line_straddling_the_middle_cut_is_whole_in_some_tile() -> None:
    # a 5%-of-height line placed across the page's vertical middle
    width, height = 1000, 1400
    line = (height // 2 - 35, height // 2 + 35)
    tiles = tile_boxes((width, height), overlap=0.15)
    assert any(t.box[1] <= line[0] and line[1] <= t.box[3] for t in tiles)


def test_tiles_are_row_major_with_matching_indices() -> None:
    tiles = tile_boxes((1000, 1000), rows=2, cols=3)
    assert [t.index for t in tiles] == list(range(6))
    assert [(t.row, t.col) for t in tiles] == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
    assert tiles[0].box[0] == tiles[3].box[0] and tiles[0].box[1] == tiles[2].box[1]


def test_one_tile_is_the_whole_image_and_zero_overlap_partitions() -> None:
    assert [t.box for t in tile_boxes((640, 480), rows=1, cols=1)] == [(0, 0, 640, 480)]
    tiles = tile_boxes((1000, 600), overlap=0.0)
    assert [t.box for t in tiles] == [(0, 0, 500, 300), (500, 0, 1000, 300),
                                     (0, 300, 500, 600), (500, 300, 1000, 600)]


def test_tiling_is_deterministic() -> None:
    assert tile_boxes((1234, 1777)) == tile_boxes((1234, 1777))


@pytest.mark.parametrize("kwargs", [{"rows": 0}, {"cols": 0}, {"overlap": -0.1}, {"overlap": 1.0}])
def test_invalid_grids_are_rejected(kwargs) -> None:
    with pytest.raises(ValueError):
        tile_boxes((1000, 1000), **kwargs)
    with pytest.raises(ValueError):
        tile_boxes((0, 10))


def test_crop_tiles_returns_images_of_the_box_size() -> None:
    from PIL import Image

    image = Image.new("RGB", (1000, 1400), "white")
    for tile, crop in crop_tiles(image):
        assert crop.size == tile.size


def test_zoom_factor_is_the_ratio_of_resize_policy_scales() -> None:
    # page 1000x1400 -> long side 1800 (scale 1.2857); tile 541x757 -> 1800 (scale 2.378)
    page = (1000, 1400)
    tile = tile_boxes(page)[0].size
    assert read_scale(page) == pytest.approx(1800 / 1400)
    assert zoom_factor(page, tile) == pytest.approx(1400 / max(tile))
    assert 1.7 < zoom_factor(page, tile) < 1.9  # draft: "about 2x"
    assert zoom_factor(page, page) == 1.0


def test_small_images_are_not_rescaled_by_the_policy() -> None:
    assert read_scale((300, 200)) == 1.0
