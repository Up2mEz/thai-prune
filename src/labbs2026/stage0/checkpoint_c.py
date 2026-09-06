"""Build Checkpoint C evidence from immutable repaired-calibration artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from labbs2026.stage0.metrics import compare_reproducibility, compute_stage0_metrics
from labbs2026.step3 import sha256_file


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _accuracy(rows: list[dict[str, Any]]) -> float | None:
    return (
        sum(bool(row["is_correct"]) for row in rows) / len(rows) if rows else None
    )


def _subgroup_accuracy(
    rows: list[dict[str, Any]], fields: tuple[str, ...]
) -> dict[str, dict[str, float | int | None]]:
    keys = sorted({tuple(str(row[field]) for field in fields) for row in rows})
    result: dict[str, dict[str, float | int | None]] = {}
    for key in keys:
        selected = [
            row
            for row in rows
            if tuple(str(row[field]) for field in fields) == key
        ]
        result["|".join(key)] = {
            "observation_count": len(selected),
            "accuracy": _accuracy(selected),
        }
    return result


def component_headroom(
    metrics: dict[str, Any], *, planning_seoi_absolute: float
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for component, summary in metrics["per_component"].items():
        accuracy = summary["accuracy_all_scored_observations"]
        interval = metrics["per_component_pair_clustered_accuracy_interval"][
            component
        ]
        point_headroom = accuracy - 0.5
        lower_bound_headroom = interval["lower"] - 0.5
        result[component] = {
            "accuracy": accuracy,
            "pair_clustered_interval": interval,
            "distance_above_chance": point_headroom,
            "accuracy_after_hypothetical_seoi_drop": accuracy
            - planning_seoi_absolute,
            "point_estimate_has_seoi_downward_headroom": point_headroom
            >= planning_seoi_absolute,
            "interval_lower_bound_has_seoi_downward_headroom": lower_bound_headroom
            >= planning_seoi_absolute,
            "interpretation": (
                "HEADROOM_CLEAR_AT_POINT_AND_INTERVAL_LOWER_BOUND"
                if lower_bound_headroom >= planning_seoi_absolute
                else "HEADROOM_PRESENT_AT_POINT_BUT_NOT_INTERVAL_LOWER_BOUND"
                if point_headroom >= planning_seoi_absolute
                else "POINT_HEADROOM_BELOW_PLANNING_SESOI"
            ),
        }
    return result


def build_checkpoint_c_evidence(
    artifact_dir: Path, *, planning_seoi_absolute: float = 0.10
) -> dict[str, Any]:
    smoke = _load_json(artifact_dir / "engineering_smoke" / "acceptance.json")
    smoke_repro = _load_json(
        artifact_dir / "engineering_smoke" / "reproducibility.json"
    )
    rows: list[list[dict[str, Any]]] = []
    runs: list[dict[str, Any]] = []
    for index in (1, 2):
        run_dir = artifact_dir / "repaired_calibration" / f"exact_run_{index}"
        current_rows = _load_jsonl(run_dir / "parsed_predictions.jsonl")
        rows.append(current_rows)
        recomputed = compute_stage0_metrics(
            current_rows,
            bootstrap_seed=20260906,
            bootstrap_resamples=2000,
            confidence_level=0.95,
        )
        stored = _load_json(run_dir / "metrics.json")
        if json.loads(json.dumps(recomputed)) != stored:
            raise RuntimeError(f"stored metrics do not recompute for exact run {index}")
        full = [
            row for row in current_rows if row["control_type"] == "FULL_INFORMATION"
        ]
        runs.append(
            {
                "run_id": f"exact_run_{index}",
                "manifest": _load_json(run_dir / "manifest.json"),
                "registered_metrics": recomputed,
                "component_by_condition_accuracy": _subgroup_accuracy(
                    full, ("component_type", "condition_id")
                ),
                "component_by_displayed_member_accuracy": _subgroup_accuracy(
                    full, ("component_type", "displayed_member")
                ),
                "component_headroom": component_headroom(
                    recomputed, planning_seoi_absolute=planning_seoi_absolute
                ),
                "artifact_sha256": {
                    name: sha256_file(run_dir / name)
                    for name in (
                        "manifest.json",
                        "observation_plan.json",
                        "raw_predictions.jsonl",
                        "parsed_predictions.jsonl",
                        "metrics.json",
                        "execution_failures.json",
                    )
                },
            }
        )
    return {
        "schema_version": 1,
        "checkpoint": "CHECKPOINT_C_REPAIRED_INSTRUMENT_AND_BASELINE_CEILING",
        "output_contract_status": "VALID_IN_REPAIRED_CALIBRATION",
        "gate_0_status": "NOT_RUN",
        "locked_validation_status": "BLOCKED",
        "stage_1a_status": "BLOCKED",
        "planning_seoi_absolute": planning_seoi_absolute,
        "engineering_smoke": {
            "acceptance": smoke,
            "reproducibility": smoke_repro,
        },
        "exact_repaired_calibration_reproducibility": compare_reproducibility(
            rows[0], rows[1]
        ),
        "runtime": _load_json(artifact_dir / "runtime.json"),
        "submission_manifest": _load_json(artifact_dir / "submission_manifest.json"),
        "runs": runs,
    }
