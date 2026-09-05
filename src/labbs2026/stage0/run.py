"""Fail-closed Stage 0 calibration runner; locked validation is not authorized."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from labbs2026.preflight import inspect_repository
from labbs2026.stage0.forced_choice import make_forced_choice, parse_choice
from labbs2026.stage0.metrics import compute_stage0_metrics
from labbs2026.step3 import (
    build_adapter,
    environment_record,
    peak_rss_monitor,
    seed_everything,
    sha256_file,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def calibration_readiness_issues(
    config: dict[str, Any], review: dict[str, Any] | None
) -> list[str]:
    issues: list[str] = []
    if config.get("status") != "FROZEN_CALIBRATION":
        issues.append("CALIBRATION_DESIGN_NOT_FROZEN")
    if config.get("compression_family") != "FULL_INFORMATION":
        issues.append("STAGE0_MUST_USE_FULL_information_ONLY".upper())
    allocation = config.get("allocation", {})
    calibration_ids = allocation.get("calibration_pair_ids")
    validation_ids = allocation.get("locked_validation_pair_ids")
    if not isinstance(calibration_ids, list) or not calibration_ids:
        issues.append("CALIBRATION_PAIR_IDS_NOT_FROZEN")
    if not isinstance(validation_ids, list) or not validation_ids:
        issues.append("LOCKED_VALIDATION_PAIR_IDS_NOT_FROZEN")
    if isinstance(calibration_ids, list) and isinstance(validation_ids, list):
        if set(calibration_ids) & set(validation_ids):
            issues.append("PAIR_SPLIT_OVERLAP")
    conditions = config.get("render_condition_selection", {}).get(
        "selected_condition_ids"
    )
    if not isinstance(conditions, list) or not conditions:
        issues.append("RENDER_CONDITIONS_NOT_FROZEN")
    blank_ids = config.get("controls", {}).get("language_prior_blank_pair_ids")
    if config.get("controls", {}).get("language_prior_blank_image") and (
        not isinstance(blank_ids, list) or not blank_ids
    ):
        issues.append("LANGUAGE_PRIOR_CONTROL_PAIR_IDS_NOT_FROZEN")
    if config.get("gate_0", {}).get("criteria") is not None:
        issues.append("GATE0_CRITERIA_MUST_NOT_BE_SET_BEFORE_CALIBRATION")
    if config.get("locked_validation", {}).get("authorized") is not False:
        issues.append("LOCKED_VALIDATION_MUST_REMAIN_UNAUTHORIZED")
    if review is None:
        issues.append("HUMAN_REVIEW_RECORD_MISSING")
    else:
        if review.get("decision") != "APPROVED_FOR_CALIBRATION":
            issues.append("HUMAN_REVIEW_NOT_APPROVED")
        approved_pairs = set(review.get("approved_pair_ids", []))
        if isinstance(calibration_ids, list) and not set(calibration_ids) <= approved_pairs:
            issues.append("CALIBRATION_CONTAINS_UNAPPROVED_PAIR")
        if isinstance(validation_ids, list) and not set(validation_ids) <= approved_pairs:
            issues.append("VALIDATION_CONTAINS_UNAPPROVED_PAIR")
        approved_conditions = set(review.get("approved_condition_ids", []))
        if isinstance(conditions, list) and not set(conditions) <= approved_conditions:
            issues.append("CALIBRATION_CONTAINS_UNAPPROVED_CONDITION")
        if review.get("prompt_parser_approved") is not True:
            issues.append("PROMPT_PARSER_NOT_APPROVED")
    return sorted(set(issues))


def make_observation_plan(
    config: dict[str, Any],
    resolved_pairs: list[dict[str, Any]],
    render_manifest: list[dict[str, Any]],
    prompt_template: str,
) -> list[dict[str, Any]]:
    pair_by_id = {pair["pair_id"]: pair for pair in resolved_pairs}
    selected_pairs = set(config["allocation"]["calibration_pair_ids"])
    selected_conditions = set(
        config["render_condition_selection"]["selected_condition_ids"]
    )
    blank_pairs = set(config["controls"]["language_prior_blank_pair_ids"])
    seed = int(config["reproducibility"]["seed"])
    observations: list[dict[str, Any]] = []
    for rendering in render_manifest:
        pair_id = rendering["pair_id"]
        condition_id = rendering["condition_id"]
        if pair_id not in selected_pairs or condition_id not in selected_conditions:
            continue
        pair = pair_by_id[pair_id]
        for member in ("a", "b"):
            choice = make_forced_choice(
                pair_id=pair_id,
                condition_id=condition_id,
                displayed_member=member,
                text_a=pair["text_a"],
                text_b=pair["text_b"],
                seed=seed,
                prompt_template=prompt_template,
            )
            base = {
                "pair_id": pair_id,
                "component_type": pair["component_type"],
                "condition_id": condition_id,
                "displayed_member": member,
                "displayed_text": pair[f"text_{member}"],
                "candidate_a": choice.candidate_a,
                "candidate_b": choice.candidate_b,
                "expected_label": choice.expected_label,
                "orientation": choice.orientation,
                "order_group_id": choice.order_group_id,
                "prompt": choice.prompt,
            }
            observations.append(
                {
                    **base,
                    "observation_id": f"full|{pair_id}|{condition_id}|{member}",
                    "control_type": "FULL_INFORMATION",
                    "image_path": rendering[f"image_{member}_path"],
                }
            )
            if pair_id in blank_pairs:
                observations.append(
                    {
                        **base,
                        "observation_id": f"blank|{pair_id}|{condition_id}|{member}",
                        "control_type": "LANGUAGE_PRIOR_BLANK",
                        "image_path": "controls/blank.png",
                    }
                )
    return observations


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_calibration(
    config_path: Path,
    dataset_review_dir: Path,
    model_config_path: Path,
) -> Path:
    root = Path(__file__).resolve().parents[3]
    preflight = inspect_repository(root)
    if not preflight.valid:
        raise RuntimeError(f"clean repository preflight required: {preflight}")
    config = _load_yaml(config_path)
    review_path_value = config.get("human_review_record")
    review = _load_json(root / review_path_value) if review_path_value else None
    issues = calibration_readiness_issues(config, review)
    if issues:
        raise RuntimeError("calibration preconditions failed: " + ", ".join(issues))

    resolved_pairs = _load_json(dataset_review_dir / "resolved_pairs.json")
    render_manifest = _load_json(dataset_review_dir / "render_manifest.json")
    prompt_config = _load_yaml(root / config["prompt_parser"])
    model_config = _load_yaml(model_config_path)
    observations = make_observation_plan(
        config, resolved_pairs, render_manifest, prompt_config["prompt_template"]
    )
    if not observations:
        raise RuntimeError("frozen calibration design produced no observations")

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    run_id = f"stage0-calibration-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{commit[:8]}"
    run_dir = root / "runs" / "stage0" / "calibration" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    control_dir = run_dir / "controls"
    control_dir.mkdir()
    blank = Image.new("RGB", (448, 448), "white")
    blank.save(control_dir / "blank.png", format="PNG", optimize=False)
    seed_everything(int(config["reproducibility"]["seed"]))
    adapter = build_adapter(model_config, root)
    raw_rows: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with peak_rss_monitor() as memory:
        for observation in observations:
            try:
                image_path = (
                    run_dir / observation["image_path"]
                    if observation["control_type"] == "LANGUAGE_PRIOR_BLANK"
                    else dataset_review_dir / observation["image_path"]
                )
                result = adapter.predict(image_path, observation["prompt"])
                parsed, parse_status = parse_choice(result.raw_output)
                raw_rows.append(
                    {
                        "observation_id": observation["observation_id"],
                        "raw_output": result.raw_output,
                    }
                )
                parsed_rows.append(
                    {
                        **observation,
                        "parsed_output": parsed,
                        "parse_status": parse_status,
                        "is_correct": parsed == observation["expected_label"] if parsed else False,
                        "llm_visual_token_count": result.metadata.llm_visual_token_count,
                        "visual_stage_metadata": asdict(result.metadata),
                        "preprocess_seconds": result.preprocess_seconds,
                        "generation_seconds": result.generation_seconds,
                    }
                )
            except BaseException as exc:
                failures.append(
                    {
                        "observation_id": observation["observation_id"],
                        "exception_type": type(exc).__name__,
                        "message": str(exc)[:1000],
                    }
                )

    metrics = compute_stage0_metrics(
        parsed_rows,
        bootstrap_seed=int(config["reproducibility"]["seed"]),
        bootstrap_resamples=int(config["analysis"]["bootstrap_resamples"]),
        confidence_level=float(config["analysis"]["confidence_level"]),
    )
    status = "VALID" if not failures and len(parsed_rows) == len(observations) else "INVALID"
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "run_status": status,
        "evidence_status": "CALIBRATION_NOT_LOCKED",
        "compression_family": "FULL_INFORMATION",
        "git_commit": commit,
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": sha256_file(config_path),
        "dataset_review_dir": str(dataset_review_dir),
        "dataset_review_packet_sha256": sha256_file(dataset_review_dir / "review_packet.json"),
        "model_id": adapter.model_id,
        "model_revision": adapter.revision,
        "processor_revision": adapter.processor_revision,
        "seed": int(config["reproducibility"]["seed"]),
        "environment": environment_record(),
        "peak_rss_bytes": memory["peak_rss_bytes"],
        "observation_count": len(observations),
        "completed_prediction_count": len(parsed_rows),
        "failure_count": len(failures),
    }
    _write_json(run_dir / "manifest.json", manifest)
    _write_json(run_dir / "resolved_config.json", config)
    _write_json(run_dir / "observation_plan.json", observations)
    _write_jsonl(run_dir / "raw_predictions.jsonl", raw_rows)
    _write_jsonl(run_dir / "parsed_predictions.jsonl", parsed_rows)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "execution_failures.json", failures)
    if status != "VALID":
        raise RuntimeError(f"calibration run is INVALID: {run_dir}")
    return run_dir
