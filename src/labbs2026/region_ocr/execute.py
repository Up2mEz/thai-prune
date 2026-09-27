"""Execution of one region-OCR observation against the pinned model.

Every observation walks the *same* call graph. That is a change from the first
run, and it is the change that makes efficiency numbers meaningful at all:
previously `FULL`/`RR` handed `pixel_values` to `generate()` and let it run the
vision tower internally, while pruning ran the tower itself and passed
`inputs_embeds`. Those two routes differ in more than the intervention, so their
wall times were never a comparison of anything. Now all families run the vision
tower explicitly, build embeddings and M-RoPE positions explicitly, and call
`generate(inputs_embeds=...)`; the families differ only in what happens to the
visual features and positions in between.

  FULL   - processor defaults, identity selection.
  RR     - processor forced to a lower pixel budget, identity selection.
  PRUNE  - processor defaults, then post-encoder token removal.
  MERGE  - processor defaults, cells averaged onto the pruned survivors.
  RESTORED - region re-rendered at a coarser grid and back to FULL's, so a
           condition can carry reduced detail at FULL's token count.
  SWEEP  - processor forced above or below FULL's budget, identity selection.

Because that rerouting could in principle change what the model emits, it is not
assumed safe: `assert_path_equivalence` runs both routes on one image and
requires identical greedy output before any scientific run.

Accounting is asserted per call rather than summarised afterwards, because a
silent mismatch between the registered budget and what the model actually
received would invalidate the contrast without producing any visible error.
"""

from __future__ import annotations

from typing import Any

from labbs2026.region_ocr.cost import CostMeter, analytic_compute
from labbs2026.region_ocr.merge_runtime import merge_features, token_ink_scores
from labbs2026.region_ocr.prune_runtime import (
    apply_keep_mask,
    embed_with_visual_features,
    full_position_ids,
    full_visual_features,
)
from labbs2026.region_ocr.pruning import (
    assert_accounting,
    assign_to_representatives,
    select_keep_indices,
    surviving_sequence_mask,
)
from labbs2026.region_ocr.workload import (
    FAMILY_MERGE,
    FAMILY_PRUNE,
    IDENTITY_FAMILIES,
)

PROMPT = "OCR:"


def _resample_filter(processor) -> int:
    """The processor's own resampling filter, so a pre-resize matches its resize.

    Emulating the processor's downscale with a different filter would make the
    restored arm carry a different bottleneck from the Resolution Reduction arm
    it is supposed to match, which is the one thing that arm exists to control.
    """
    return int(getattr(getattr(processor, "image_processor", processor), "resample", 3))


def _apply_pre_resize(image, pre_resize: dict | None, resample: int):
    """Render the region at a coarser grid, then restore it to FULL's grid.

    The crops here sit far below the processor's pixel floor, so every condition
    is an upsample of the source and none of them loses source information. That
    makes Resolution Reduction and post-encoder pruning differ in magnification
    as well as in where tokens are removed, and the two cannot be told apart.

    This round trip breaks that tie: the image comes back at FULL's dimensions,
    and therefore FULL's token count and magnification, while carrying only the
    detail the coarser grid could hold.
    """
    if pre_resize is None:
        return image, None
    down_h, down_w = pre_resize["down"]
    up_h, up_w = pre_resize["up"]
    coarse = image.resize((int(down_w), int(down_h)), resample)
    restored = coarse.resize((int(up_w), int(up_h)), resample)
    return restored, {
        "pre_resize_down": [int(down_h), int(down_w)],
        "pre_resize_up": [int(up_h), int(up_w)],
        "pre_resize_resample": resample,
    }


def _processor_inputs(processor, image, forced_pixels: int | None):
    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}
    ]
    kwargs: dict[str, Any] = dict(
        add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
    )
    if forced_pixels is not None:
        # Any condition that names a pixel budget pins the processor to it: the
        # reduction arms, the restored arms that pin it back to FULL's grid, and
        # the magnification sweep that pushes past FULL. The
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


def _accounting(inputs, model, source_size) -> dict[str, Any]:
    grid = [int(v) for v in inputs["image_grid_thw"][0].tolist()]
    merge = int(model.config.vision_config.spatial_merge_size)
    patch = int(model.config.vision_config.patch_size)
    from_grid = grid[0] * (grid[1] // merge) * (grid[2] // merge)
    placeholders = int((inputs["input_ids"] == int(model.config.image_token_id)).sum().item())
    if from_grid != placeholders:
        raise RuntimeError(f"grid-derived {from_grid} != placeholders {placeholders}")

    # Geometry on both sides of the processor. Without this, the finding that a
    # reduced budget beats FULL cannot be separated from the processor having
    # upsampled a small crop before the encoder ever saw it: an intervention that
    # removes an interpolation artefact is not an intervention that shows
    # compression helps.
    # Deliberately the *original* region, not whatever was handed to the
    # processor: a restored arm arrives pre-enlarged, and measuring its scale
    # against that enlargement would report 1.0 and hide the very magnification
    # this record exists to expose.
    source_width, source_height = source_size
    processed_height, processed_width = grid[1] * patch, grid[2] * patch
    source_pixels = max(1, int(source_height) * int(source_width))
    processed_pixels = processed_height * processed_width
    return {
        "image_grid_thw": grid,
        "pre_merge": grid[0] * grid[1] * grid[2],
        "placeholders": placeholders,
        "token_rows": grid[1] // merge,
        "token_cols": grid[2] // merge,
        "patch_size": patch,
        "spatial_merge_size": merge,
        "source_height": int(source_height),
        "source_width": int(source_width),
        "processed_height": processed_height,
        "processed_width": processed_width,
        "processor_scale": processed_pixels / source_pixels,
        "processor_upsampled": processed_pixels > source_pixels,
    }


def _visual_features_for(model, inputs, accounting, observation, meter):
    """Projector features aligned to the placeholders, plus the survivors.

    Returns a full-length (N, D) tensor in every case. Merging writes each
    cell's mean into all of that cell's rows, so the survivors carry the merged
    vector and the downstream sequence surgery is identical for every family.
    """
    import torch

    family = observation["family"]
    native = accounting["placeholders"]
    expected = int(observation["expected_placeholders"])

    with meter.stage("vision"), torch.inference_mode():
        features = full_visual_features(
            model, inputs["pixel_values"], inputs["image_grid_thw"]
        )
    if int(features.shape[0]) != native:
        raise RuntimeError(f"projector emitted {int(features.shape[0])} != {native} features")

    if family in IDENTITY_FAMILIES:
        with meter.stage("select"):
            keep = tuple(range(native))
        return features, keep

    if expected > native:
        raise RuntimeError(f"{observation['condition_id']}: cannot keep {expected} of {native}")

    with meter.stage("select"):
        scores = None
        if observation["policy"] == "COVERAGE":
            scores = token_ink_scores(
                inputs["pixel_values"], tokens=native,
                merge=accounting["spatial_merge_size"],
            )
        keep = select_keep_indices(
            policy=observation["policy"], rows=accounting["token_rows"],
            cols=accounting["token_cols"], kept=expected, seed=observation["seed"],
            scores=scores,
        )
        if family == FAMILY_MERGE:
            assignment = assign_to_representatives(
                accounting["token_rows"], accounting["token_cols"], keep
            )
            merged = merge_features(features, assignment, expected)
            features = merged[torch.as_tensor(list(assignment), device=merged.device)]
    return features, keep


def execute_observation(model, processor, image, observation: dict[str, Any],
                        *, max_new_tokens: int, device: str) -> dict[str, Any]:
    """Run one observation and return its record, failing closed on any mismatch."""
    import torch

    family = observation["family"]
    expected = int(observation["expected_placeholders"])
    meter = CostMeter(device)

    source_size = image.size
    with meter.stage("processor"):
        image, resize_record = _apply_pre_resize(
            image, observation.get("pre_resize"), _resample_filter(processor)
        )
        inputs = _processor_inputs(processor, image, observation["forced_pixels"])
    accounting = _accounting(inputs, model, source_size)
    prompt_len = int(inputs["input_ids"].shape[-1])
    native = accounting["placeholders"]

    if family in IDENTITY_FAMILIES and native != expected:
        raise RuntimeError(
            f"{observation['condition_id']}: placeholders {native} != registered {expected}"
        )

    # Move every processor tensor to the model's device before any of them touch
    # the model. The vision tower is run explicitly here rather than inside
    # generate(), so leaving these on CPU fails only under GPU - which a
    # CPU-only smoke cannot surface.
    inputs = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    _assert_same_device(model, inputs)

    features, keep = _visual_features_for(model, inputs, accounting, observation, meter)

    with meter.stage("embed"), torch.inference_mode():
        embeds = embed_with_visual_features(model, inputs["input_ids"], features)
        positions = full_position_ids(
            model, input_ids=inputs["input_ids"], image_grid_thw=inputs["image_grid_thw"],
            inputs_embeds=embeds, attention_mask=inputs.get("attention_mask"),
            mm_token_type_ids=inputs.get("mm_token_type_ids"),
        )

    mask = surviving_sequence_mask(
        inputs["input_ids"][0].tolist(), int(model.config.image_token_id), keep
    )
    staged = apply_keep_mask(
        inputs_embeds=embeds, attention_mask=inputs.get("attention_mask"),
        position_ids=positions, keep_mask=mask,
    )
    kept_visual = len(keep)
    expected_len = prompt_len - (native - kept_visual)
    if int(staged["inputs_embeds"].shape[1]) != expected_len:
        raise RuntimeError(
            f"{observation['condition_id']}: staged length "
            f"{int(staged['inputs_embeds'].shape[1])} != expected {expected_len}"
        )
    assert_accounting(pre_prune=native, post_prune=kept_visual,
                      llm_positions=kept_visual, expected_kept=expected)
    _assert_same_device(model, staged)

    # Prefill is timed on its own pass because it is the only part of generation
    # that scales with sequence length, and therefore the only part a
    # post-encoder intervention can shorten. Decode scales with how many tokens
    # the model chose to emit, which is an outcome of the intervention rather
    # than a cost of it, so folding the two together would let a condition look
    # cheap merely by giving up early.
    with meter.stage("prefill"), torch.inference_mode():
        model(inputs_embeds=staged["inputs_embeds"],
              attention_mask=staged.get("attention_mask"),
              position_ids=staged.get("position_ids"), use_cache=True)

    with meter.stage("generate"), torch.inference_mode():
        produced = model.generate(**staged, do_sample=False, num_beams=1,
                                  max_new_tokens=max_new_tokens)
    # With inputs_embeds the prompt is not echoed: everything returned is new.
    new_tokens = produced[0]
    generated = int(new_tokens.shape[-1])

    raw = processor.decode(new_tokens, skip_special_tokens=True)
    costs = meter.record()
    decode_seconds = max(0.0, costs["seconds_generate"] - costs["seconds_prefill"])
    return {
        **{k: observation[k] for k in
           ("image_id", "source_photo_id", "reference", "condition_id",
            "family", "policy", "seed", "nominal_ratio", "target_placeholders",
            "expected_placeholders")},
        "raw_output": raw,
        "parsed_output": raw.strip(),
        "generated_tokens": generated,
        "reached_max_new_tokens": generated >= max_new_tokens,
        "latency_seconds": costs["seconds_generate"],
        "seconds_decode": decode_seconds,
        "seconds_per_generated_token": decode_seconds / max(1, generated - 1),
        "pre_prune_placeholders": native,
        "llm_visual_positions": kept_visual,
        "prompt_length": prompt_len,
        "staged_sequence_length": expected_len,
        "pre_resized": resize_record is not None,
        **(resize_record or {}),
        **costs,
        **analytic_compute(
            grid=accounting["image_grid_thw"], merge=accounting["spatial_merge_size"],
            llm_visual_positions=kept_visual, prompt_length=expected_len,
        ),
        **{f"native_{k}": v for k, v in accounting.items()},
    }


def assert_path_equivalence(model, processor, image, *, max_new_tokens: int,
                            device: str) -> dict[str, Any]:
    """The staged route must reproduce the legacy route's output exactly.

    `FULL` used to be generated by handing `pixel_values` straight to
    `generate()`. Routing it through explicit features and `inputs_embeds`
    should be an identity, but "should be" is not evidence, and if it is not an
    identity then the recorded FULL baseline and everything measured against it
    are two different quantities. Greedy decoding makes the comparison exact, so
    it is asserted rather than eyeballed.
    """
    import torch

    inputs = _processor_inputs(processor, image, None)
    accounting = _accounting(inputs, model, image.size)
    inputs = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in inputs.items()}
    prompt_len = int(inputs["input_ids"].shape[-1])

    with torch.inference_mode():
        legacy = model.generate(**inputs, do_sample=False, num_beams=1,
                                max_new_tokens=max_new_tokens)
    legacy_text = processor.decode(legacy[0][prompt_len:], skip_special_tokens=True)

    observation = {
        "family": "FULL", "policy": None, "seed": None,
        "condition_id": "FULL", "expected_placeholders": accounting["placeholders"],
        "forced_pixels": None, "image_id": "path-equivalence",
        "source_photo_id": "path-equivalence", "reference": "",
        "nominal_ratio": 1.0, "target_placeholders": accounting["placeholders"],
        "pre_resize": None, "budget_matched": False,
    }
    staged = execute_observation(model, processor, image, observation,
                                 max_new_tokens=max_new_tokens, device=device)
    if staged["raw_output"] != legacy_text:
        raise RuntimeError(
            "staged path diverged from the legacy path:\n"
            f"  legacy: {legacy_text!r}\n"
            f"  staged: {staged['raw_output']!r}"
        )
    return {
        "path_equivalence": "IDENTICAL",
        "placeholders": accounting["placeholders"],
        "output": legacy_text,
    }
