"""Assembly of the region-OCR condition grid.

One region contributes one `FULL` observation plus, for each nominal ratio, a
matched pair of interventions: Resolution Reduction at a forced pixel budget,
and post-encoder pruning to the count that Resolution Reduction actually
achieved for that same region.

The matching is the whole point of the design, so it is enforced here rather
than trusted: a pruning observation always carries the achieved count of its
partner, never the nominal target.
"""

from __future__ import annotations

from typing import Any, Sequence

FAMILY_FULL = "FULL"
FAMILY_RR = "INPUT_RESOLUTION_REDUCTION"
FAMILY_PRUNE = "POST_ENCODER_TOKEN_PRUNING"
FAMILY_MERGE = "POST_ENCODER_SPATIAL_MERGE"

POLICY_GRID = "GRID"
POLICY_RANDOM = "RANDOM"
POLICY_COVERAGE = "COVERAGE"
POLICY_MERGE_GRID = "MERGE_GRID"

# Both post-encoder families are matched against the same Resolution Reduction
# partner, so anything that checks matching must treat them together.
POST_ENCODER_FAMILIES = (FAMILY_PRUNE, FAMILY_MERGE)


def build_region_observations(
    region: dict[str, Any],
    plan: dict[str, Any],
    *,
    random_seeds: Sequence[int],
) -> list[dict[str, Any]]:
    """Every observation for one region: FULL, then a matched pair per ratio."""
    if not random_seeds:
        raise ValueError("at least one random seed is required")
    if len(set(random_seeds)) != len(random_seeds):
        raise ValueError("random seeds must be distinct")

    base = {
        "image_id": region["image_id"],
        "source_photo_id": region["source_photo_id"],
        "reference": region["label"],
        "full_placeholders": plan["full_placeholders"],
    }
    observations: list[dict[str, Any]] = [
        {
            **base,
            "condition_id": "FULL",
            "family": FAMILY_FULL,
            "policy": None,
            "seed": None,
            "nominal_ratio": 1.0,
            "target_placeholders": plan["full_placeholders"],
            "expected_placeholders": plan["full_placeholders"],
            "forced_pixels": None,
        }
    ]

    for budget in plan["budgets"]:
        ratio = budget["ratio"]
        achieved = budget["pruning_placeholders"]
        label = f"{int(round(ratio * 100)):02d}"
        observations.append(
            {
                **base,
                "condition_id": f"RR_{label}",
                "family": FAMILY_RR,
                "policy": None,
                "seed": None,
                "nominal_ratio": ratio,
                "target_placeholders": budget["target_placeholders"],
                "expected_placeholders": achieved,
                "forced_pixels": budget["resolution_reduction"]["forced_pixels"],
            }
        )
        observations.append(
            {
                **base,
                "condition_id": f"PRUNE_GRID_{label}",
                "family": FAMILY_PRUNE,
                "policy": POLICY_GRID,
                "seed": None,
                "nominal_ratio": ratio,
                "target_placeholders": budget["target_placeholders"],
                "expected_placeholders": achieved,
                "forced_pixels": None,
            }
        )
        # Same survivors and same M-RoPE positions as PRUNE_GRID; the only
        # difference is that each survivor carries the mean of its cell instead
        # of its own vector. Any gap between the two is therefore attributable
        # to the discarded content, not to the token count.
        observations.append(
            {
                **base,
                "condition_id": f"MERGE_GRID_{label}",
                "family": FAMILY_MERGE,
                "policy": POLICY_MERGE_GRID,
                "seed": None,
                "nominal_ratio": ratio,
                "target_placeholders": budget["target_placeholders"],
                "expected_placeholders": achieved,
                "forced_pixels": None,
            }
        )
        # Same spatial coverage guarantee as PRUNE_GRID, but each cell spends
        # its one survivor on the token carrying the most contrast, which is
        # where a small glyph would be.
        observations.append(
            {
                **base,
                "condition_id": f"PRUNE_COVERAGE_{label}",
                "family": FAMILY_PRUNE,
                "policy": POLICY_COVERAGE,
                "seed": None,
                "nominal_ratio": ratio,
                "target_placeholders": budget["target_placeholders"],
                "expected_placeholders": achieved,
                "forced_pixels": None,
            }
        )
        for seed in random_seeds:
            observations.append(
                {
                    **base,
                    "condition_id": f"PRUNE_RANDOM_s{seed}_{label}",
                    "family": FAMILY_PRUNE,
                    "policy": POLICY_RANDOM,
                    "seed": seed,
                    "nominal_ratio": ratio,
                    "target_placeholders": budget["target_placeholders"],
                    "expected_placeholders": achieved,
                    "forced_pixels": None,
                }
            )
    return observations


def assert_matched(observations: Sequence[dict[str, Any]]) -> None:
    """Every pruning observation must match its Resolution Reduction partner.

    If this ever fails the two arms are not comparable and the H3 contrast is
    meaningless, so it raises rather than warning.
    """
    by_region: dict[str, dict[tuple[str, float], list[dict[str, Any]]]] = {}
    for obs in observations:
        if obs["family"] == FAMILY_FULL:
            continue
        key = (obs["image_id"], obs["nominal_ratio"])
        by_region.setdefault(obs["image_id"], {}).setdefault(key, []).append(obs)

    for region_map in by_region.values():
        for (image_id, ratio), group in region_map.items():
            rr = [o for o in group if o["family"] == FAMILY_RR]
            pruned = [o for o in group if o["family"] in POST_ENCODER_FAMILIES]
            if len(rr) != 1:
                raise RuntimeError(f"{image_id} ratio {ratio}: expected one RR observation")
            if not pruned:
                raise RuntimeError(f"{image_id} ratio {ratio}: no pruning partner")
            expected = rr[0]["expected_placeholders"]
            for obs in pruned:
                if obs["expected_placeholders"] != expected:
                    raise RuntimeError(
                        f"{image_id} ratio {ratio}: pruning budget "
                        f"{obs['expected_placeholders']} != RR achieved {expected}"
                    )


def build_workload(
    regions: Sequence[dict[str, Any]],
    plans: dict[str, dict[str, Any]],
    *,
    random_seeds: Sequence[int],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for region in regions:
        plan = plans[region["image_id"]]
        observations.extend(
            build_region_observations(region, plan, random_seeds=random_seeds)
        )
    ids = [(o["image_id"], o["condition_id"]) for o in observations]
    if len(set(ids)) != len(ids):
        raise RuntimeError("duplicate (image_id, condition_id) in workload")
    assert_matched(observations)
    return observations


def workload_summary(observations: Sequence[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, int] = {}
    for obs in observations:
        families[obs["family"]] = families.get(obs["family"], 0) + 1
    regions = {o["image_id"] for o in observations}
    return {
        "observations": len(observations),
        "regions": len(regions),
        "clusters": len({o["source_photo_id"] for o in observations}),
        "conditions_per_region": len(observations) // max(1, len(regions)),
        "by_family": families,
    }
