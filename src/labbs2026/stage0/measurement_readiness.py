"""Measurement-readiness audit using preserved S0 artifacts only."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


SESOI = 0.10


def headroom_class(ci_low: float, sesoi: float = SESOI) -> str:
    """Classify from SESOI multiples, without outcome-tuned cut points."""
    if ci_low >= 2 * sesoi:
        return "ADEQUATE_HEADROOM"
    if ci_low >= sesoi:
        return "MARGINAL_HEADROOM"
    return "FLOOR_LIMITED"


def _pair_rates(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["model_role"], row["pair_id"])].append(row)
    result = {}
    for key, group in groups.items():
        if len(group) != 8:
            raise RuntimeError(f"expected eight clustered observations: {key}")
        result[key] = {
            "component_type": group[0]["component_type"],
            "successes": sum(bool(row["primary_exact"]) for row in group),
            "rate": float(np.mean([row["primary_exact"] for row in group])),
        }
    return result


def build_headroom_audit(
    rows: list[dict[str, Any]], analysis: dict[str, Any]
) -> list[dict[str, Any]]:
    rates = _pair_rates(rows)
    output = []
    components = sorted({value["component_type"] for value in rates.values()})
    for role in ("BASE", "SPECIALIZED"):
        for component in components:
            values = np.array([
                value["rate"]
                for (model_role, _), value in rates.items()
                if model_role == role and value["component_type"] == component
            ])
            estimate = analysis["components"][component][role]
            output.append({
                "model_role": role,
                "component_type": component,
                "full_information_exact_accuracy": estimate["estimate"],
                "ci_low": estimate["ci_low"],
                "ci_high": estimate["ci_high"],
                "cluster_count": len(values),
                "maximum_possible_absolute_downward_degradation": estimate["estimate"],
                "headroom_minus_10pp_sesoi": estimate["estimate"] - SESOI,
                "headroom_in_sesoi_units": estimate["estimate"] / SESOI,
                "fraction_pair_clusters_at_exact_floor": float(np.mean(values == 0)),
                "fraction_pair_clusters_at_exact_ceiling": float(np.mean(values == 1)),
                "classification": headroom_class(estimate["ci_low"]),
            })
    return output


def _logit_shifted(probabilities: np.ndarray, requested_drop: float) -> np.ndarray:
    """Find a common log-odds shift giving the requested marginal drop."""
    target = probabilities.mean() - requested_drop
    if target < -1e-12:
        raise ValueError("requested degradation exceeds baseline mean")
    if requested_drop == 0:
        return probabilities.copy()
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1 - clipped))
    low, high = -40.0, 0.0
    for _ in range(100):
        middle = (low + high) / 2
        mean = np.mean(1 / (1 + np.exp(-(logits + middle))))
        if mean < target:
            low = middle
        else:
            high = middle
    return 1 / (1 + np.exp(-(logits + (low + high) / 2)))


def _simulate_scenario(
    base: np.ndarray,
    specialized: np.ndarray,
    base_drop: float,
    specialized_drop: float,
    simulations: int,
    seed: int,
    renders_per_cluster: int = 8,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(base)
    reduced_base = _logit_shifted(base, base_drop)
    reduced_specialized = _logit_shifted(specialized, specialized_drop)
    detected = 0
    estimates = np.empty(simulations)
    for simulation in range(simulations):
        indices = rng.integers(0, n, size=n)
        b0 = rng.binomial(renders_per_cluster, base[indices]) / renders_per_cluster
        b1 = rng.binomial(renders_per_cluster, reduced_base[indices]) / renders_per_cluster
        s0 = rng.binomial(renders_per_cluster, specialized[indices]) / renders_per_cluster
        s1 = rng.binomial(renders_per_cluster, reduced_specialized[indices]) / renders_per_cluster
        interaction = (s1 - s0) - (b1 - b0)
        estimate = float(interaction.mean())
        se = float(interaction.std(ddof=1) / np.sqrt(n))
        estimates[simulation] = estimate
        detected += int(estimate - 1.96 * se > 0 or estimate + 1.96 * se < 0)
    return {
        "mean_estimated_interaction": float(estimates.mean()),
        "detection_probability_ci_excludes_zero": detected / simulations,
        "simulation_estimate_q025": float(np.quantile(estimates, 0.025)),
        "simulation_estimate_q975": float(np.quantile(estimates, 0.975)),
        "cluster_count": n,
    }


def simulation_planning(
    rows: list[dict[str, Any]], simulations: int = 5000, seed: int = 20260912
) -> dict[str, Any]:
    rates = _pair_rates(rows)
    pair_ids = sorted({pair_id for _, pair_id in rates})
    components = {pair_id: rates[("BASE", pair_id)]["component_type"] for pair_id in pair_ids}

    def probabilities(role: str, selected: list[str], smoothing: str) -> np.ndarray:
        successes = np.array([rates[(role, pair_id)]["successes"] for pair_id in selected], dtype=float)
        if smoothing == "EMPIRICAL_PLUGIN":
            return successes / 8
        if smoothing == "JEFFREYS":
            return (successes + 0.5) / 9
        raise ValueError(smoothing)

    scenarios = []

    def safe_simulate(
        base: np.ndarray,
        specialized: np.ndarray,
        base_drop: float,
        specialized_drop: float,
        scenario_seed: int,
    ) -> dict[str, Any]:
        try:
            return _simulate_scenario(
                base,
                specialized,
                base_drop,
                specialized_drop,
                simulations,
                scenario_seed,
            )
        except ValueError:
            return {"status": "STRUCTURALLY_INFEASIBLE_FROM_ASSUMED_BASELINE"}

    for smoothing_index, smoothing in enumerate(("EMPIRICAL_PLUGIN", "JEFFREYS")):
        base = probabilities("BASE", pair_ids, smoothing)
        specialized = probabilities("SPECIALIZED", pair_ids, smoothing)
        for index, common_drop_pp in enumerate((0, 5, 10, 15, 20)):
            common = common_drop_pp / 100
            scenarios.append({
                "smoothing": smoothing,
                "common_degradation_pp": common_drop_pp,
                "null_equal_degradation": safe_simulate(base, specialized, common, common, seed + smoothing_index * 1000 + index),
                "alternative_base_degrades_10pp_more": safe_simulate(base, specialized, common + SESOI, common, seed + smoothing_index * 1000 + 100 + index),
                "alternative_specialized_degrades_10pp_more": safe_simulate(base, specialized, common, common + SESOI, seed + smoothing_index * 1000 + 200 + index),
            })

    component_power = []
    for component_index, component in enumerate(sorted(set(components.values()))):
        selected = [pair_id for pair_id in pair_ids if components[pair_id] == component]
        base = probabilities("BASE", selected, "EMPIRICAL_PLUGIN")
        specialized = probabilities("SPECIALIZED", selected, "EMPIRICAL_PLUGIN")
        # A 10 pp differential at zero common degradation is feasible for every
        # observed component in both orientations except when the relevant mean
        # is below 10 pp. Record infeasibility instead of silently clipping.
        entry: dict[str, Any] = {"component_type": component, "cluster_count": len(selected)}
        for label, base_drop, specialized_drop in (
            ("base_degrades_10pp_more", SESOI, 0.0),
            ("specialized_degrades_10pp_more", 0.0, SESOI),
        ):
            try:
                entry[label] = _simulate_scenario(base, specialized, base_drop, specialized_drop, simulations, seed + 3000 + component_index * 10 + (base_drop == 0))
            except ValueError:
                entry[label] = {"status": "STRUCTURALLY_INFEASIBLE_FROM_EMPIRICAL_BASELINE"}
        component_power.append(entry)
    return {
        "schema_version": 1,
        "scope": "DESIGN_ANALYSIS_ONLY_NO_REDUCED_BUDGET_OBSERVATIONS",
        "simulations_per_scenario": simulations,
        "seed": seed,
        "cluster_unit": "pair_id",
        "renders_per_cluster": 8,
        "assumptions": [
            "One generic future reduced-budget condition is contrasted with full information; no token budget is selected.",
            "A common log-odds shift is calibrated to each requested marginal percentage-point degradation.",
            "The 95 paired pair_id clusters are resampled; eight renders remain inside each cluster.",
            "Conditional binomial variation is a planning assumption, not empirical compression behavior.",
            "Normal 95% cluster-level intervals approximate the future paired marginal interaction test.",
            "EMPIRICAL_PLUGIN is primary; JEFFREYS smoothing is a floor/ceiling sensitivity analysis.",
        ],
        "overall_scenarios": scenarios,
        "component_10pp_sensitivity": component_power,
    }


def build_audit(artifact_dir: Path) -> dict[str, Any]:
    manifest = json.loads((artifact_dir / "manifest.json").read_text("utf-8"))
    locked = json.loads((artifact_dir / "locked_set_audit.json").read_text("utf-8"))
    if manifest["call_count"] != 1520 or manifest["pair_count"] != 95:
        raise RuntimeError("unexpected S0 artifact scope")
    if locked["locked_pair_count"] != 0 or not locked["valid"]:
        raise RuntimeError("locked-set audit is not valid")
    rows = [json.loads(line) for line in (artifact_dir / "raw_outputs.jsonl").read_text("utf-8").splitlines()]
    if len(rows) != 1520:
        raise RuntimeError("raw output count mismatch")
    analysis = json.loads((artifact_dir / "analysis.json").read_text("utf-8"))
    return {
        "schema_version": 1,
        "source_run_id": manifest["run_id"],
        "source_git_sha": manifest["git_sha"],
        "new_model_inference": False,
        "locked_validation_access": False,
        "compression_run": False,
        "sesoi_pp": 10,
        "classification_rule": {
            "ADEQUATE_HEADROOM": "pair-clustered lower CI >= 2 x SESOI",
            "MARGINAL_HEADROOM": "SESOI <= pair-clustered lower CI < 2 x SESOI",
            "FLOOR_LIMITED": "pair-clustered lower CI < SESOI",
        },
        "headroom_cells": build_headroom_audit(rows, analysis),
        "simulation_planning": simulation_planning(rows),
    }


def write_audit(artifact_dir: Path, output: Path) -> dict[str, Any]:
    audit = build_audit(artifact_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return audit
