"""Contrastive greedy decoding: VCD (noised image) and M3ID-form (no image).

Both run two streams through the same model — the real input and a contrast
input — and pick each token from

    score = (1 + w_t) * log p(y | real) - w_t * log p(y | contrast),

restricted to tokens whose real-stream probability is at least
`beta * max p(y | real)` (VCD's adaptive plausibility constraint).

- VCD (arXiv:2311.16922): contrast = the same prompt with a noised image;
  `w_t = alpha` for every step.
- M3ID form (as this project reads it; re-check against the paper before any
  registration): contrast = the prompt with no image; `w_t` grows with the
  generated step t as `(1 - exp(-lam * t)) / exp(-lam * t)`, capped by
  `max_weight`.

Qwen3-VL keeps `rope_deltas` on the model, so two streams with different
images through `generate` would share one offset. This loop never uses it:
every forward gets explicit 4-row position ids (text position, then the three
M-RoPE axes) built the same way `generate` builds them, and `alpha = 0`
reproduces `generate`'s greedy output exactly (tested).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Weight:
    """Contrast weight per generated step (0-based)."""

    kind: str          # "constant" or "m3id"
    alpha: float = 0.0
    lam: float = 0.0
    max_weight: float = 10.0

    def __call__(self, step: int) -> float:
        if self.kind == "constant":
            return float(self.alpha)
        if self.kind == "m3id":
            decay = math.exp(-self.lam * step)
            return min(self.max_weight, (1.0 - decay) / decay)
        raise ValueError(f"unknown weight kind {self.kind!r}")


def contrastive_scores(logits_real, logits_contrast, weight: float, beta: float):
    """Scores over the vocabulary; implausible tokens are -inf.

    `beta = 0` keeps every token; `weight = 0` returns the real stream's
    log-probabilities on the plausible set, whose argmax is plain greedy.
    """
    import torch

    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must lie in [0, 1]")
    logp_real = torch.log_softmax(logits_real.float(), dim=-1)
    logp_contrast = torch.log_softmax(logits_contrast.float(), dim=-1)
    scores = (1.0 + weight) * logp_real - weight * logp_contrast
    if beta > 0:
        cutoff = logp_real.max(dim=-1, keepdim=True).values + math.log(beta)
        scores = scores.masked_fill(logp_real < cutoff, float("-inf"))
    return scores


def _prefix_positions(model, inputs: dict[str, Any]):
    """(4, 1, L) positions for a prompt, as `generate` builds them."""
    import torch

    input_ids = inputs["input_ids"]
    length = input_ids.shape[-1]
    text = torch.arange(length, device=input_ids.device).view(1, 1, -1)
    if "image_grid_thw" in inputs and inputs.get("mm_token_type_ids") is not None:
        vision, _ = model.model.get_rope_index(
            input_ids,
            image_grid_thw=inputs["image_grid_thw"],
            attention_mask=torch.ones_like(input_ids),
            mm_token_type_ids=inputs["mm_token_type_ids"],
        )
    else:
        vision = text.expand(3, 1, -1)
    return torch.cat([text, vision], dim=0)


class _Stream:
    """One prompt's KV cache and positions, advanced token by token."""

    def __init__(self, model, inputs: dict[str, Any]):
        import torch

        self.model = model
        positions = _prefix_positions(model, inputs)
        kwargs: dict[str, Any] = {
            "input_ids": inputs["input_ids"], "position_ids": positions,
            "attention_mask": torch.ones_like(inputs["input_ids"]),
            "use_cache": True, "logits_to_keep": 1,
        }
        for key in ("pixel_values", "image_grid_thw", "mm_token_type_ids"):
            if inputs.get(key) is not None:
                kwargs[key] = inputs[key]
        with torch.inference_mode():
            out = model(**kwargs)
        self.cache = out.past_key_values
        self.logits = out.logits[0, -1]
        self.length = inputs["input_ids"].shape[-1]
        self.last = positions[:, :, -1:]  # (4, 1, 1)

    def advance(self, token: int) -> None:
        import torch

        self.last = self.last + 1
        self.length += 1
        ids = torch.tensor([[token]], device=self.logits.device)
        with torch.inference_mode():
            out = self.model(
                input_ids=ids, position_ids=self.last,
                attention_mask=torch.ones((1, self.length), dtype=torch.long, device=ids.device),
                past_key_values=self.cache, use_cache=True,
            )
        self.cache = out.past_key_values
        self.logits = out.logits[0, -1]


def contrastive_greedy(model, real_inputs: dict[str, Any], contrast_inputs: dict[str, Any], *,
                       weight: Callable[[int], float], beta: float, max_new_tokens: int,
                       eos_token_ids: list[int]) -> dict:
    """Greedy decoding on contrastive scores. Returns generated ids and per-step records."""
    import torch

    if max_new_tokens < 1:
        raise ValueError("max_new_tokens must be at least 1")
    real = _Stream(model, real_inputs)
    contrast = _Stream(model, contrast_inputs)
    generated: list[int] = []
    changed_steps: list[int] = []  # steps where the remedy picked a different token than greedy
    for step in range(max_new_tokens):
        w = float(weight(step))
        scores = contrastive_scores(real.logits, contrast.logits, w, beta)
        token = int(torch.argmax(scores).item())
        if token != int(torch.argmax(real.logits).item()):
            changed_steps.append(step)
        generated.append(token)
        if token in eos_token_ids:
            break
        real.advance(token)
        contrast.advance(token)
    return {"new_token_ids": generated, "generated_tokens": len(generated),
            "reached_max_new_tokens": len(generated) >= max_new_tokens,
            "changed_steps": changed_steps}


def noised_image(image, *, step: int, total_steps: int = 1000, seed: int = 0):
    """VCD's distortion: forward diffusion q(x_t | x_0) with a linear beta schedule.

    `x_t = sqrt(abar_t) * x_0 + sqrt(1 - abar_t) * eps`, pixels scaled to [-1, 1],
    betas linear in [1e-4, 0.02] over `total_steps`. Deterministic given `seed`.
    """
    import numpy as np
    from PIL import Image

    if not 0 <= step < total_steps:
        raise ValueError("step outside the schedule")
    betas = np.linspace(1e-4, 0.02, total_steps, dtype=np.float64)
    abar = float(np.cumprod(1.0 - betas)[step])
    x0 = np.asarray(image.convert("RGB"), dtype=np.float64) / 127.5 - 1.0
    eps = np.random.default_rng(seed).standard_normal(x0.shape)
    xt = math.sqrt(abar) * x0 + math.sqrt(1.0 - abar) * eps
    pixels = np.clip((xt + 1.0) * 127.5, 0, 255).round().astype(np.uint8)
    return Image.fromarray(pixels, mode="RGB")
