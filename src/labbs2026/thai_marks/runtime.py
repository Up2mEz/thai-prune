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


def resolved_generation(model, kwargs: dict) -> dict:
    """The generation config `generate()` will actually use for these kwargs.

    Uses the same merge `generate()` applies (pinned transformers 5.12).
    """
    config, _ = model._prepare_generation_config(None, **kwargs)
    return config.to_dict()


def generate(model, processor, image, prompt: str, *, generation: dict, device: str) -> dict:
    """Greedy transcription; `generation` is `generation.generation_kwargs(...)`."""
    import torch

    _sync(device)
    started = time.perf_counter()
    inputs = prompt_inputs(processor, image, prompt, device)
    prepared = time.perf_counter()
    image_token = model.config.image_token_id
    visual = int((inputs["input_ids"] == image_token).sum().item())
    if str(device).startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    max_new_tokens = generation["max_new_tokens"]
    with torch.inference_mode():
        produced = model.generate(**inputs, **generation)
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


def continuation_split(encode, decode, prefix: str, continuations: dict[str, str],
                       own: list[int] | None = None
                       ) -> tuple[list[int], dict[str, list[int]]]:
    """Shared prefix tokens and each continuation's own tokens (T3).

    Byte-level BPE can merge across the join, so each `prefix + continuation`
    is tokenized whole and the split point is the longest token prefix that
    all of them share with the prefix's own tokenization and that decodes to
    a prefix of `prefix`. Every continuation is then scored from the same
    context, and only its own tokens differ. `own` may be given when the
    prefix's tokens are already fixed by a longer tokenization (T2: the prefix
    of the whole reference); the split is then also a prefix of those.
    """
    if own is None:
        own = encode(prefix)
    joint = {label: encode(prefix + text) for label, text in continuations.items()}
    k = len(own)
    for ids in joint.values():
        j = 0
        while j < min(k, len(ids)) and ids[j] == own[j]:
            j += 1
        k = j
    while k > 0 and not prefix.startswith(decode(own[:k])):
        k -= 1
    windows = {label: ids[k:] for label, ids in joint.items()}
    if any(not w for w in windows.values()):
        raise RuntimeError("a continuation has no tokens of its own; refusing to score")
    return own[:k], windows


def score_continuations(model, processor, image, prompt: str, prefix: str,
                        continuations: dict[str, str], *, device: str,
                        tolerance: float) -> dict[str, dict]:
    """Log-probabilities of alternative continuations of the model's own prefix.

    Same machinery as `score_item`: one full forward over prompt + prefix with
    explicit M-RoPE positions, then each continuation from a cropped copy of
    that cache; the first continuation is re-scored by an uncached forward and
    the call fails closed if they disagree by more than `tolerance` nats.
    """
    import torch

    tokenizer = processor.tokenizer
    shared, windows = continuation_split(
        lambda t: tokenizer(t, add_special_tokens=False)["input_ids"],
        lambda ids: tokenizer.decode(ids, clean_up_tokenization_spaces=False),
        prefix, continuations)
    out: dict[str, dict] = {}
    for condition in ("image", "no_image"):
        has_image = condition == "image"
        inputs = prompt_inputs(processor, image if has_image else None, prompt, device)
        prompt_ids = inputs["input_ids"]
        context = torch.cat([prompt_ids, torch.tensor([shared], device=prompt_ids.device,
                                                      dtype=prompt_ids.dtype)], dim=-1)
        result, positions = _full_forward(model, processor, inputs, context, has_image, 1)
        cache = result.past_key_values
        boundary = context.shape[-1] - 1
        for number, (label, targets) in enumerate(windows.items()):
            feed = torch.tensor([[int(context[0, boundary])] + targets[:-1]],
                                device=context.device, dtype=context.dtype)
            branch = copy.deepcopy(cache)
            branch.crop(boundary)
            with torch.inference_mode():
                logits = model(input_ids=feed,
                               position_ids=continuation_positions(positions, boundary,
                                                                   feed.shape[-1]),
                               past_key_values=branch, use_cache=True).logits
            logps = _window_logprobs(logits, targets)
            entry = {"logprob": sum(logps), "tokens": len(targets),
                     "token_ids": [int(t) for t in targets], "token_logprobs": logps}
            if number == 0:
                check = torch.cat([context, torch.tensor([targets], device=context.device,
                                                         dtype=context.dtype)], dim=-1)
                fresh, _ = _full_forward(model, processor, inputs, check, has_image,
                                         len(targets) + 1)
                worst = max(abs(a - b) for a, b in
                            zip(logps, _window_logprobs(fresh.logits[:, :-1, :], targets)))
                if not math.isfinite(worst) or worst > tolerance:
                    raise RuntimeError(f"cached continuation disagrees with uncached forward "
                                       f"by {worst:.4f} nats ({condition}); refusing to record")
                entry["consistency_max_abs_nats"] = worst
            out.setdefault(label, {})[condition] = entry
        del cache
    return out


def scoring_window_token(offsets: Sequence[tuple[int, int]], site_index: int,
                         clean_prefix, text_length: int) -> int:
    """Index of the reference token where a site's scoring window starts.

    Starts at the token containing the site (as registered), then (1) only
    when the site is the last character of the text and its token starts at
    the site, steps back one token — otherwise the "no mark" variant is an
    empty window whose summed log-probability of 0 beats every real variant
    (10 sites of the 2026-09-27 run) — and (2) steps back to a boundary whose
    token prefix decodes cleanly, since byte-level BPE can split a rare Thai
    character across two tokens. Every variant of the site shares the result.
    """
    k = next((i for i, (start, end) in enumerate(offsets) if start <= site_index < end), None)
    if k is None:
        raise RuntimeError(f"no token covers character {site_index}")
    if k > 0 and offsets[k][0] >= site_index and site_index == text_length - 1:
        k -= 1
    while k > 0 and not clean_prefix(k):
        k -= 1
    return k


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
            k = scoring_window_token(
                offsets, site.index,
                lambda j: tokenizer.decode(ref_ids[:j], clean_up_tokenization_spaces=False)
                == reference[: offsets[j][0]], len(reference))
            window_start = offsets[k][0]
            # Each variant is tokenized *in context* (prefix + window as one
            # string), not on its own: standalone tokenization of a window that
            # starts at a mark gives a token sequence the model never produces
            # for that text (e.g. ...ต|ั then ้ง), which drove 93% of the
            # 2026-09-28 run's wrong tone oracles. The shared prefix is then the
            # longest one every variant's canonical tokenization agrees on.
            windows = dict(window_variants(reference, site, window_start, window_after))
            shared, targets_of = continuation_split(
                lambda t: tokenizer(t, add_special_tokens=False)["input_ids"],
                lambda ids: tokenizer.decode(ids, clean_up_tokenization_spaces=False),
                reference[:window_start], windows, own=ref_ids[:k])
            boundary = prompt_len + len(shared) - 1  # re-fed token predicting the window
            for label in windows:
                targets = targets_of[label]
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
                    # Kept per token so scoring conventions (sum, mean, first
                    # divergent token) can be compared offline without a rerun.
                    "token_ids": [int(t) for t in targets],
                    "token_logprobs": token_logps,
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
