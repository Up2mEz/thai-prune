"""Registered analysis for the region-OCR pruning branch.

Implements exactly what the protocol froze:

  * primary population = every eligible region; pre-registered secondary =
    regions where CER(FULL) = 0;
  * per-region delta-CER against FULL, paired within region;
  * the registered estimand DiD_b = deltaCER(PRUNE_GRID, b) - deltaCER(RR, b);
  * cluster bootstrap over `source_photo_id` using **one shared index matrix**
    across every condition, so the two terms of a difference are computed on the
    same resampled clusters and the contrast keeps its covariance;
  * Holm across the three budgets, primary population only.

Execution failures are excluded and counted, never scored as CER 1.0: that would
convert infrastructure faults into apparent degradation.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from labbs2026.region_ocr.text_metrics import region_cer

FULL = "FULL"
GRID = "PRUNE_GRID"
RR = "RR"


def condition_key(record: dict[str, Any]) -> str:
    return str(record["condition_id"])


def per_region_cer(records: Iterable[dict[str, Any]]) -> dict[tuple[str, str], float]:
    """CER for every (region, condition) cell."""
    table: dict[tuple[str, str], float] = {}
    for record in records:
        key = (record["image_id"], condition_key(record))
        if key in table:
            raise RuntimeError(f"duplicate observation for {key}")
        table[key] = region_cer(record["reference"], record["parsed_output"])
    return table


def eligible_regions(
    table: dict[tuple[str, str], float],
    conditions: Sequence[str],
    *,
    full_correct_only: bool = False,
) -> list[str]:
    """Regions with a complete row across the conditions an analysis needs.

    A region missing any required cell is dropped from that analysis rather than
    silently contributing an unbalanced pair.
    """
    regions = sorted({image for image, _ in table})
    complete = [r for r in regions if all((r, c) in table for c in (FULL, *conditions))]
    if full_correct_only:
        complete = [r for r in complete if table[(r, FULL)] == 0.0]
    return complete


def delta_cer(table: dict[tuple[str, str], float], regions: Sequence[str],
              condition: str) -> np.ndarray:
    """Per-region CER change against FULL, paired within region."""
    return np.array(
        [table[(r, condition)] - table[(r, FULL)] for r in regions], dtype=float
    )


def _cluster_indices(regions: Sequence[str], clusters: dict[str, str]) -> list[np.ndarray]:
    groups: dict[str, list[int]] = {}
    for position, region in enumerate(regions):
        groups.setdefault(clusters[region], []).append(position)
    return [np.array(v, dtype=int) for _, v in sorted(groups.items())]


def bootstrap_matrix(
    regions: Sequence[str], clusters: dict[str, str], *, resamples: int, seed: int
) -> list[np.ndarray]:
    """Shared resample plan: a list of region-index arrays, one per draw.

    Built once and reused for every statistic in the analysis. Drawing
    independently per condition would inflate every difference's interval.
    """
    groups = _cluster_indices(regions, clusters)
    rng = np.random.default_rng(seed)
    count = len(groups)
    draws = rng.integers(0, count, size=(resamples, count))
    return [np.concatenate([groups[g] for g in row]) for row in draws]


def _interval(samples: np.ndarray, confidence: float) -> tuple[float, float]:
    lower = float(np.quantile(samples, (1 - confidence) / 2))
    upper = float(np.quantile(samples, 1 - (1 - confidence) / 2))
    return lower, upper


def summarise(values: np.ndarray, plan: Sequence[np.ndarray], *,
              confidence: float = 0.95) -> dict[str, Any]:
    draws = np.array([values[idx].mean() for idx in plan], dtype=float)
    low, high = _interval(draws, confidence)
    return {
        "mean": float(values.mean()),
        "ci_low": low,
        "ci_high": high,
        "n_regions": int(values.size),
    }


def bootstrap_p_value(draws: np.ndarray) -> float:
    """Two-sided centred bootstrap p-value for a mean difference of zero."""
    centred = draws - draws.mean()
    observed = abs(draws.mean())
    return float((np.abs(centred) >= observed).mean())


def holm(p_values: Sequence[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        value = (len(p_values) - rank) * p_values[index]
        running = max(running, min(1.0, value))
        adjusted[index] = running
    return adjusted


def analyse_population(
    table: dict[tuple[str, str], float],
    clusters: dict[str, str],
    budgets: Sequence[str],
    *,
    resamples: int,
    seed: int,
    full_correct_only: bool,
) -> dict[str, Any]:
    """One population: marginal deltas per arm plus the registered DiD per budget."""
    conditions = [f"{GRID}_{b}" for b in budgets] + [f"{RR}_{b}" for b in budgets]
    regions = eligible_regions(table, conditions, full_correct_only=full_correct_only)
    if not regions:
        raise RuntimeError("no regions have a complete row for this analysis")
    plan = bootstrap_matrix(regions, clusters, resamples=resamples, seed=seed)

    arms: dict[str, Any] = {}
    did: dict[str, Any] = {}
    raw_p: list[float] = []
    for budget in budgets:
        grid = delta_cer(table, regions, f"{GRID}_{budget}")
        rr = delta_cer(table, regions, f"{RR}_{budget}")
        arms[f"{GRID}_{budget}"] = summarise(grid, plan)
        arms[f"{RR}_{budget}"] = summarise(rr, plan)
        contrast = grid - rr
        draws = np.array([contrast[idx].mean() for idx in plan], dtype=float)
        low, high = _interval(draws, 0.95)
        p = bootstrap_p_value(draws)
        raw_p.append(p)
        did[budget] = {
            "estimate": float(contrast.mean()),
            "ci_low": low,
            "ci_high": high,
            "p_value": p,
        }
    for budget, adjusted in zip(budgets, holm(raw_p)):
        did[budget]["p_holm"] = adjusted

    return {
        "population": "CER_FULL_ZERO" if full_correct_only else "ALL_ELIGIBLE",
        "regions": len(regions),
        "clusters": len({clusters[r] for r in regions}),
        "bootstrap_resamples": resamples,
        "arms": arms,
        "did": did,
        "estimand": "DiD_b = deltaCER(PRUNE_GRID,b) - deltaCER(RR,b)",
        "multiplicity": "Holm across budgets" if not full_correct_only else "none (secondary)",
    }
