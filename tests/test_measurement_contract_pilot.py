from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from labbs2026.stage0.measurement_contract_pilot import (
    _anchor_mask,
    add_surrounding_layout,
)


ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets/fonts/noto/NotoSansThai-Regular.ttf"
TARGET_CELL = (160, 144, 288, 304)


def _mask() -> np.ndarray:
    return _anchor_mask(
        font_path=FONT,
        font_size=72,
        canvas_size=(448, 448),
        item_y=(144, 304),
        anchor_cells=[(0, 64), (80, 144), (304, 368), (384, 448)],
        anchors=["ก", "น", "ม", "ล"],
        separator_rectangles=[
            (71, 168, 73, 280),
            (151, 168, 153, 280),
            (295, 168, 297, 280),
            (375, 168, 377, 280),
        ],
    )


def test_surrounding_layout_preserves_target_crop_bytes() -> None:
    isolated = np.full((448, 448, 3), 255, dtype=np.uint8)
    isolated[205:245, 195:255] = 0

    surrounded, metadata = add_surrounding_layout(
        Image.fromarray(isolated), anchor_mask=_mask(), target_cell=TARGET_CELL
    )

    observed = np.asarray(surrounded)
    assert np.array_equal(
        isolated[144:304, 160:288], observed[144:304, 160:288]
    )
    assert metadata["target_pixel_identity"] == "PASS"
    assert metadata["target_layer_sha256_B"] == metadata["target_layer_sha256_C"]
    assert not np.array_equal(isolated, observed)


def test_surrounding_layout_rejects_target_ink_outside_cell() -> None:
    isolated = np.full((448, 448, 3), 255, dtype=np.uint8)
    isolated[10, 10] = 0

    with pytest.raises(ValueError, match="ISOLATED_TARGET_INK_OUTSIDE_TARGET_CELL"):
        add_surrounding_layout(
            Image.fromarray(isolated), anchor_mask=_mask(), target_cell=TARGET_CELL
        )


def test_surrounding_layout_rejects_anchor_ink_inside_target_cell() -> None:
    mask = _mask()
    mask[200, 200] = 255

    with pytest.raises(ValueError, match="ANCHOR_OR_SEPARATOR_INK_INSIDE_TARGET_CELL"):
        add_surrounding_layout(
            Image.new("RGB", (448, 448), "white"),
            anchor_mask=mask,
            target_cell=TARGET_CELL,
        )
