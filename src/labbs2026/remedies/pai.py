"""PAI-style attention amplification toward image tokens (arXiv:2407.21771).

As this project reads PAI (re-check against the paper before any
registration): in the chosen language-model layers, the pre-softmax attention
score of every query toward an image-token key is raised by `alpha * |score|`,
countering "text inertia"; by default only decode-step queries are touched, so
the prompt's own representation is unchanged. PAI's second component — refining
logits against a text-only pass — is the contrastive form already in
`labbs2026.remedies.contrastive` and is not repeated here.

Implemented as a registered attention function that is the eager computation
plus that one change, swapped in for the text model only while the context is
active. `alpha = 0` is exactly eager attention (tested).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable

NAME = "labbs_pai"


@dataclass
class _State:
    image_keys: Any = None       # 1-D LongTensor of key positions holding image tokens
    layers: frozenset = frozenset()
    alpha: float = 0.0
    decode_only: bool = True


_STATE: _State | None = None


def amplify(scores, image_keys, alpha: float):
    """`scores + alpha * |scores|` on the image-key columns; other columns untouched."""
    if alpha == 0 or image_keys is None or image_keys.numel() == 0:
        return scores
    keys = image_keys[image_keys < scores.shape[-1]]
    out = scores.clone()
    out[..., keys] = scores[..., keys] + alpha * scores[..., keys].abs()
    return out


def _pai_attention(module, query, key, value, attention_mask, scaling: float, dropout: float = 0.0,
                   **kwargs):
    import torch
    from torch import nn
    from transformers.models.qwen3_vl.modeling_qwen3_vl import repeat_kv

    key_states = repeat_kv(key, module.num_key_value_groups)
    value_states = repeat_kv(value, module.num_key_value_groups)
    scores = torch.matmul(query, key_states.transpose(2, 3)) * scaling
    state = _STATE
    if (state is not None and module.layer_idx in state.layers
            and (not state.decode_only or query.shape[-2] == 1)):
        scores = amplify(scores, state.image_keys.to(scores.device), state.alpha)
    if attention_mask is not None:
        scores = scores + attention_mask
    weights = nn.functional.softmax(scores, dim=-1, dtype=torch.float32).to(query.dtype)
    weights = nn.functional.dropout(weights, p=dropout, training=module.training)
    output = torch.matmul(weights, value_states).transpose(1, 2).contiguous()
    return output, weights


def _register() -> None:
    """Register the attention function and, with it, eager's additive causal mask.

    Without the mask registration `create_causal_mask` returns no mask for an
    unknown implementation name and prefill would attend bidirectionally.
    """
    from transformers import AttentionInterface
    from transformers.masking_utils import ALL_MASK_ATTENTION_FUNCTIONS, eager_mask

    AttentionInterface.register(NAME, _pai_attention)
    ALL_MASK_ATTENTION_FUNCTIONS.register(NAME, eager_mask)


@contextmanager
def amplified_image_attention(model, input_ids, *, image_token_id: int, layers: Iterable[int],
                              alpha: float, decode_only: bool = True):
    """Within the context, the text model attends with PAI amplification.

    `input_ids` is the prompt; its image-token positions are the image keys,
    which stay valid as generated tokens are appended after them.
    """
    global _STATE
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    n_layers = len(model.model.language_model.layers)
    layers = frozenset(int(l) for l in layers)
    if any(not 0 <= l < n_layers for l in layers):
        raise ValueError(f"layers must lie in [0, {n_layers})")
    _register()
    text_config = model.model.language_model.config
    previous = text_config._attn_implementation
    _STATE = _State((input_ids[0] == image_token_id).nonzero().flatten(), layers, float(alpha),
                    decode_only)
    text_config._attn_implementation = NAME
    try:
        yield
    finally:
        text_config._attn_implementation = previous
        _STATE = None
