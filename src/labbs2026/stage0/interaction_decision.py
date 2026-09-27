"""Frozen interpretation rule for the confirmatory MODEL x BUDGET analysis."""

from __future__ import annotations

import math
from collections.abc import Mapping


DID_NAMES = ("DID_196", "DID_121", "DID_64")
ALPHA = 0.05
ABSOLUTE_SESOI = 0.10


def classify_interaction(
    omnibus_p_value: float,
    did_estimates: Mapping[str, float],
    holm_adjusted_p_values: Mapping[str, float],
) -> str:
    """Apply the pre-registered confirmatory interpretation without directionality."""
    if set(did_estimates) != set(DID_NAMES):
        raise ValueError(f"DID estimates must contain exactly {DID_NAMES}")
    if set(holm_adjusted_p_values) != set(DID_NAMES):
        raise ValueError(f"Holm p-values must contain exactly {DID_NAMES}")
    values = [omnibus_p_value, *did_estimates.values(), *holm_adjusted_p_values.values()]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("all estimates and p-values must be finite")
    if not 0 <= omnibus_p_value <= 1 or any(
        not 0 <= value <= 1 for value in holm_adjusted_p_values.values()
    ):
        raise ValueError("p-values must be within [0, 1]")

    if omnibus_p_value > ALPHA:
        return "NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE"

    meaningful = {
        name for name in DID_NAMES if abs(did_estimates[name]) >= ABSOLUTE_SESOI
    }
    if not meaningful:
        return "INTERACTION_DETECTED_BELOW_PLANNED_SESOI"
    if any(holm_adjusted_p_values[name] <= ALPHA for name in meaningful):
        return "MEANINGFUL_MODEL_BUDGET_INTERACTION_SUPPORTED"
    return "SUGGESTIVE_MEANINGFUL_INTERACTION_NOT_CONFIRMED"
