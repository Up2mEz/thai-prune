"""Region-OCR run: plan budgets, assemble the grid, execute, write artifacts."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import time
from pathlib import Path
from typing import Any, Sequence

from labbs2026.region_ocr.budget import (
    degenerate_budgets,
    find_pixel_budget_for_target,
    placeholders_for,
    plan_magnification_sweep,
    plan_region_budgets,
)
from labbs2026.region_ocr.execute import (
    PROMPT,
    assert_path_equivalence,
    execute_observation,
)
from labbs2026.region_ocr.workload import build_workload, workload_summary


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_processor_geometry(processor) -> dict[str, Any]:
    """Geometry and the resize rule, read from the image processor.

    `AutoProcessor` returns a wrapper; `smart_resize`, the patch/merge sizes and
    the pixel bounds all live on the image processor inside it, so the wrapper is
    unwrapped rather than queried directly.
    """
    image_processor = getattr(processor, "image_processor", processor)
    module = __import__(type(image_processor).__module__, fromlist=["smart_resize"])
    smart_resize = getattr(module, "smart_resize", None)
    if smart_resize is None:
        from transformers.models.paddleocr_vl import image_processing_paddleocr_vl as fallback

        smart_resize = fallback.smart_resize
    # Older remote-code processors expose min_pixels/max_pixels directly; the
    # native transformers class carries the same bounds inside its SizeDict.
    size = getattr(image_processor, "size", None)
    min_pixels = getattr(image_processor, "min_pixels", None)
    max_pixels = getattr(image_processor, "max_pixels", None)
    if min_pixels is None and size is not None:
        min_pixels = size["shortest_edge"] if isinstance(size, dict) else size.shortest_edge
    if max_pixels is None and size is not None:
        max_pixels = size["longest_edge"] if isinstance(size, dict) else size.longest_edge
    if min_pixels is None or max_pixels is None:
        raise RuntimeError("could not resolve the processor's pixel bounds")
    return {
        "smart_resize": smart_resize,
        "patch": image_processor.patch_size,
        "merge": image_processor.merge_size,
        "min_pixels": int(min_pixels),
        "max_pixels": int(max_pixels),
    }


def preflight_processor_contract(processor, geometry: dict[str, Any]) -> dict[str, Any]:
    """Check the processor API before any weights are loaded.

    Three separate failures were hit in development because the API surface
    differs between the remote-code path used while exploring and the native
    path the runs actually use: `smart_resize` lives in a different module, the
    pixel bounds moved into a SizeDict, and Resolution Reduction needs a
    different kwarg shape. Each surfaced one at a time, after a slow weight load.

    This reproduces all three in seconds on a synthetic image, so an API change
    fails fast and visibly instead of mid-run.
    """
    from PIL import Image
    import numpy as np

    probe = Image.fromarray(np.full((64, 256, 3), 255, dtype=np.uint8), "RGB")
    messages = [{"role": "user", "content": [
        {"type": "image", "image": probe}, {"type": "text", "text": PROMPT}]}]

    baseline = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
    )
    grid = [int(v) for v in baseline["image_grid_thw"][0].tolist()]
    merge = geometry["merge"]
    observed_full = grid[0] * (grid[1] // merge) * (grid[2] // merge)

    predicted_full, _ = placeholders_for(64, 256, **geometry)
    if observed_full != predicted_full:
        raise RuntimeError(
            "processor geometry contract broken: predicted "
            f"{predicted_full} placeholders, processor produced {observed_full}"
        )

    target = max(1, round(observed_full * 0.5))
    forced = find_pixel_budget_for_target(
        64, 256, target, smart_resize=geometry["smart_resize"],
        patch=geometry["patch"], merge=geometry["merge"],
    )
    reduced = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
        processor_kwargs={
            "size": {"shortest_edge": forced["forced_pixels"],
                     "longest_edge": forced["forced_pixels"]},
            "min_pixels": forced["forced_pixels"],
            "max_pixels": forced["forced_pixels"],
        },
    )
    rgrid = [int(v) for v in reduced["image_grid_thw"][0].tolist()]
    observed_reduced = rgrid[0] * (rgrid[1] // merge) * (rgrid[2] // merge)
    if observed_reduced != forced["achieved"]:
        raise RuntimeError(
            "Resolution Reduction contract broken: forcing "
            f"{forced['forced_pixels']} pixels predicted {forced['achieved']} "
            f"placeholders but produced {observed_reduced}"
        )
    if observed_reduced >= observed_full:
        raise RuntimeError(
            f"Resolution Reduction did not reduce: {observed_full} -> {observed_reduced}"
        )
    return {
        "probe_shape": [64, 256],
        "full_placeholders": observed_full,
        "reduced_placeholders": observed_reduced,
        "forced_pixels": forced["forced_pixels"],
        "geometry_prediction_matches": True,
        "resolution_reduction_effective": True,
    }


def plan_all_budgets(regions: Sequence[dict[str, Any]], geometry: dict[str, Any],
                     ratios: Sequence[float],
                     sweep_factors: Sequence[float] = ()) -> tuple[dict[str, Any], list[str]]:
    plans: dict[str, Any] = {}
    degenerate: list[str] = []
    sweep_geometry = {k: v for k, v in geometry.items() if k not in ("min_pixels", "max_pixels")}
    for region in regions:
        plan = plan_region_budgets(
            region["image_height"], region["image_width"], ratios, **geometry
        )
        if degenerate_budgets(plan):
            degenerate.append(region["image_id"])
        # The sweep deliberately leaves the processor's own floor and ceiling
        # behind: its whole purpose is to reach magnifications FULL cannot.
        plan["sweep"] = plan_magnification_sweep(
            region["image_height"], region["image_width"],
            plan["full_placeholders"], sweep_factors, **sweep_geometry,
        )
        plans[region["image_id"]] = plan
    return plans, degenerate


def run(
    *,
    regions: Sequence[dict[str, Any]],
    images_dir: Path,
    model,
    processor,
    ratios: Sequence[float],
    random_seeds: Sequence[int],
    max_new_tokens: int,
    device: str,
    artifact_dir: Path,
    sweep_factors: Sequence[float] = (),
) -> dict[str, Any]:
    from PIL import Image

    artifact_dir.mkdir(parents=True, exist_ok=True)
    geometry = load_processor_geometry(processor)
    contract = preflight_processor_contract(processor, geometry)
    plans, degenerate = plan_all_budgets(regions, geometry, ratios, sweep_factors)
    if degenerate:
        raise RuntimeError(f"degenerate budget plan for {len(degenerate)} regions: {degenerate[:5]}")

    workload = build_workload(regions, plans, random_seeds=random_seeds)
    summary = workload_summary(workload)

    # Every family now reaches generate() through inputs_embeds. That reroute
    # must be an identity for the unintervened condition, or the FULL baseline
    # recorded here is not the same quantity as the one recorded before it, and
    # every delta measured against it is meaningless. Checked once, on a real
    # region, before any observation is written.
    first = regions[0]
    with Image.open(images_dir / f"{first['image_id']}.jpg") as opened:
        opened.load()
        equivalence = assert_path_equivalence(
            model, processor, opened.convert("RGB").copy(),
            max_new_tokens=max_new_tokens, device=device,
        )

    raw_path = artifact_dir / "observations.jsonl"
    failures: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    by_image = {r["image_id"]: r for r in regions}
    images: dict[str, Any] = {}
    started = time.perf_counter()

    with io.open(raw_path, "w", encoding="utf-8", newline="\n") as handle:
        for observation in workload:
            image_id = observation["image_id"]
            if image_id not in images:
                with Image.open(images_dir / f"{image_id}.jpg") as opened:
                    opened.load()
                    region = by_image[image_id]
                    if opened.size != (region["image_width"], region["image_height"]):
                        raise RuntimeError(f"{image_id}: geometry disagrees with metadata")
                    images[image_id] = opened.convert("RGB").copy()
            try:
                record = execute_observation(
                    model, processor, images[image_id], observation,
                    max_new_tokens=max_new_tokens, device=device,
                )
            except Exception as exc:  # recorded, never silently skipped
                failures.append({
                    "image_id": image_id,
                    "condition_id": observation["condition_id"],
                    "error": f"{type(exc).__name__}: {exc}"[:800],
                })
                continue
            records.append(record)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    elapsed = time.perf_counter() - started
    manifest = {
        "status": "REGION_OCR_RUN_COMPLETE" if not failures else "REGION_OCR_RUN_WITH_FAILURES",
        "prompt": PROMPT,
        "path_equivalence": equivalence,
        "ratios": list(ratios),
        "sweep_factors": list(sweep_factors),
        "random_seeds": list(random_seeds),
        "max_new_tokens": max_new_tokens,
        "device": device,
        "python": platform.python_version(),
        "processor_contract": contract,
        "workload": summary,
        "completed_observations": len(records),
        "execution_failures": len(failures),
        "wall_seconds": elapsed,
        "observations_sha256": _sha256(raw_path),
    }
    for name, value in (("manifest.json", manifest),
                        ("execution_failures.json", failures),
                        ("budget_plans.json", plans)):
        with io.open(artifact_dir / name, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return manifest
