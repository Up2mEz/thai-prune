"""Execution of one region-OCR observation against the pinned model.

Every observation passes through the same generation call; only how the visual
evidence reaches the language model differs:

  FULL   - processor defaults, standard path.
  RR     - processor forced to a lower pixel budget, standard path.
  PRUNE  - processor defaults, then post-encoder token removal.

Accounting is asserted per call rather than summarised afterwards, because a
silent mismatch between the registered budget and what the model actually
received would invalidate the contrast without producing any visible error.
"""

from __future__ import annotations

import time
from typing import Any

from labbs2026.region_ocr.prune_runtime import (
    apply_keep_mask,
    embed_with_visual_features,
    full_position_ids,
    full_visual_features,
)
from labbs2026.region_ocr.pruning import (
    assert_accounting,
    select_keep_indices,
    surviving_sequence_mask,
)
from labbs2026.region_ocr.workload import FAMILY_FULL, FAMILY_PRUNE, FAMILY_RR

PROMPT = "OCR:"


def _processor_inputs(processor, image, forced_pixels: int | None):
    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}
    ]
    kwargs: dict[str, Any] = dict(
        add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
    )
    if forced_pixels is not None:
        # Resolution Reduction pins the processor to one exact pixel budget. The
        # native class takes that as a SizeDict; older remote-code processors took
        # min_pixels/max_pixels. Both are sent so either implementation honours it,
        # and the placeholder count is asserted afterwards regardless.
        pixels = int(forced_pixels)
        kwargs["processor_kwargs"] = {
            "size": {"shortest_edge": pixels, "longest_edge": pixels},
            "min_pixels": pixels,
            "max_pixels": pixels,
        }
    return processor.apply_chat_template(messages, **kwargs)


def _assert_same_device(model, tensors: dict[str, Any]) -> None:
    """Every tensor handed to the model must sit on the model's device.

    A mismatch raises deep inside a convolution with an opaque message, and only
    under GPU, so it is checked explicitly here instead.
    """
    import torch

    target = next(model.parameters()).device
    wrong = {
        name: str(value.device)
        for name, value in tensors.items()
        if isinstance(value, torch.Tensor) and value.device != target
    }
    if wrong:
        raise RuntimeError(f"tensors not on {target}: {wrong}")


def _accounting(inputs, model) -> dict[str, Any]:
    grid = [int(v) for v in inputs["image_grid_thw"][0].tolist()]
    merge = int(model.config.vision_config.spatial_merge_size)
    from_grid = grid[0] * (grid[1] // merge) * (grid[2] // merge)
    placeholders = int((inputs["input_ids"] == int(model.config.image_token_id)).sum().item())
    if from_grid != placeholders:
        raise RuntimeError(f"grid-derived {from_grid} != placeholders {placeholders}")
    return {
        "image_grid_thw": grid,
        "pre_merge": grid[0] * grid[1] * grid[2],
        "placeholders": placeholders,
        "token_rows": grid[1] // merge,
        "token_cols": grid[2] // merge,
    }


def execute_observation(model, processor, image, observation: dict[str, Any],
                        *, max_new_tokens: int, device: str) -> dict[str, Any]:
    """Run one observation and return its record, failing closed on any mismatch."""
    import torch

    family = observation["family"]
    expected = int(observation["expected_placeholders"])
    inputs = _processor_inputs(
        processor, image, observation["forced_pixels"] if family == FAMILY_RR else None
    )
    accounting = _accounting(inputs, model)
    prompt_len = int(inputs["input_ids"].shape[-1])

    # Move every processor tensor to the model's device before any of them touch
    # the model. The pruning path runs the vision tower itself rather than letting
    # generate() do it, so leaving these on CPU fails only under GPU - which a
    # CPU-only smoke cannot surface.
    inputs = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    _assert_same_device(model, inputs)

    started = time.perf_counter()
    if family in (FAMILY_FULL, FAMILY_RR):
        if accounting["placeholders"] != expected:
            raise RuntimeError(
                f"{observation['condition_id']}: placeholders {accounting['placeholders']} "
                f"!= registered {expected}"
            )
        with torch.inference_mode():
            produced = model.generate(**inputs, do_sample=False, num_beams=1,
                                      max_new_tokens=max_new_tokens)
        new_tokens = produced[0][prompt_len:]
        llm_positions = accounting["placeholders"]
        pre_prune = accounting["placeholders"]
    elif family == FAMILY_PRUNE:
        native = accounting["placeholders"]
        if expected > native:
            raise RuntimeError(
                f"{observation['condition_id']}: cannot keep {expected} of {native}"
            )
        keep = select_keep_indices(
            policy=observation["policy"], rows=accounting["token_rows"],
            cols=accounting["token_cols"], kept=expected, seed=observation["seed"],
        )
        with torch.inference_mode():
            features = full_visual_features(model, inputs["pixel_values"], inputs["image_grid_thw"])
            embeds = embed_with_visual_features(model, inputs["input_ids"], features)
            positions = full_position_ids(
                model, input_ids=inputs["input_ids"], image_grid_thw=inputs["image_grid_thw"],
                inputs_embeds=embeds, attention_mask=inputs.get("attention_mask"),
                mm_token_type_ids=inputs.get("mm_token_type_ids"),
            )
        mask = surviving_sequence_mask(
            inputs["input_ids"][0].tolist(), int(model.config.image_token_id), keep
        )
        pruned = apply_keep_mask(
            inputs_embeds=embeds, attention_mask=inputs.get("attention_mask"),
            position_ids=positions, keep_mask=mask,
        )
        expected_len = prompt_len - (native - expected)
        if int(pruned["inputs_embeds"].shape[1]) != expected_len:
            raise RuntimeError(
                f"{observation['condition_id']}: pruned length "
                f"{int(pruned['inputs_embeds'].shape[1])} != expected {expected_len}"
            )
        assert_accounting(pre_prune=native, post_prune=expected,
                          llm_positions=expected, expected_kept=expected)
        _assert_same_device(model, pruned)
        with torch.inference_mode():
            produced = model.generate(**pruned, do_sample=False, num_beams=1,
                                      max_new_tokens=max_new_tokens)
        # With inputs_embeds the prompt is not echoed: everything returned is new.
        new_tokens = produced[0]
        llm_positions = expected
        pre_prune = native
    else:
        raise ValueError(f"unknown family: {family!r}")
    latency = time.perf_counter() - started

    raw = processor.decode(new_tokens, skip_special_tokens=True)
    return {
        **{k: observation[k] for k in
           ("image_id", "source_photo_id", "reference", "condition_id",
            "family", "policy", "seed", "nominal_ratio", "target_placeholders",
            "expected_placeholders")},
        "raw_output": raw,
        "parsed_output": raw.strip(),
        "generated_tokens": int(new_tokens.shape[-1]),
        "reached_max_new_tokens": int(new_tokens.shape[-1]) >= max_new_tokens,
        "latency_seconds": latency,
        "pre_prune_placeholders": pre_prune,
        "llm_visual_positions": llm_positions,
        "prompt_length": prompt_len,
        **{f"native_{k}": v for k, v in accounting.items()},
    }
