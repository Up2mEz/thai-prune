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
                # Round 3. Render the region at this budget's grid and then
                # restore it to FULL's grid, so an arm can carry this budget's
                # pixel detail while presenting FULL's token count and
                # magnification. Without it, Resolution Reduction and pruning
                # differ in detail *and* in token count at once.
                "restored": {
                    "down_height": resize["processed_height"],
                    "down_width": resize["processed_width"],
                    "up_height": processed[0],
                    "up_width": processed[1],
                    "forced_pixels": processed[0] * processed[1],
                    "placeholders": full,
                },
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


def plan_magnification_sweep(
    height: int,
    width: int,
    full_placeholders: int,
    factors: Sequence[float],
    *,
    smart_resize: SmartResize,
    patch: int,
    merge: int,
) -> list[dict[str, Any]]:
    """Forced budgets at multiples of FULL's token count, above and below it.

    Round 1 found a reduced budget outscoring FULL, and round 2 showed why that
    is hard to interpret: these crops are far smaller than the processor's pixel
    floor, so *every* condition is an upsample of the source and none of them
    loses source information. What differs between FULL and a reduced budget is
    magnification, and magnification cannot be separated from token count for a
    whole image - one knob sets both.

    What can be done is to trace the curve. If accuracy keeps improving as
    magnification falls toward native and degrades as it is pushed past FULL,
    then FULL simply sits on the wrong side of a scale preference, and the
    round 1 inversion needs no appeal to compression helping. A factor above 1
    magnifies more than FULL does; that direction is the informative one,
    because nothing in the compression story predicts it should hurt.
    """
    planned: list[dict[str, Any]] = []
    for factor in factors:
        if factor <= 0:
            raise ValueError(f"factor must be positive, got {factor}")
        target = max(1, round(full_placeholders * factor))
        resize = find_pixel_budget_for_target(
            height, width, target, smart_resize=smart_resize, patch=patch, merge=merge,
        )
        planned.append({
            "factor": factor,
            "target_placeholders": target,
            "resolution": resize,
            "placeholders": resize["achieved"],
        })
    return planned
