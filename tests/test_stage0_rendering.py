import hashlib
from pathlib import Path

import numpy as np

from labbs2026.stage0.rendering import render_pair, renderer_versions


ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "assets/fonts/noto/NotoSansThai-Regular.ttf"


def _digest(image) -> str:
    return hashlib.sha256(np.asarray(image).tobytes()).hexdigest()


def test_harfbuzz_freetype_render_is_deterministic() -> None:
    arguments = {
        "font_path": FONT,
        "font_size": 96,
        "canvas": (448, 448),
        "position_offset": (0, 0),
        "foreground": "#000000",
        "background": "#FFFFFF",
    }
    first = render_pair("กี", "กี่", **arguments)
    second = render_pair("กี", "กี่", **arguments)

    assert [_digest(image) for image in first[:3]] == [
        _digest(image) for image in second[:3]
    ]
    assert first[3] == second[3]


def test_pair_uses_shared_origin_and_nonempty_difference_mask() -> None:
    image_a, image_b, difference, metadata = render_pair(
        "กี",
        "กี่",
        font_path=FONT,
        font_size=96,
        canvas=(448, 448),
        position_offset=(0, 0),
        foreground="#000000",
        background="#FFFFFF",
    )

    assert image_a.size == image_b.size == difference.size == (448, 448)
    assert not metadata.missing_glyph
    assert metadata.ink_pixels_a > 0
    assert metadata.ink_pixels_b > 0
    assert metadata.critical_pixel_area > 0
    assert metadata.difference_threshold == 1
    assert metadata.actual_origin_delta == (0, 0)
    assert metadata.critical_bbox != (0, 0, 0, 0)
    assert metadata.shared_origin[0] > 0
    assert metadata.shared_origin[1] > 0


def test_difference_mask_is_reproducible_and_thresholded() -> None:
    first = render_pair(
        "กี",
        "กี่",
        font_path=FONT,
        font_size=96,
        canvas=(448, 448),
        position_offset=(0, 0),
        foreground="#000000",
        background="#FFFFFF",
        difference_threshold=1,
        difference_rule="MAI_EK_IN_UPPER_CONTEXT",
    )
    second = render_pair(
        "กี",
        "กี่",
        font_path=FONT,
        font_size=96,
        canvas=(448, 448),
        position_offset=(0, 0),
        foreground="#000000",
        background="#FFFFFF",
        difference_threshold=1,
        difference_rule="MAI_EK_IN_UPPER_CONTEXT",
    )

    assert first[2].tobytes() == second[2].tobytes()
    assert first[3].critical_pixel_area == second[3].critical_pixel_area
    assert first[3].coverage_delta_sum == second[3].coverage_delta_sum


def test_contextual_glyph_change_outside_tone_mark_is_rejected() -> None:
    result = render_pair(
        "ฬา",
        "ฬ่า",
        font_path=FONT,
        font_size=96,
        canvas=(448, 448),
        position_offset=(0, 0),
        foreground="#000000",
        background="#FFFFFF",
        difference_rule="MAI_EK_ADDITION",
    )

    assert result[3].unexpected_contextual_layout_change
    assert result[3].shaping_change_status == "FAIL_CONTEXTUAL_GLYPH_SUBSTITUTION"


def test_renderer_versions_are_auditable() -> None:
    versions = renderer_versions()

    assert versions["engine"] == "uharfbuzz+freetype-py"
    assert versions["uharfbuzz"]
    assert versions["freetype_py"]
    assert len(versions["freetype_library"]) == 3
