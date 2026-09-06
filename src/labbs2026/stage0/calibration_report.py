"""Audit a completed Stage 0 calibration without changing registered parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from labbs2026.stage0.metrics import compare_reproducibility, compute_stage0_metrics
from labbs2026.step3 import sha256_file


LEADING_LABEL_PATTERN = re.compile(r"^\s*([AB])(?:\.|\s|$)", re.IGNORECASE)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _diagnostic_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transformed: list[dict[str, Any]] = []
    for row in rows:
        match = LEADING_LABEL_PATTERN.match(row["raw_output"])
        label = match.group(1).upper() if match else None
        transformed.append(
            {
                **row,
                "parsed_output": label,
                "parse_status": "PARSED" if label else "PARSER_FAILURE",
                "is_correct": (
                    label == row["expected_label"]
                    if label is not None and row["expected_label"] is not None
                    else None
                ),
            }
        )
    return transformed


def _raw_format_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact_ab = 0
    leading_label = 0
    label_only = 0
    exact_candidate_echo = 0
    for row in rows:
        raw = row["raw_output"].strip()
        if re.fullmatch(r"[AB]", raw, re.IGNORECASE):
            exact_ab += 1
        match = re.fullmatch(r"([AB])(?:\.\s*(.*))?", raw, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        leading_label += 1
        echo = match.group(2)
        if echo in (None, ""):
            label_only += 1
        label = match.group(1).upper()
        selected = row["candidate_a"] if label == "A" else row["candidate_b"]
        if echo == selected:
            exact_candidate_echo += 1
    count = len(rows)
    return {
        "observation_count": count,
        "registered_exact_ab_count": exact_ab,
        "registered_exact_ab_rate": exact_ab / count if count else None,
        "leading_label_shape_count": leading_label,
        "leading_label_shape_rate": leading_label / count if count else None,
        "label_only_count": label_only,
        "exact_selected_candidate_echo_count": exact_candidate_echo,
    }


def build_calibration_evidence(artifact_dir: Path) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    row_sets: list[list[dict[str, Any]]] = []
    for index in (1, 2):
        run_dir = artifact_dir / f"exact_run_{index}"
        rows = _load_jsonl(run_dir / "parsed_predictions.jsonl")
        row_sets.append(rows)
        diagnostic = compute_stage0_metrics(
            _diagnostic_rows(rows),
            bootstrap_seed=20260906,
            bootstrap_resamples=2000,
            confidence_level=0.95,
        )
        runs.append(
            {
                "run_id": f"exact_run_{index}",
                "manifest": _load_json(run_dir / "manifest.json"),
                "registered_metrics": _load_json(run_dir / "metrics.json"),
                "raw_output_format_audit": _raw_format_audit(rows),
                "posthoc_leading_label_diagnostic": {
                    "status": "UNREGISTERED_POSTHOC_DIAGNOSTIC_DO_NOT_USE_FOR_GATE0",
                    "pattern": LEADING_LABEL_PATTERN.pattern,
                    "metrics": diagnostic,
                },
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
    failure = _load_json(artifact_dir / "FAILURE.json")
    return {
        "schema_version": 1,
        "checkpoint": "STAGE0_CALIBRATION_HUMAN_REVIEW",
        "calibration_instrument_status": "INVALID_REGISTERED_PARSER_COLLAPSE",
        "gate_0_status": "NOT_RUN",
        "locked_validation_status": "BLOCKED",
        "stage_1a_status": "BLOCKED",
        "submission_level_status": "ERROR_AFTER_BOTH_EXACT_RUNS_COMPLETED",
        "submission_failure": failure,
        "exact_rerun_agreement": compare_reproducibility(row_sets[0], row_sets[1]),
        "runs": runs,
    }
