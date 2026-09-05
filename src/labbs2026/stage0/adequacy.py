"""Outcome-independent pair inventory planning for Stage 0."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from typing import Any


def _score(seed: int, pair_id: str) -> str:
    return hashlib.sha256(f"{seed}|{pair_id}".encode("utf-8")).hexdigest()


def propose_stratified_allocation(
    pairs: list[dict[str, Any]], *, seed: int
) -> dict[str, list[str]]:
    """Split each component evenly using only IDs and a registered seed."""

    grouped: dict[str, list[str]] = defaultdict(list)
    for pair in pairs:
        grouped[str(pair["component_type"])].append(str(pair["pair_id"]))
    calibration: list[str] = []
    locked: list[str] = []
    for component, pair_ids in sorted(grouped.items()):
        rows = [pair for pair in pairs if str(pair["component_type"]) == component]
        constrained = [pair for pair in rows if pair.get("proposed_split")]
        if constrained:
            if len(constrained) != len(rows):
                raise ValueError(f"partial proposed_split constraints: {component}")
            component_calibration = sorted(
                str(pair["pair_id"])
                for pair in rows
                if pair["proposed_split"] == "CALIBRATION"
            )
            component_locked = sorted(
                str(pair["pair_id"])
                for pair in rows
                if pair["proposed_split"] == "LOCKED_VALIDATION"
            )
            if len(component_calibration) != len(component_locked):
                raise ValueError(f"unbalanced proposed_split constraints: {component}")
            if len(component_calibration) + len(component_locked) != len(rows):
                raise ValueError(f"invalid proposed_split value: {component}")
            calibration.extend(component_calibration)
            locked.extend(component_locked)
            continue
        ordered = sorted(pair_ids, key=lambda pair_id: (_score(seed, pair_id), pair_id))
        if len(ordered) % 2:
            raise ValueError(f"component count must be even: {component}")
        midpoint = len(ordered) // 2
        calibration.extend(ordered[:midpoint])
        locked.extend(ordered[midpoint:])
    return {
        "calibration_pair_ids": sorted(calibration),
        "locked_validation_pair_ids": sorted(locked),
    }


def assess_pair_inventory(
    pairs: list[dict[str, Any]], *, seoi_absolute_pp: float, seed: int
) -> dict[str, Any]:
    """Apply a transparent granularity floor without claiming statistical power.

    The floor requires one pair to represent no more than half the provisional
    SESOI within either disjoint split. Repeated renders never enter this count.
    """

    if not 0 < seoi_absolute_pp <= 100:
        raise ValueError("SESOI must be within (0, 100]")
    target_granularity_pp = seoi_absolute_pp / 2
    minimum_pairs_per_split = math.ceil(100 / target_granularity_pp)
    minimum_inventory_per_component = minimum_pairs_per_split * 2
    counts = Counter(str(pair["component_type"]) for pair in pairs)
    allocation = propose_stratified_allocation(pairs, seed=seed)
    calibration_counts = Counter(
        str(pair["component_type"])
        for pair in pairs
        if pair["pair_id"] in set(allocation["calibration_pair_ids"])
    )
    locked_counts = Counter(
        str(pair["component_type"])
        for pair in pairs
        if pair["pair_id"] in set(allocation["locked_validation_pair_ids"])
    )
    inadequate = sorted(
        component
        for component, count in counts.items()
        if count < minimum_inventory_per_component
    )
    return {
        "status": (
            "EXPANSION_REQUIRED"
            if inadequate
            else "MEETS_PROVISIONAL_GRANULARITY_FLOOR_NOT_POWER_GUARANTEE"
        ),
        "method": "pair-level empirical granularity floor",
        "seoi_absolute_pp": seoi_absolute_pp,
        "target_granularity_pp": target_granularity_pp,
        "minimum_pairs_per_split_per_component": minimum_pairs_per_split,
        "minimum_inventory_per_component": minimum_inventory_per_component,
        "component_inventory_counts": dict(sorted(counts.items())),
        "calibration_counts": dict(sorted(calibration_counts.items())),
        "locked_validation_counts": dict(sorted(locked_counts.items())),
        "inadequate_components": inadequate,
        "repeated_renderings_count_as_independent": False,
        "power_guarantee": False,
        "interpretation": (
            "This is a non-outcome planning floor. Calibration must estimate "
            "between-pair heterogeneity and achieved interval precision; meeting "
            "the floor does not establish power for a later 10 pp interaction."
        ),
        "allocation_seed": seed,
        "proposed_allocation": allocation,
    }
