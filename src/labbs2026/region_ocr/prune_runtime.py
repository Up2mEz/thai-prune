"""Tensor surgery that turns a selection of surviving tokens into a model call.

The model's forward accepts `inputs_embeds` and `position_ids` directly, and
skips the vision path entirely when `pixel_values` is omitted. That is what
makes correct pruning possible:

- visual features are computed once from the unpruned image and scattered into
  the embedding sequence, so the encoder still sees the whole image — the whole
  point of *post*-encoder pruning;
- M-RoPE positions are computed once for the unpruned layout and then subset,
  so every surviving token keeps the 3D position it originally had. Letting the
  model recompute them from `image_grid_thw` after pruning would hand a K-token
  sequence positions generated for N tokens;
- the unselected image positions are removed from the sequence rather than
  masked, so the language model genuinely receives fewer positions.

The pure tensor work is separated from anything that needs weights so it can be
tested without loading a model.
"""

from __future__ import annotations

from typing import Any, Sequence


def apply_keep_mask(
    *,
    inputs_embeds: Any,
    attention_mask: Any,
    position_ids: Any | None,
    keep_mask: Sequence[bool],
) -> dict[str, Any]:
    """Drop non-surviving sequence positions from every aligned tensor.

    `position_ids` carries the M-RoPE axes in its leading dimension, so it is
    indexed on its last axis rather than its first.
    """
    import torch

    mask = torch.as_tensor(list(keep_mask), dtype=torch.bool, device=inputs_embeds.device)
    if mask.numel() != inputs_embeds.shape[1]:
        raise ValueError(
            f"keep_mask length {mask.numel()} != sequence length {inputs_embeds.shape[1]}"
        )
    if attention_mask is not None and attention_mask.shape[-1] != mask.numel():
        raise ValueError("attention_mask length does not match the sequence")

    pruned: dict[str, Any] = {"inputs_embeds": inputs_embeds[:, mask, :]}
    if attention_mask is not None:
        pruned["attention_mask"] = attention_mask[..., mask]
    if position_ids is not None:
        if position_ids.shape[-1] != mask.numel():
            raise ValueError("position_ids length does not match the sequence")
        pruned["position_ids"] = position_ids[..., mask]
    return pruned


def embed_with_visual_features(model: Any, input_ids: Any, image_features: Any) -> Any:
    """Text embeddings with the projector's visual features scattered in.

    Mirrors the model's own forward so the pruned path and the unpruned path
    differ only by which positions survive.
    """
    inner = model.model if hasattr(model, "model") else model
    inputs_embeds = inner.language_model.embed_tokens(input_ids)
    features = image_features.to(inputs_embeds.device, inputs_embeds.dtype)
    image_mask = inner.get_placeholder_mask(
        input_ids, inputs_embeds=inputs_embeds, image_features=features
    )
    return inputs_embeds.masked_scatter(image_mask, features)


def full_visual_features(model: Any, pixel_values: Any, image_grid_thw: Any) -> Any:
    """Projector output for the unpruned image: the N features pruning selects from."""
    inner = model.model if hasattr(model, "model") else model
    return inner.get_image_features(pixel_values, image_grid_thw, return_dict=True).pooler_output


def full_position_ids(
    model: Any,
    *,
    input_ids: Any,
    image_grid_thw: Any,
    inputs_embeds: Any,
    attention_mask: Any,
    mm_token_type_ids: Any,
) -> Any:
    """M-RoPE positions for the unpruned layout, to be subset afterwards."""
    inner = model.model if hasattr(model, "model") else model
    return inner.compute_3d_position_ids(
        input_ids=input_ids,
        image_grid_thw=image_grid_thw,
        inputs_embeds=inputs_embeds,
        attention_mask=attention_mask,
        past_key_values=None,
        mm_token_type_ids=mm_token_type_ids,
    )
