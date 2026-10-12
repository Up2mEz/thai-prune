"""E4a readings."""

from __future__ import annotations

from labbs2026.thai_marks import e4a_analysis as e4


def _page(found: bool, control: bool = True) -> dict:
    return {"lines": [{"group": "absent", "marks": 10, "outcome": "text" if found else "not_found"},
                      {"group": "control", "marks": 10, "outcome": "text" if control else "not_found"}]}


def _view(flags: list[bool], control: bool = True) -> list[dict]:
    return [_page(f, control) for f in flags]


def test_competing_content_reading() -> None:
    pages = 21
    scores = {"repeat": _view([False] * pages),
              "masked_bands": _view([True] * pages),
              "bands100": _view([True] * pages)}
    out = e4.analyze(scores)
    assert out["C1_masked_minus_repeat"]["material"]
    assert not out["C3_bands100_minus_masked"]["material"]
    assert out["reading"] == "competing_content"


def test_image_size_reading() -> None:
    pages = 21
    scores = {"repeat": _view([False] * pages),
              "masked_bands": _view([False] * pages),
              "bands100": _view([True] * pages)}
    assert e4.analyze(scores)["reading"] == "image_size_or_token_count"


def test_crop_effect_not_reproduced_and_control_floor() -> None:
    pages = 21
    none = {"repeat": _view([False] * pages), "masked_bands": _view([False] * pages),
            "bands100": _view([False] * pages)}
    assert e4.analyze(none)["reading"] == "crop_effect_not_reproduced"
    damaged = {"repeat": _view([False] * pages), "masked_bands": _view([True] * pages, control=False),
               "bands100": _view([True] * pages)}
    assert e4.analyze(damaged)["reading"] == "masked_damages_ordinary_reading"
