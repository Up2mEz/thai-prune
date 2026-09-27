"""Model-side code for SPEC_DECODE_S1: one `generate` per arm, and the REF margin.

Loading, the image policy and prompt construction are T1's
(`labbs2026.thai_marks.runtime`), imported unchanged so S1's `REF` arm repeats
T1's `TYPHOON_CARD` condition.

Qwen3-VL caches `rope_deltas` on the model. Every `generate` here starts from an
empty cache, which recomputes it from the item's own image grid, and the margin
forward passes explicit multimodal token types over the full sequence, so no
call inherits another's offset.
"""

from __future__ import annotations

import math
import time
from typing import Any

from labbs2026.spec_decode.design import top2_margin


def _sync(device: str) -> None:
    import torch

    if str(device).startswith("cuda"):
        torch.cuda.synchronize(device)


def _language_model(model):
    return model.model.language_model


def run_arm(model, inputs: dict[str, Any], arm_kwargs: dict[str, Any], *,
            max_new_tokens: int, device: str) -> dict:
    """Greedy `generate` with the arm's extra arguments, timed and forward-counted."""
    import torch

    forwards = [0]

    def count(*_):
        forwards[0] += 1

    hook = _language_model(model).register_forward_hook(count)
    try:
        if str(device).startswith("cuda"):
            torch.cuda.reset_peak_memory_stats(device)
        _sync(device)
        started = time.perf_counter()
        with torch.inference_mode():
            produced = model.generate(**inputs, do_sample=False, num_beams=1,
                                      max_new_tokens=max_new_tokens, **arm_kwargs)
        _sync(device)
        seconds = time.perf_counter() - started
    finally:
        hook.remove()
    prompt_length = int(inputs["input_ids"].shape[-1])
    new_ids = [int(t) for t in produced[0][prompt_length:].tolist()]
    return {
        "new_token_ids": new_ids,
        "generated_tokens": len(new_ids),
        "reached_max_new_tokens": len(new_ids) >= max_new_tokens,
        "prompt_tokens": prompt_length,
        "seconds_generate": seconds,
        "target_forwards": forwards[0],
        "peak_bytes": int(torch.cuda.max_memory_allocated(device))
        if str(device).startswith("cuda") else None,
    }


def seconds_to_first_token(model, inputs: dict[str, Any], *, device: str) -> float:
    """Wall-clock of a `max_new_tokens=1` greedy call: prefill plus one step."""
    import torch

    _sync(device)
    started = time.perf_counter()
    with torch.inference_mode():
        model.generate(**inputs, do_sample=False, num_beams=1, max_new_tokens=1)
    _sync(device)
    return time.perf_counter() - started


def ref_margin_at(model, inputs: dict[str, Any], ref_new_ids: list[int], position: int) -> dict:
    """REF's top-1 minus top-2 logit where generated token `position` is chosen.

    One teacher-forced forward over prompt + REF's first `position` tokens.
    Fails closed on non-finite logits or on a fed length that is not
    prompt + `position` (registration §7).
    """
    import torch

    if not 0 <= position < len(ref_new_ids):
        raise ValueError("position outside REF's output")
    prompt_ids = inputs["input_ids"]
    prefix = torch.tensor([ref_new_ids[:position]], device=prompt_ids.device, dtype=prompt_ids.dtype)
    full_ids = torch.cat([prompt_ids, prefix], dim=-1)
    if full_ids.shape[-1] != prompt_ids.shape[-1] + position:
        raise RuntimeError("margin forward length does not match REF's prefix; refusing to record")
    kwargs: dict[str, Any] = {"input_ids": full_ids, "attention_mask": torch.ones_like(full_ids),
                              "use_cache": False, "logits_to_keep": 1}
    for key in ("pixel_values", "image_grid_thw"):
        if key in inputs:
            kwargs[key] = inputs[key]
    if "mm_token_type_ids" in inputs:
        mm = inputs["mm_token_type_ids"]
        pad = torch.zeros((1, position), dtype=mm.dtype, device=mm.device)
        kwargs["mm_token_type_ids"] = torch.cat([mm, pad], dim=-1)
    with torch.inference_mode():
        logits = model(**kwargs).logits[0, -1]
    if not bool(torch.isfinite(logits).all().item()):
        raise RuntimeError("non-finite logits in margin forward; refusing to record")
    margin = top2_margin(logits)
    if not math.isfinite(margin):
        raise RuntimeError("non-finite margin; refusing to record")
    return {
        "margin_logits": margin,
        "teacher_forced_argmax": int(torch.argmax(logits).item()),
        "ref_token": int(ref_new_ids[position]),
    }
