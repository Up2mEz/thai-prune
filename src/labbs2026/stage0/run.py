"""Fail-closed Stage 0 calibration runner; locked validation is not authorized."""

from __future__ import annotations

import json
import subprocess
import time
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


ENGINEERING_SMOKE_ROLE = "ENGINEERING_FORMAT_SMOKE_NOT_SCIENTIFIC_EVIDENCE"
REPAIRED_CALIBRATION_ROLE = "REGISTERED_REPAIRED_STAGE0_CALIBRATION"


def canonical_allocation_sha256(allocation: dict[str, Any]) -> str:
    """Hash only the frozen pair allocation contract, not YAML formatting."""

    import hashlib

    payload = {
        "strategy": allocation.get("strategy"),
        "allocation_seed": allocation.get("allocation_seed"),
        "calibration_pair_ids": allocation.get("calibration_pair_ids"),
        "locked_validation_pair_ids": allocation.get("locked_validation_pair_ids"),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
        if len(calibration_ids) != len(set(calibration_ids)) or len(validation_ids) != len(
            set(validation_ids)
        ):
            issues.append("PAIR_SPLIT_DUPLICATE_ID")
    expected_allocation_hash = allocation.get("sha256")
    if expected_allocation_hash != canonical_allocation_sha256(allocation):
        issues.append("ALLOCATION_HASH_MISMATCH")
    conditions = config.get("render_condition_selection", {}).get(
        "selected_condition_ids"
    )
    if not isinstance(conditions, list) or not conditions:
        issues.append("RENDER_CONDITIONS_NOT_FROZEN")
    blank_ids = config.get("controls", {}).get(
        "language_candidate_bias_blank_pair_ids"
    )
    if config.get("controls", {}).get("language_candidate_bias_blank_image") and (
        not isinstance(blank_ids, list) or not blank_ids
    ):
        issues.append("LANGUAGE_PRIOR_CONTROL_PAIR_IDS_NOT_FROZEN")
    if isinstance(blank_ids, list) and isinstance(calibration_ids, list):
        if set(blank_ids) != set(calibration_ids):
            issues.append("BLANK_CONTROL_IDS_MUST_EQUAL_CALIBRATION_IDS")
    if config.get("controls", {}).get("control_type") != "LANGUAGE_CANDIDATE_BIAS_BLANK":
        issues.append("BLANK_CONTROL_TYPE_MISMATCH")
    if config.get("gate_0", {}).get("criteria") is not None:
        issues.append("GATE0_CRITERIA_MUST_NOT_BE_SET_BEFORE_CALIBRATION")
    if config.get("locked_validation", {}).get("authorized") is not False:
        issues.append("LOCKED_VALIDATION_MUST_REMAIN_UNAUTHORIZED")
    if review is None:
        issues.append("HUMAN_REVIEW_RECORD_MISSING")
    else:
        if review.get("decision") != "APPROVED_FOR_CALIBRATION":
            issues.append("HUMAN_REVIEW_NOT_APPROVED")
        if review.get("approved_allocation_sha256") != expected_allocation_hash:
            issues.append("HUMAN_REVIEW_ALLOCATION_HASH_MISMATCH")
        if review.get("approved_inventory_sha256") != config.get(
            "candidate_inventory_sha256"
        ):
            issues.append("HUMAN_REVIEW_INVENTORY_HASH_MISMATCH")
        if review.get("approved_source_review_packet_sha256") != config.get(
            "source_review_packet_sha256"
        ):
            issues.append("HUMAN_REVIEW_SOURCE_PACKET_HASH_MISMATCH")
        approved_conditions = set(review.get("approved_condition_ids", []))
        if isinstance(conditions, list) and not set(conditions) <= approved_conditions:
            issues.append("CALIBRATION_CONTAINS_UNAPPROVED_CONDITION")
        if review.get("prompt_parser_approved") is not True:
            issues.append("PROMPT_PARSER_NOT_APPROVED")
        if review.get("authorized_scope") != "STAGE0_CALIBRATION_ONLY":
            issues.append("HUMAN_REVIEW_SCOPE_MISMATCH")
        if any(
            review.get(key) is not False
            for key in (
                "locked_validation_authorized",
                "gate_0_approval_granted",
                "stage_1a_authorized",
                "compression_authorized",
            )
        ):
            issues.append("LATER_STAGE_AUTHORIZATION_MUST_REMAIN_FALSE")
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
    blank_pairs = set(
        config["controls"]["language_candidate_bias_blank_pair_ids"]
    )
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
                "displayed_lexical_status": pair[f"lexical_status_{member}"],
                "candidate_a": choice.candidate_a,
                "candidate_b": choice.candidate_b,
                "candidate_a_lexical_status": pair[
                    "lexical_status_b" if choice.orientation == "B_THEN_A" else "lexical_status_a"
                ],
                "candidate_b_lexical_status": pair[
                    "lexical_status_a" if choice.orientation == "B_THEN_A" else "lexical_status_b"
                ],
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
    for pair_id in sorted(blank_pairs):
        pair = pair_by_id[pair_id]
        for orientation, candidate_a, candidate_b, status_a, status_b in (
            (
                "A_THEN_B",
                pair["text_a"],
                pair["text_b"],
                pair["lexical_status_a"],
                pair["lexical_status_b"],
            ),
            (
                "B_THEN_A",
                pair["text_b"],
                pair["text_a"],
                pair["lexical_status_b"],
                pair["lexical_status_a"],
            ),
        ):
            observations.append(
                {
                    "observation_id": f"blank_bias|{pair_id}|{orientation}",
                    "pair_id": pair_id,
                    "component_type": pair["component_type"],
                    "condition_id": "NO_VISUAL_CONTENT",
                    "displayed_member": None,
                    "displayed_text": None,
                    "displayed_lexical_status": None,
                    "candidate_a": candidate_a,
                    "candidate_b": candidate_b,
                    "candidate_a_lexical_status": status_a,
                    "candidate_b_lexical_status": status_b,
                    "expected_label": None,
                    "orientation": orientation,
                    "order_group_id": f"blank_bias|{pair_id}|{orientation}",
                    "prompt": prompt_template.format(
                        candidate_a=candidate_a, candidate_b=candidate_b
                    ),
                    "control_type": "LANGUAGE_CANDIDATE_BIAS_BLANK",
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


def compute_engineering_contract_metrics(
    rows: list[dict[str, Any]], *, planned_observation_count: int
) -> dict[str, Any]:
    """Report format/provenance checks without computing scientific accuracy."""

    completed = len(rows)
    conformance = sum(row.get("output_contract_conformance") is True for row in rows)
    parser_failures = sum(row.get("parse_status") != "PARSED" for row in rows)
    return {
        "scientific_use": "FORBIDDEN_ENGINEERING_SMOKE_ONLY",
        "visual_accuracy_computed": False,
        "planned_observation_count": planned_observation_count,
        "completed_observation_count": completed,
        "call_completion_rate": (
            completed / planned_observation_count if planned_observation_count else None
        ),
        "output_contract_conformance_count": conformance,
        "output_contract_conformance_rate": conformance / completed if completed else None,
        "parser_failure_count": parser_failures,
        "parser_failure_rate": parser_failures / completed if completed else None,
        "parsed_choice_counts": {
            label: sum(row.get("parsed_output") == label for row in rows)
            for label in ("A", "B")
        },
        "visual_token_count_distribution": {
            str(count): sum(row.get("llm_visual_token_count") == count for row in rows)
            for count in sorted(
                {
                    int(row["llm_visual_token_count"])
                    for row in rows
                    if row.get("llm_visual_token_count") is not None
                }
            )
        },
    }


def run_calibration(
    config_path: Path,
    dataset_review_dir: Path,
    model_config_path: Path,
    *,
    runtime: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    expected_git_sha: str | None = None,
    run_role: str = "REGISTERED_STAGE0_CALIBRATION",
    selected_pair_ids: set[str] | None = None,
    selected_condition_ids: set[str] | None = None,
    compute_scientific_metrics: bool = True,
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
    bundle_manifest = _load_json(dataset_review_dir / "bundle_manifest.json")
    calibration_ids = set(config["allocation"]["calibration_pair_ids"])
    locked_ids = set(config["allocation"]["locked_validation_pair_ids"])
    selected_conditions = set(
        config["render_condition_selection"]["selected_condition_ids"]
    )
    bundled_pair_ids = {pair["pair_id"] for pair in resolved_pairs}
    rendered_pair_ids = {row["pair_id"] for row in render_manifest}
    rendered_condition_ids = {row["condition_id"] for row in render_manifest}
    if bundled_pair_ids != calibration_ids or rendered_pair_ids != calibration_ids:
        raise RuntimeError("calibration bundle does not contain exactly calibration pair IDs")
    if rendered_condition_ids != selected_conditions:
        raise RuntimeError("calibration bundle does not contain exactly frozen conditions")
    if locked_ids & (bundled_pair_ids | rendered_pair_ids):
        raise RuntimeError("locked-validation pair IDs are present in the model input bundle")
    if bundle_manifest.get("source_review_packet_sha256") != config.get(
        "source_review_packet_sha256"
    ):
        raise RuntimeError("calibration bundle source review packet hash mismatch")
    prompt_config = _load_yaml(root / config["prompt_parser"])
    model_config = _load_yaml(model_config_path)
    observations = make_observation_plan(
        config, resolved_pairs, render_manifest, prompt_config["prompt_template"]
    )
    if selected_pair_ids is not None:
        unknown = selected_pair_ids - calibration_ids
        if unknown:
            raise RuntimeError(f"observation filter contains non-calibration pairs: {unknown}")
        observations = [row for row in observations if row["pair_id"] in selected_pair_ids]
    if selected_condition_ids is not None:
        unknown_conditions = selected_condition_ids - selected_conditions
        if unknown_conditions:
            raise RuntimeError(
                f"observation filter contains non-frozen conditions: {unknown_conditions}"
            )
        observations = [
            row
            for row in observations
            if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
            or row["condition_id"] in selected_condition_ids
        ]
    if not observations:
        raise RuntimeError("frozen calibration design produced no observations")

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    if expected_git_sha is not None and commit != expected_git_sha:
        raise RuntimeError(
            f"Git SHA mismatch: expected {expected_git_sha}, observed {commit}"
        )
    if output_dir is None:
        run_id = (
            f"stage0-calibration-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{commit[:8]}"
        )
        run_dir = root / "runs" / "stage0" / "calibration" / run_id
    else:
        run_dir = output_dir.resolve()
        run_id = run_dir.name
    run_dir.mkdir(parents=True, exist_ok=False)
    control_dir = run_dir / "controls"
    control_dir.mkdir()
    blank = Image.new("RGB", (448, 448), "white")
    blank.save(control_dir / "blank.png", format="PNG", optimize=False)
    seed_everything(int(config["reproducibility"]["seed"]))
    adapter = build_adapter(model_config, root, runtime)
    raw_rows: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    started = time.perf_counter()
    cuda_memory: dict[str, int | None] = {
        "allocated_after_model_load_bytes": None,
        "reserved_after_model_load_bytes": None,
        "peak_allocated_during_inference_bytes": None,
        "peak_reserved_during_inference_bytes": None,
    }
    architecture = adapter.architecture_record()
    expected_processor = model_config.get("expected_processor", {})
    for key, expected in expected_processor.items():
        if architecture.get(key) != expected:
            raise RuntimeError(
                f"processor contract mismatch for {key}: "
                f"expected {expected!r}, observed {architecture.get(key)!r}"
            )
    contract_records = [
        adapter.inspect_output_contract(observation["prompt"])
        for observation in observations
    ]
    expected_label_ids = (
        model_config.get("generation", {})
        .get("output_contract", {})
        .get("expected_label_token_ids")
    )
    if expected_label_ids is not None:
        expected_label_ids = {
            str(label): int(token_id) for label, token_id in expected_label_ids.items()
        }
        if any(record.get("label_token_ids") != expected_label_ids for record in contract_records):
            raise RuntimeError("runtime tokenizer label mapping differs from repair contract")
    output_contract_audit = {
        "verified_prompt_count": len(contract_records),
        "all_valid": all(record.get("valid") is True for record in contract_records),
        "label_token_ids": contract_records[0].get("label_token_ids"),
        "tokenizer_class": contract_records[0].get("tokenizer_class"),
        "tokenizer_name_or_path": contract_records[0].get("tokenizer_name_or_path"),
        "tokenizer_revision": contract_records[0].get("tokenizer_revision"),
        "contract_version": contract_records[0].get("contract_version"),
    }
    with peak_rss_monitor() as memory:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        _ = adapter.model
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            cuda_memory["allocated_after_model_load_bytes"] = int(
                torch.cuda.memory_allocated()
            )
            cuda_memory["reserved_after_model_load_bytes"] = int(
                torch.cuda.memory_reserved()
            )
            torch.cuda.reset_peak_memory_stats()
        for observation in observations:
            try:
                image_path = (
                    run_dir / observation["image_path"]
                    if observation["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
                    else dataset_review_dir / observation["image_path"]
                )
                result = adapter.predict(image_path, observation["prompt"])
                parsed, parse_status = parse_choice(result.raw_output)
                if (parsed, parse_status) != (result.parsed_output, result.parse_status):
                    raise RuntimeError("adapter and registered parser disagree")
                raw_rows.append(
                    {
                        "observation_id": observation["observation_id"],
                        "raw_output": result.raw_output,
                        "generated_token_ids": list(result.generated_token_ids),
                        "output_contract_conformance": result.output_contract_conformance,
                        "output_contract": result.output_contract,
                        "resolved_generation_config": result.resolved_generation_config,
                    }
                )
                parsed_rows.append(
                    {
                        **observation,
                        "raw_output": result.raw_output,
                        "parsed_output": parsed,
                        "parse_status": parse_status,
                        "generated_token_ids": list(result.generated_token_ids),
                        "output_contract_conformance": result.output_contract_conformance,
                        "output_contract": result.output_contract,
                        "resolved_generation_config": result.resolved_generation_config,
                        "is_correct": (
                            parsed == observation["expected_label"]
                            if parsed and observation["expected_label"] is not None
                            else None
                        ),
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
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            cuda_memory["peak_allocated_during_inference_bytes"] = int(
                torch.cuda.max_memory_allocated()
            )
            cuda_memory["peak_reserved_during_inference_bytes"] = int(
                torch.cuda.max_memory_reserved()
            )

    if compute_scientific_metrics:
        metrics = compute_stage0_metrics(
            parsed_rows,
            bootstrap_seed=int(config["reproducibility"]["seed"]),
            bootstrap_resamples=int(config["analysis"]["bootstrap_resamples"]),
            confidence_level=float(config["analysis"]["confidence_level"]),
        )
    else:
        metrics = compute_engineering_contract_metrics(
            parsed_rows, planned_observation_count=len(observations)
        )
    constrained_contract = expected_label_ids is not None
    contract_valid = not constrained_contract or all(
        row.get("output_contract_conformance") is True for row in parsed_rows
    )
    status = (
        "VALID"
        if not failures
        and len(parsed_rows) == len(observations)
        and contract_valid
        and all(row.get("parse_status") == "PARSED" for row in parsed_rows)
        else "INVALID"
    )
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "run_status": status,
        "run_role": run_role,
        "evidence_status": (
            "ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE"
            if not compute_scientific_metrics
            else "CALIBRATION_NOT_LOCKED"
        ),
        "compression_family": "FULL_INFORMATION",
        "git_commit": commit,
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": sha256_file(config_path),
        "model_config_path": model_config_path.relative_to(root).as_posix(),
        "model_config_sha256": sha256_file(model_config_path),
        "prompt_config_path": config["prompt_parser"],
        "prompt_config_sha256": sha256_file(root / config["prompt_parser"]),
        "calibration_input_bundle": config["calibration_input_bundle"],
        "calibration_input_bundle_sha256": config[
            "calibration_input_bundle_sha256"
        ],
        "dataset_review_dir": str(dataset_review_dir),
        "dataset_review_packet_sha256": sha256_file(dataset_review_dir / "review_packet.json"),
        "source_review_packet_sha256": config["source_review_packet_sha256"],
        "dataset_bundle_manifest_sha256": sha256_file(
            dataset_review_dir / "bundle_manifest.json"
        ),
        "allocation_sha256": config["allocation"]["sha256"],
        "model_id": adapter.model_id,
        "model_revision": adapter.revision,
        "processor_revision": adapter.processor_revision,
        "tokenizer_revision": adapter.tokenizer_revision,
        "seed": int(config["reproducibility"]["seed"]),
        "environment": environment_record(),
        "architecture": architecture,
        "output_contract_audit": output_contract_audit,
        "resolved_generation_config": architecture["generation"],
        "resolved_runtime": (runtime or {}).get("model_runtime", {}),
        "model_load_seconds": adapter.model_load_seconds,
        "total_seconds": time.perf_counter() - started,
        "peak_rss_bytes": memory["peak_rss_bytes"],
        "cuda_memory": cuda_memory,
        "observation_count": len(observations),
        "completed_prediction_count": len(parsed_rows),
        "failure_count": len(failures),
        "output_contract_failure_count": sum(
            row.get("output_contract_conformance") is not True for row in parsed_rows
        )
        if constrained_contract
        else None,
        "parser_failure_count": sum(
            row.get("parse_status") != "PARSED" for row in parsed_rows
        ),
        "locked_validation_pair_count_exposed_to_model": 0,
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
