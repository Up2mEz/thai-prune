"""The T2 scoring window never collapses to an empty string."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.orthography import Site, window_variants
from labbs2026.thai_marks.runtime import scoring_window_token

MAI_THO = "้"


def _always_clean(_: int) -> bool:
    return True


def test_a_final_mark_that_starts_its_own_token_gets_its_base_in_the_window() -> None:
    # "ข้า" … ending in a mark tokenized alone, as on 10 sites of the 2026-09-27 run.
    text = "ไปก่อน" + MAI_THO
    offsets = [(0, 2), (2, 6), (6, 7)]  # the final ้ is its own token
    site = Site(kind="TONE", index=6, reference=MAI_THO)
    k = scoring_window_token(offsets, site.index, _always_clean, len(text))
    assert offsets[k][0] < site.index
    windows = dict(window_variants(text, site, offsets[k][0], 8))
    assert all(windows.values()), windows  # "none" is no longer empty


def test_a_site_inside_a_token_keeps_that_token() -> None:
    offsets = [(0, 3), (3, 7)]
    assert scoring_window_token(offsets, 5, _always_clean, 7) == 1


def test_unclean_byte_boundaries_step_back() -> None:
    offsets = [(0, 3), (3, 5), (5, 8)]
    assert scoring_window_token(offsets, 6, lambda j: j != 2, 8) == 1


def test_an_uncovered_character_is_an_error() -> None:
    with pytest.raises(RuntimeError):
        scoring_window_token([(0, 2)], 5, _always_clean, 6)


def test_a_mark_starting_its_token_mid_text_keeps_the_registered_window() -> None:
    offsets = [(0, 2), (2, 3), (3, 6)]  # a mark at 2 starts its own token, text goes on
    assert scoring_window_token(offsets, 2, _always_clean, 6) == 1
