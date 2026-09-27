"""Model-side code for T1 (generation) and T2 (teacher-forced variant scoring).

Qwen3-VL keeps `rope_deltas` as mutable model state and uses it to position
tokens decoded after a cached prefix. Relying on it here would be silently
wrong: a no-image prefix scored after an image item inherits that item's delta.
Every forward pass in T2 is therefore given explicit position ids, and the
cached continuation is checked against an uncached forward on every item.
"""

from __future__ import annotations

import copy
import math
import time
from typing import Any, Sequence

from labbs2026.thai_marks.orthography import Site, window_variants

TYPHOON_CARD_MAX_SIDE = 1800
TYPHOON_CARD_TRIGGER = 300


def resize_policy(image):
    """Typhoon OCR 1.5's card policy, applied to both models."""
    from PIL import Image

    width, height = image.size
    if width > TYPHOON_CARD_TRIGGER or height > TYPHOON_CARD_TRIGGER:
        scale = TYPHOON_CARD_MAX_SIDE / float(max(width, height))
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS
        )
    return image


def load(model_id: str, revision: str, dtype_name: str, device: str):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    dtype = {"float16": torch.float16, "float32": torch.float32}[dtype_name]
    processor = AutoProcessor.from_pretrained(model_id, revision=revision)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, revision=revision, dtype=dtype, attn_implementation="sdpa"
    ).to(device).eval()
    return model, processor


def prompt_inputs(processor, image, prompt: str, device: str) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    if image is not None:
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": prompt})
    inputs = processor.apply_chat_template(
        [{"role": "user", "content": content}],
        add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
    )
    return {k: (v.to(device) if hasattr(v, "to") else v) for k, v in inputs.items()}


def logits_are_finite(model, processor, image, prompt: str, device: str) -> bool:
    import torch

    inputs = prompt_inputs(processor, image, prompt, device)
    with torch.inference_mode():
        logits = model(**inputs, logits_to_keep=1).logits
    return bool(torch.isfinite(logits).all().item())


def _sync(device: str) -> None:
    import torch

    if str(device).startswith("cuda"):
        torch.cuda.synchronize(device)


def generate(model, processor, image, prompt: str, *, max_new_tokens: int, device: str) -> dict:
    import torch

    _sync(device)
    started = time.perf_counter()
    inputs = prompt_inputs(processor, image, prompt, device)
    prepared = time.perf_counter()
    image_token = model.config.image_token_id
    visual = int((inputs["input_ids"] == image_token).sum().item())
    if str(device).startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    with torch.inference_mode():
        produced = model.generate(**inputs, do_sample=False, num_beams=1,
                                  max_new_tokens=max_new_tokens)
    _sync(device)
    finished = time.perf_counter()
    new = produced[0][inputs["input_ids"].shape[-1]:]
    generated = int(new.shape[-1])
    return {
        "raw_output": processor.decode(new, skip_special_tokens=True),
        "generated_tokens": generated,
        "reached_max_new_tokens": generated >= max_new_tokens,
        "visual_tokens": visual,
        "prompt_tokens": int(inputs["input_ids"].shape[-1]),
        "seconds_processor": prepared - started,
        "seconds_generate": finished - prepared,
        "seconds_per_generated_token": (finished - prepared) / max(1, generated),
        "peak_bytes": int(torch.cuda.max_memory_allocated(device))
        if str(device).startswith("cuda") else None,
    }


# --- T2 ---------------------------------------------------------------------


def _positions(model, input_ids, inputs: dict, has_image: bool):
    """(3, 1, L) M-RoPE positions for a full sequence, computed explicitly."""
    import torch

    length = input_ids.shape[-1]
    if not has_image:
        return torch.arange(length, device=input_ids.device).view(1, 1, -1).expand(3, 1, -1)
    mm = inputs["mm_token_type_ids"]
    pad = torch.zeros((1, length - mm.shape[-1]), dtype=mm.dtype, device=mm.device)
    positions, _ = model.model.get_rope_index(
        input_ids,
        mm_token_type_ids=torch.cat([mm, pad], dim=-1),
        image_grid_thw=inputs["image_grid_thw"],
        attention_mask=torch.ones_like(input_ids),
    )
    return positions


def continuation_positions(prefix_positions, boundary: int, length: int):
    """Positions for `length` text tokens continuing from index `boundary`.

    The token at `boundary` is re-fed so that its output predicts the first
    window token; text tokens then advance by one on every M-RoPE axis.
    """
    import torch

    base = prefix_positions[:, :, boundary : boundary + 1]
    step = torch.arange(length, device=base.device).view(1, 1, -1)
    return base + step


def _window_logprobs(logits, targets) -> list[float]:
    import torch

    logp = torch.log_softmax(logits.float(), dim=-1)
    return [float(logp[0, i, t].item()) for i, t in enumerate(targets)]


def _full_forward(model, processor, prompt_ids_inputs: dict, full_ids, has_image: bool,
                  logits_to_keep: int):
    import torch

    kwargs: dict[str, Any] = {
        "input_ids": full_ids,
        "position_ids": _positions(model, full_ids, prompt_ids_inputs, has_image),
        "use_cache": True,
        "logits_to_keep": logits_to_keep,
    }
    if has_image:
        kwargs["pixel_values"] = prompt_ids_inputs["pixel_values"]
        kwargs["image_grid_thw"] = prompt_ids_inputs["image_grid_thw"]
    with torch.inference_mode():
        out = model(**kwargs)
    return out, kwargs["position_ids"]


def score_item(model, processor, image, prompt: str, reference: str,
               sites: Sequence[Site], *, device: str, tolerance: float,
               window_after: int = 8) -> list[dict]:
    """Every variant of every site, scored with and without the image.

    Fails closed if the cached continuation disagrees with an uncached forward
    on the first site of each condition.
    """
    import torch

    tokenizer = processor.tokenizer
    encoded = tokenizer(reference, add_special_tokens=False, return_offsets_mapping=True)
    ref_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]

    def token_containing(char_index: int) -> int:
        for k, (start, end) in enumerate(offsets):
            if start <= char_index < end:
                return k
        raise RuntimeError(f"no token covers character {char_index}")

    results: dict[tuple[int, str], dict] = {}
    for condition in ("image", "no_image"):
        has_image = condition == "image"
        inputs = prompt_inputs(processor, image if has_image else None, prompt, device)
        prompt_ids = inputs["input_ids"]
        full_ids = torch.cat(
            [prompt_ids, torch.tensor([ref_ids], device=prompt_ids.device, dtype=prompt_ids.dtype)],
            dim=-1,
        )
        prompt_len = prompt_ids.shape[-1]
        out, positions = _full_forward(model, processor, inputs, full_ids, has_image, 1)
        cache = out.past_key_values

        for site_number, site in enumerate(sites):
            k = token_containing(site.index)
            # Byte-level BPE can split a rare Thai character across two tokens;
            # step back to the nearest boundary that decodes cleanly. Every
            # variant of the site shares that boundary, so fairness is kept.
            while k > 0 and tokenizer.decode(
                ref_ids[:k], clean_up_tokenization_spaces=False
            ) != reference[: offsets[k][0]]:
                k -= 1
            window_start = offsets[k][0]
            boundary = prompt_len + k - 1  # re-fed token, whose output predicts the window
            for label, window in window_variants(reference, site, window_start, window_after):
                targets = tokenizer(window, add_special_tokens=False)["input_ids"]
                feed = torch.tensor([[int(full_ids[0, boundary])] + targets[:-1]],
                                    device=full_ids.device, dtype=full_ids.dtype)
                branch = copy.deepcopy(cache)
                branch.crop(boundary)
                with torch.inference_mode():
                    logits = model(
                        input_ids=feed,
                        position_ids=continuation_positions(positions, boundary, feed.shape[-1]),
                        past_key_values=branch,
                        use_cache=True,
                    ).logits
                token_logps = _window_logprobs(logits, targets)
                entry = results.setdefault((site.index, site.kind), {
                    "kind": site.kind, "index": site.index, "reference": site.reference,
                    "variants": {},
                })
                entry["variants"].setdefault(label, {})[condition] = {
                    "logprob": sum(token_logps), "tokens": len(targets),
                }

                if site_number == 0 and label == site.reference:
                    check_ids = torch.cat(
                        [full_ids[:, : boundary + 1],
                         torch.tensor([targets], device=full_ids.device, dtype=full_ids.dtype)],
                        dim=-1,
                    )
                    fresh, _ = _full_forward(model, processor, inputs, check_ids, has_image,
                                             len(targets) + 1)
                    fresh_logps = _window_logprobs(fresh.logits[:, :-1, :], targets)
                    worst = max(abs(a - b) for a, b in zip(token_logps, fresh_logps))
                    if not math.isfinite(worst) or worst > tolerance:
                        raise RuntimeError(
                            f"cached continuation disagrees with uncached forward by {worst:.4f} "
                            f"nats ({condition}); refusing to record scores"
                        )
                    entry.setdefault("consistency_max_abs_nats", {})[condition] = worst
        del cache
        if str(device).startswith("cuda"):
            torch.cuda.empty_cache()
    return list(results.values())
