"""Tests for post-encoder visual-token selection and sequence surgery."""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.pruning import (
    assert_accounting,
    image_token_positions,
    resolve_budget,
    select_grid_indices,
    select_keep_indices,
    select_random_indices,
    surviving_sequence_mask,
)

IMAGE_TOKEN = 100295


def _sequence(image_tokens: int) -> list[int]:
    return [1, 2, *([IMAGE_TOKEN] * image_tokens), 3, 4]


def test_resolve_budget_bounds() -> None:
    assert resolve_budget(10, 10) == 10
    for total, kept in ((10, 0), (10, 11), (0, 1)):
        with pytest.raises(ValueError):
            resolve_budget(total, kept)


def test_random_selection_is_deterministic_and_sized() -> None:
    first = select_random_indices(160, 40, seed=7)
    assert first == select_random_indices(160, 40, seed=7)
    assert len(first) == 40
    assert len(set(first)) == 40
    assert list(first) == sorted(first)
    assert max(first) < 160


def test_random_seeds_differ() -> None:
    assert select_random_indices(160, 40, seed=1) != select_random_indices(160, 40, seed=2)


@pytest.mark.parametrize(
    ("rows", "cols", "kept"),
    [(10, 16, 120), (10, 16, 80), (10, 16, 40), (12, 14, 126), (8, 20, 40), (4, 4, 1), (5, 7, 35)],
)
def test_grid_selection_returns_exactly_the_budget(rows: int, cols: int, kept: int) -> None:
    chosen = select_grid_indices(rows, cols, kept)
    assert len(chosen) == kept
    assert len(set(chosen)) == kept
    assert list(chosen) == sorted(chosen)
    assert max(chosen) < rows * cols


def test_grid_selection_spreads_across_both_axes() -> None:
    """Striding the flattened sequence would drop whole rows; this must not."""
    rows, cols = 10, 16
    chosen = select_grid_indices(rows, cols, 40)
    touched_rows = {index // cols for index in chosen}
    touched_cols = {index % cols for index in chosen}
    assert len(touched_rows) > 1
    assert len(touched_cols) > 1
    # A row-striding bug would touch every column of a few rows only.
    assert len(touched_rows) >= 4


def test_grid_selection_is_deterministic() -> None:
    assert select_grid_indices(10, 16, 80) == select_grid_indices(10, 16, 80)


def test_grid_full_budget_keeps_everything() -> None:
    assert select_grid_indices(4, 5, 20) == tuple(range(20))


def test_select_keep_indices_dispatch() -> None:
    assert len(select_keep_indices(policy="GRID", rows=10, cols=16, kept=40)) == 40
    assert len(select_keep_indices(policy="RANDOM", rows=10, cols=16, kept=40, seed=3)) == 40
    with pytest.raises(ValueError, match="requires a seed"):
        select_keep_indices(policy="RANDOM", rows=10, cols=16, kept=40)
    with pytest.raises(ValueError, match="unknown policy"):
        select_keep_indices(policy="NOPE", rows=4, cols=4, kept=2)  # type: ignore[arg-type]


def test_image_token_positions() -> None:
    assert image_token_positions(_sequence(3), IMAGE_TOKEN) == (2, 3, 4)
    assert image_token_positions([1, 2, 3], IMAGE_TOKEN) == ()


def test_surviving_mask_drops_only_unselected_image_tokens() -> None:
    sequence = _sequence(4)  # positions 2,3,4,5 are image tokens
    mask = surviving_sequence_mask(sequence, IMAGE_TOKEN, [0, 2])
    assert mask == (True, True, True, False, True, False, True, True)
    assert sum(mask) == len(sequence) - 2


def test_surviving_mask_keeps_all_non_image_positions() -> None:
    sequence = _sequence(6)
    mask = surviving_sequence_mask(sequence, IMAGE_TOKEN, [1])
    survivors = [token for token, keep in zip(sequence, mask) if keep]
    assert survivors.count(IMAGE_TOKEN) == 1
    assert [t for t in survivors if t != IMAGE_TOKEN] == [1, 2, 3, 4]


def test_surviving_mask_rejects_out_of_range_indices() -> None:
    with pytest.raises(ValueError, match="out of range"):
        surviving_sequence_mask(_sequence(3), IMAGE_TOKEN, [0, 5])


def test_accounting_accepts_a_consistent_call() -> None:
    assert_accounting(pre_prune=160, post_prune=40, llm_positions=40, expected_kept=40) is None


def test_accounting_rejects_masking_instead_of_removal() -> None:
    """Zeroing tokens leaves the sequence length unchanged; that must fail."""
    with pytest.raises(RuntimeError, match="LLM image positions"):
        assert_accounting(pre_prune=160, post_prune=40, llm_positions=160, expected_kept=40)


def test_accounting_rejects_feature_count_mismatch() -> None:
    with pytest.raises(RuntimeError, match="post-prune features"):
        assert_accounting(pre_prune=160, post_prune=39, llm_positions=40, expected_kept=40)


def test_accounting_rejects_growth() -> None:
    with pytest.raises(RuntimeError, match="exceeds pre-prune"):
        assert_accounting(pre_prune=40, post_prune=80, llm_positions=80, expected_kept=80)
