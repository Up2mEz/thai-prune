"""Per-region budget matching between Resolution Reduction and Token Pruning.

Resolution Reduction is applied by forcing the processor's pixel budget, not by
pre-resizing the source. Pre-resizing does not work at all here: `min_pixels`
upsamples anything smaller back to the floor, so every reduced budget collapses
onto the same ~144-placeholder count and the levels become indistinguishable.
Setting `min_pixels = max_pixels = target` is the same mechanism the frozen
design already registered as `force_equal_min_max_pixels`.

Even then the processor rounds each side up to `patch * merge` pixels, so
achievable placeholder counts remain a coarse, shape-dependent lattice. The protocol therefore matches budgets *per
region*: resize to land as close as possible to each target, record what was
actually achieved, and then prune to exactly that achieved number. Both arms
then deliver an identical number of visual positions for that region, which is
what makes the H3 contrast a comparison of *where* compression happens rather
than *how much*.

`smart_resize` is injected rather than imported so this module is testable
without loading a processor.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

SmartResize = Callable[..., tuple[int, int]]


def placeholders_for(
    height: int,
    width: int,
    *,
    smart_resize: SmartResize,
    patch: int,
    merge: int,
    min_pixels: int,
    max_pixels: int,
) -> tuple[int, tuple[int, int]]:
    """Placeholder count the processor would produce, and the resized shape."""
    new_h, new_w = smart_resize(
        height, width, factor=patch * merge, min_pixels=min_pixels, max_pixels=max_pixels
    )
    grid_h, grid_w = new_h // patch, new_w // patch
    return (grid_h // merge) * (grid_w // merge), (new_h, new_w)


def find_pixel_budget_for_target(
    height: int,
    width: int,
    target: int,
    *,
    smart_resize: SmartResize,
    patch: int,
    merge: int,
    search_span: float = 0.35,
    search_steps: int = 240,
) -> dict[str, Any]:
    """Forced pixel budget whose processed placeholder count is closest to `target`.

    Scans around the analytic estimate `target * (patch * merge) ** 2` rather
    than trusting it, because `smart_resize` rounds both axes independently and
    the achieved count is not monotonic in the requested area.

    Ties break toward the smaller achieved count so a budget is never
    accidentally overshot into a larger one.
    """
    if target < 1:
        raise ValueError("target must be >= 1")

    cell = (patch * merge) ** 2
    centre = target * cell
    low = max(cell, int(centre * (1.0 - search_span)))
    high = int(centre * (1.0 + search_span))

    best: dict[str, Any] | None = None
    for step in range(search_steps + 1):
        pixels = low + round((high - low) * step / search_steps)
        achieved, resized = placeholders_for(
            height, width, smart_resize=smart_resize, patch=patch, merge=merge,
            min_pixels=pixels, max_pixels=pixels,
        )
        key = (abs(achieved - target), achieved)
        if best is None or key < (abs(best["achieved"] - target), best["achieved"]):
            best = {
                "forced_pixels": pixels,
                "processed_height": resized[0],
                "processed_width": resized[1],
                "achieved": achieved,
            }
    assert best is not None
    best["target"] = target
    best["absolute_error"] = abs(best["achieved"] - target)
    return best


def plan_region_budgets(
    height: int,
    width: int,
    ratios: Sequence[float],
    *,
    smart_resize: SmartResize,
    patch: int,
    merge: int,
    min_pixels: int,
    max_pixels: int,
) -> dict[str, Any]:
    """Full budget plan for one region: FULL, then one matched pair per ratio.

    The pruning budget is the count Resolution Reduction *achieved*, never the
    nominal target, so the two arms are matched exactly even where the lattice
    prevents RR from reaching the target.
    """
    full, processed = placeholders_for(
        height, width, smart_resize=smart_resize, patch=patch, merge=merge,
        min_pixels=min_pixels, max_pixels=max_pixels,
    )
    budgets = []
    for ratio in ratios:
        if not 0 < ratio < 1:
            raise ValueError(f"ratio must be strictly between 0 and 1, got {ratio}")
        target = max(1, round(full * ratio))
        resize = find_pixel_budget_for_target(
            height, width, target, smart_resize=smart_resize, patch=patch, merge=merge,
        )
        budgets.append(
            {
                "ratio": ratio,
                "target_placeholders": target,
                "resolution_reduction": resize,
                "pruning_placeholders": resize["achieved"],
                "matched": True,
            }
        )
    return {
        "full_placeholders": full,
        "full_processed_shape": [processed[0], processed[1]],
        "source_shape": [height, width],
        "budgets": budgets,
    }


def degenerate_budgets(plan: dict[str, Any]) -> list[float]:
    """Ratios whose achieved budget collides with FULL or with another budget."""
    counts = [plan["full_placeholders"]] + [b["pruning_placeholders"] for b in plan["budgets"]]
    collisions = []
    for index, budget in enumerate(plan["budgets"], start=1):
        others = counts[:index] + counts[index + 1 :]
        if budget["pruning_placeholders"] in others:
            collisions.append(budget["ratio"])
    return collisions
