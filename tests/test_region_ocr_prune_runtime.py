"""Tensor-surgery tests for pruning, using synthetic tensors only (no weights)."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from labbs2026.region_ocr.prune_runtime import apply_keep_mask
from labbs2026.region_ocr.pruning import surviving_sequence_mask

IMAGE_TOKEN = 100295


def _fixture(seq_len: int = 8, hidden: int = 4):
    embeds = torch.arange(seq_len * hidden, dtype=torch.float32).reshape(1, seq_len, hidden)
    attn = torch.ones(1, seq_len, dtype=torch.long)
    # M-RoPE: axes on the leading dimension, sequence on the last.
    pos = torch.arange(seq_len).view(1, 1, seq_len).repeat(3, 1, 1)
    return embeds, attn, pos


def test_keep_mask_drops_positions_from_every_tensor() -> None:
    embeds, attn, pos = _fixture()
    keep = [True, True, True, False, True, False, True, True]
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=keep)
    assert out["inputs_embeds"].shape == (1, 6, 4)
    assert out["attention_mask"].shape == (1, 6)
    assert out["position_ids"].shape == (3, 1, 6)


def test_surviving_rows_keep_their_original_content() -> None:
    embeds, attn, pos = _fixture()
    keep = [True, False, True, False, True, True, True, True]
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=keep)
    expected_rows = [i for i, k in enumerate(keep) if k]
    assert torch.equal(out["inputs_embeds"][0], embeds[0][expected_rows])


def test_position_ids_are_subset_not_renumbered() -> None:
    """A survivor must keep the 3D position it had before pruning."""
    embeds, attn, pos = _fixture()
    keep = [True, False, False, True, True, False, True, True]
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=keep)
    kept = [i for i, k in enumerate(keep) if k]
    assert out["position_ids"][0, 0].tolist() == kept
    assert out["position_ids"][0, 0].tolist() != list(range(len(kept)))


def test_all_mrope_axes_are_subset_consistently() -> None:
    embeds, attn, _ = _fixture()
    pos = torch.stack([torch.arange(8), torch.arange(8) * 10, torch.arange(8) * 100]).unsqueeze(1)
    keep = [True, False, True, True, False, True, False, True]
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=keep)
    kept = [i for i, k in enumerate(keep) if k]
    assert out["position_ids"][0, 0].tolist() == kept
    assert out["position_ids"][1, 0].tolist() == [i * 10 for i in kept]
    assert out["position_ids"][2, 0].tolist() == [i * 100 for i in kept]


def test_sequence_shrinks_rather_than_being_masked() -> None:
    """The whole point: the language model must receive fewer positions."""
    embeds, attn, pos = _fixture(seq_len=10)
    keep = [True] * 4 + [False] * 4 + [True] * 2
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=keep)
    assert out["inputs_embeds"].shape[1] == 6
    assert int(out["attention_mask"].sum()) == 6


def test_optional_tensors_may_be_absent() -> None:
    embeds, _, _ = _fixture()
    out = apply_keep_mask(
        inputs_embeds=embeds, attention_mask=None, position_ids=None, keep_mask=[True] * 8
    )
    assert set(out) == {"inputs_embeds"}


def test_length_mismatches_fail_closed() -> None:
    embeds, attn, pos = _fixture()
    with pytest.raises(ValueError, match="keep_mask length"):
        apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=[True] * 7)
    with pytest.raises(ValueError, match="attention_mask length"):
        apply_keep_mask(
            inputs_embeds=embeds, attention_mask=torch.ones(1, 7), position_ids=pos, keep_mask=[True] * 8
        )
    with pytest.raises(ValueError, match="position_ids length"):
        apply_keep_mask(
            inputs_embeds=embeds,
            attention_mask=attn,
            position_ids=torch.zeros(3, 1, 7, dtype=torch.long),
            keep_mask=[True] * 8,
        )


def test_end_to_end_index_path_from_input_ids() -> None:
    """Selection indices -> sequence mask -> pruned tensors, as the runner does it."""
    input_ids = [1, 2, IMAGE_TOKEN, IMAGE_TOKEN, IMAGE_TOKEN, IMAGE_TOKEN, 3, 4]
    embeds, attn, pos = _fixture(seq_len=len(input_ids))
    keep_indices = [0, 3]
    mask = surviving_sequence_mask(input_ids, IMAGE_TOKEN, keep_indices)
    out = apply_keep_mask(inputs_embeds=embeds, attention_mask=attn, position_ids=pos, keep_mask=mask)
    surviving_ids = [t for t, k in zip(input_ids, mask) if k]
    assert surviving_ids.count(IMAGE_TOKEN) == len(keep_indices)
    assert out["inputs_embeds"].shape[1] == len(input_ids) - 2
    assert out["position_ids"][0, 0].tolist() == [0, 1, 2, 5, 6, 7]
