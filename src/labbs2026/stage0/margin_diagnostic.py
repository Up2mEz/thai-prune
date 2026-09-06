"""Fail-closed Stage 0 image-gain/decision-margin diagnostic."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import random
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import yaml
from PIL import Image

from labbs2026.kaggle import (
    _check_remote_ref,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    cuda_preflight,
    load_runtime,
    locked_package_versions,
    parse_kaggle_status,
    render_worker,
    sha256_file,
    utc_now,
    write_failure,
)
from labbs2026.preflight import inspect_repository
from labbs2026.stage0.bundle import extract_and_verify_calibration_bundle
from labbs2026.stage0.kaggle_backend import _check_runtime_contract, _checksums, stage0_preflight
from labbs2026.stage0.run import make_observation_plan
from labbs2026.step3 import build_adapter, environment_record, peak_rss_monitor, seed_everything


KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-stage-0-margin-diagnostic",
    "title": "LabBS2026 Stage 0 Margin Diagnostic",
    "code_file": "worker.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": [],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _canonical_payload_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _binary_reference(rows: list[dict[str, Any]]) -> dict[str, str]:
    reference = {row["observation_id"]: row["parsed_output"] for row in rows}
    if len(reference) != 1000 or set(reference.values()) - {"A", "B"}:
        raise RuntimeError("binary reference must contain 1,000 unique exact A/B outputs")
    return reference


def diagnostic_preflight(root: Path, diagnostic_path: Path, runtime_path: Path) -> dict[str, Any]:
    root = root.resolve()
    diagnostic = _load_yaml(diagnostic_path)
    frozen = diagnostic["frozen_inputs"]
    model_path = root / frozen["model_config"]
    base = stage0_preflight(root, root / frozen["calibration_design"], runtime_path, model_path)
    checks = dict(base["checks"])
    expected_hashes = {
        frozen["calibration_input_bundle"]: frozen["calibration_input_bundle_sha256"],
        frozen["prompt_parser"]: frozen["prompt_parser_sha256"],
        frozen["model_config"]: frozen["model_config_sha256"],
        frozen["binary_reference_path"]: frozen["binary_reference_sha256"],
    }
    checks["frozen_input_hashes"] = {
        "ok": all(sha256_file(root / path) == expected for path, expected in expected_hashes.items()),
        "expected": expected_hashes,
        "observed": {path: sha256_file(root / path) for path in expected_hashes},
    }
    reference = _binary_reference(_jsonl(root / frozen["binary_reference_path"]))
    checks["binary_reference"] = {
        "ok": len(reference) == 1000,
        "observation_count": len(reference),
        "canonical_sha256": _canonical_payload_sha256(reference),
    }
    prohibitions = diagnostic["prohibitions"]
    checks["authorization"] = {
        "ok": diagnostic.get("status") == "FROZEN_CALIBRATION_MARGIN_DIAGNOSTIC_AUTHORIZED"
        and diagnostic.get("authorization_scope") == "ALREADY_EXPOSED_CALIBRATION_PAIRS_ONLY"
        and all(value is False for value in prohibitions.values()),
        "prohibitions": prohibitions,
    }
    smoke = diagnostic["engineering_smoke"]
    full = diagnostic["diagnostic"]
    checks["workload"] = {
        "ok": smoke.get("total_calls") == 40
        and smoke.get("observations_per_exact_run") == 20
        and smoke.get("exact_rerun_count") == 2
        and full.get("full_information_calls") == 800
        and full.get("matched_blank_calls") == 200
        and full.get("total_calls") == 1000
        and full.get("exact_run_count") == 1,
    }
    runtime = load_runtime(runtime_path)
    model = _load_yaml(model_path)
    checks["runtime_contract"] = {
        "ok": not _check_runtime_contract(runtime, model),
        "issues": _check_runtime_contract(runtime, model),
    }
    checks["kernel_metadata"] = {
        "ok": _load_json(root / "infra/kaggle/stage0-margin-diagnostic-kernel-metadata.json")
        == KERNEL_METADATA
    }
    checks["remote_ref"] = _check_remote_ref(root, runtime)
    valid = all(check.get("ok") is True for check in checks.values())
    return {"schema_version": 1, "valid": valid, "checks": checks}


def make_diagnostic_spec(
    root: Path, diagnostic_path: Path, runtime_path: Path, git_sha: str
) -> dict[str, Any]:
    diagnostic = _load_yaml(diagnostic_path)
    frozen = diagnostic["frozen_inputs"]
    runtime = load_runtime(runtime_path)
    paths = {
        "diagnostic_config_path": diagnostic_path.relative_to(root).as_posix(),
        "config_path": frozen["calibration_design"],
        "runtime_path": runtime_path.relative_to(root).as_posix(),
        "model_config_path": frozen["model_config"],
        "prompt_config_path": frozen["prompt_parser"],
        "bundle_path": frozen["calibration_input_bundle"],
    }
    hashes = {key.replace("_path", "_sha256"): sha256_file(root / value) for key, value in paths.items()}
    reference = _binary_reference(_jsonl(root / frozen["binary_reference_path"]))
    diagnostic_sha = hashes["diagnostic_config_sha256"]
    return {
        "schema_version": 1,
        "run_type": "STAGE0_CALIBRATION_MARGIN_DIAGNOSTIC",
        "run_id": f"kaggle-stage0-margin-{git_sha[:12]}-{diagnostic_sha[:8]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        **paths,
        **hashes,
        "bundle_sha256": frozen["calibration_input_bundle_sha256"],
        "allocation_sha256": frozen["pair_allocation_sha256"],
        "binary_reference_sha256": frozen["binary_reference_sha256"],
        "binary_reference_canonical_sha256": _canonical_payload_sha256(reference),
        "binary_reference": reference,
        "smoke": diagnostic["engineering_smoke"],
        "diagnostic": diagnostic["diagnostic"],
        "requested_accelerator": runtime["accelerator"],
        "environment_contract": runtime["evidence_environment_contract"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "worker_template_path": "infra/kaggle/stage0_margin_diagnostic_worker.py",
        "kernel_id": KERNEL_METADATA["id"],
        "locked_validation_authorized": False,
        "gate_0_status": "NOT_RUN",
        "stage_1a_status": "BLOCKED",
        "created_at_utc": utc_now(),
    }


def prepare_diagnostic_staging(root: Path, diagnostic_path: Path, runtime_path: Path) -> dict[str, Any]:
    preflight = diagnostic_preflight(root, diagnostic_path, runtime_path)
    if not preflight["valid"]:
        raise RuntimeError("Stage 0 margin diagnostic preflight failed")
    git_sha = preflight["checks"]["repository"]["git_commit"]
    spec = make_diagnostic_spec(root, diagnostic_path, runtime_path, git_sha)
    run_dir = root / "runs" / "kaggle" / spec["run_id"]
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / spec["worker_template_path"]
    spec["worker_template_sha256"] = sha256_file(template)
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    shutil.copyfile(
        root / "infra/kaggle/stage0-margin-diagnostic-kernel-metadata.json",
        staging / "kernel-metadata.json",
    )
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", preflight)
    return {
        "run_id": spec["run_id"], "run_dir": str(run_dir),
        "staging_dir": str(staging), "submit_command": build_submit_command(staging),
    }


def _position_margin(logit_a: float, logit_b: float) -> float:
    return logit_a - logit_b


def _canonical_margin(position_margin: float, orientation: str) -> float:
    if orientation == "A_THEN_B":
        return position_margin
    if orientation == "B_THEN_A":
        return -position_margin
    raise ValueError(f"unknown orientation: {orientation}")


def _correct_margin(position_margin: float, expected_label: str | None) -> float | None:
    if expected_label is None:
        return None
    if expected_label == "A":
        return position_margin
    if expected_label == "B":
        return -position_margin
    raise ValueError(f"unknown expected label: {expected_label}")


def _run_pass(
    *,
    spec: dict[str, Any],
    source: Path,
    input_dir: Path,
    runtime: dict[str, Any],
    output_dir: Path,
    observations: list[dict[str, Any]],
    render_by_key: dict[tuple[str, str], dict[str, Any]],
    verify_direct_forward: bool,
    role: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    controls = output_dir / "controls"
    controls.mkdir()
    Image.new("RGB", (448, 448), "white").save(controls / "blank.png", optimize=False)
    seed_everything(int(_load_yaml(source / spec["config_path"])["reproducibility"]["seed"]))
    adapter = build_adapter(_load_yaml(source / spec["model_config_path"]), source, runtime)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    cuda_memory: dict[str, int | None] = {
        "allocated_after_model_load_bytes": None,
        "reserved_after_model_load_bytes": None,
        "peak_allocated_during_inference_bytes": None,
        "peak_reserved_during_inference_bytes": None,
    }
    started = time.perf_counter()
    with peak_rss_monitor() as memory:
        import torch

        _ = adapter.model
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            cuda_memory["allocated_after_model_load_bytes"] = int(torch.cuda.memory_allocated())
            cuda_memory["reserved_after_model_load_bytes"] = int(torch.cuda.memory_reserved())
            torch.cuda.reset_peak_memory_stats()
        for observation in observations:
            try:
                image_path = (
                    controls / "blank.png"
                    if observation["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
                    else input_dir / observation["image_path"]
                )
                result = adapter.predict_with_decision_logits(
                    image_path, observation["prompt"], verify_direct_forward=verify_direct_forward
                )
                prediction = result.prediction
                margin = _position_margin(result.logit_a, result.logit_b)
                render = render_by_key.get((observation["pair_id"], observation["condition_id"]))
                row = {
                    **observation,
                    "font_id": render.get("font_id") if render else None,
                    "font_size": render.get("font_size") if render else None,
                    "logit_A": result.logit_a,
                    "logit_B": result.logit_b,
                    "position_margin": margin,
                    "canonical_member_margin": _canonical_margin(margin, observation["orientation"]),
                    "correct_margin": _correct_margin(margin, observation["expected_label"]),
                    "direct_forward_logit_A": result.direct_forward_logit_a,
                    "direct_forward_logit_B": result.direct_forward_logit_b,
                    "generate_direct_exact": result.generate_direct_exact,
                    "binary_prediction": prediction.parsed_output,
                    "binary_correct": (
                        prediction.parsed_output == observation["expected_label"]
                        if observation["expected_label"] is not None else None
                    ),
                    "binary_reference_prediction": spec["binary_reference"][observation["observation_id"]],
                    "binary_reference_agrees": prediction.parsed_output
                    == spec["binary_reference"][observation["observation_id"]],
                    "raw_output": prediction.raw_output,
                    "parse_status": prediction.parse_status,
                    "generated_token_ids": list(prediction.generated_token_ids),
                    "output_contract_conformance": prediction.output_contract_conformance,
                    "output_contract": prediction.output_contract,
                    "resolved_generation_config": prediction.resolved_generation_config,
                    "llm_visual_token_count": prediction.metadata.llm_visual_token_count,
                    "visual_stage_metadata": asdict(prediction.metadata),
                    "preprocess_seconds": prediction.preprocess_seconds,
                    "generation_seconds": prediction.generation_seconds,
                }
                if not all(math.isfinite(row[key]) for key in ("logit_A", "logit_B", "position_margin")):
                    raise RuntimeError("non-finite decision logit")
                rows.append(row)
            except BaseException as exc:
                failures.append({
                    "observation_id": observation["observation_id"],
                    "exception_type": type(exc).__name__, "message": str(exc)[:1000],
                })
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            cuda_memory["peak_allocated_during_inference_bytes"] = int(torch.cuda.max_memory_allocated())
            cuda_memory["peak_reserved_during_inference_bytes"] = int(torch.cuda.max_memory_reserved())
    architecture = adapter.architecture_record()
    manifest = {
        "schema_version": 1, "run_role": role,
        "evidence_status": "ENGINEERING_ONLY" if verify_direct_forward else "CALIBRATION_DIAGNOSTIC_ONLY",
        "run_status": "VALID" if len(rows) == len(observations) and not failures else "INVALID",
        "git_commit": spec["git_sha"], "model_id": adapter.model_id,
        "model_revision": adapter.revision, "processor_revision": adapter.processor_revision,
        "environment": environment_record(), "frozen_environment_contract": spec["environment_contract"],
        "architecture": architecture, "model_load_seconds": adapter.model_load_seconds,
        "observation_count": len(observations), "completed_count": len(rows),
        "failure_count": len(failures), "total_seconds": time.perf_counter() - started,
        "peak_rss_bytes": memory["peak_rss_bytes"], "cuda_memory": cuda_memory,
        "locked_validation_pair_count_exposed_to_model": 0,
        "primary_metric_replaced": False, "compression_family": "FULL_INFORMATION",
    }
    _write_jsonl(output_dir / "decision_margins.jsonl", rows)
    atomic_write_json(output_dir / "execution_failures.json", failures)
    atomic_write_json(output_dir / "manifest.json", manifest)
    if manifest["run_status"] != "VALID":
        raise RuntimeError(f"margin pass is invalid: {output_dir}")
    return output_dir


def _enrich_image_gain(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blanks = {
        (row["pair_id"], row["orientation"]): row
        for row in rows if row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK"
    }
    enriched: list[dict[str, Any]] = []
    for row in rows:
        if row["control_type"] != "FULL_INFORMATION":
            enriched.append({**row, "matched_blank_correct_margin": None, "image_gain": None})
            continue
        blank = blanks[(row["pair_id"], row["orientation"])]
        blank_correct = _correct_margin(blank["position_margin"], row["expected_label"])
        assert blank_correct is not None and row["correct_margin"] is not None
        enriched.append({
            **row,
            "matched_blank_observation_id": blank["observation_id"],
            "matched_blank_correct_margin": blank_correct,
            "matched_blank_canonical_member_margin": blank["canonical_member_margin"],
            "image_gain": row["correct_margin"] - blank_correct,
        })
    return enriched


def _smoke_acceptance(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> dict[str, Any]:
    by_first = {row["observation_id"]: row for row in first}
    by_second = {row["observation_id"]: row for row in second}
    same_ids = set(by_first) == set(by_second) and len(by_first) == 20
    paired = [(by_first[key], by_second[key]) for key in sorted(by_first)] if same_ids else []
    rows = first + second
    criteria = {
        "call_completion": len(rows) == 40,
        "exact_token_ids": all(row["output_contract"]["label_token_ids"] == {"A": 32, "B": 33} for row in rows),
        "generate_direct_logits_exact": all(row["generate_direct_exact"] is True for row in rows),
        "registered_binary_unchanged": all(row["binary_reference_agrees"] is True for row in rows),
        "binary_argmax_matches_generation": all(
            row["binary_prediction"] == ("A" if row["logit_A"] >= row["logit_B"] else "B") for row in rows
        ),
        "deterministic_margin_reproducibility": bool(paired) and all(
            a["logit_A"] == b["logit_A"] and a["logit_B"] == b["logit_B"]
            and a["binary_prediction"] == b["binary_prediction"] for a, b in paired
        ),
        "frozen_visual_tokens": all(row["llm_visual_token_count"] == 256 for row in rows),
    }
    return {
        "schema_version": 1, "status": "PASS" if all(criteria.values()) else "FAIL",
        "scientific_use": "FORBIDDEN_ENGINEERING_SMOKE_ONLY", "criteria": criteria,
        "completed_calls": len(rows), "planned_calls": 40,
    }


def execute_remote_diagnostic(spec_path: Path) -> None:
    spec = _load_json(spec_path)
    source = Path.cwd()
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    phase = "cuda_preflight"
    started = time.perf_counter()
    try:
        runtime = load_runtime(source / spec["runtime_path"])
        gpu = cuda_preflight(spec["requested_accelerator"])
        phase = "bundle_verification"
        input_dir = Path("/tmp/labbs2026-stage0-margin-input")
        bundle = extract_and_verify_calibration_bundle(source / spec["bundle_path"], input_dir, spec["bundle_sha256"])
        if bundle["allocation_sha256"] != spec["allocation_sha256"]:
            raise RuntimeError("bundle allocation differs from frozen calibration")
        config = _load_yaml(source / spec["config_path"])
        prompt = _load_yaml(source / spec["prompt_config_path"])["prompt_template"]
        resolved_pairs = _load_json(input_dir / "resolved_pairs.json")
        render_manifest = _load_json(input_dir / "render_manifest.json")
        observations = make_observation_plan(config, resolved_pairs, render_manifest, prompt)
        if len(observations) != 1000 or len({row["pair_id"] for row in observations}) != 100:
            raise RuntimeError("diagnostic must use exactly the exposed 100-pair calibration plan")
        if set(spec["binary_reference"]) != {row["observation_id"] for row in observations}:
            raise RuntimeError("binary reference IDs differ from frozen observation plan")
        render_by_key = {(row["pair_id"], row["condition_id"]): row for row in render_manifest}
        smoke = spec["smoke"]
        smoke_obs = [
            row for row in observations
            if row["pair_id"] in set(smoke["pair_ids"])
            and (row["control_type"] == "LANGUAGE_CANDIDATE_BIAS_BLANK" or row["condition_id"] == smoke["condition_id"])
        ]
        if len(smoke_obs) != 20:
            raise RuntimeError("engineering smoke plan must contain exactly 20 observations")
        phase = "engineering_margin_smoke"
        smoke_root = artifact_dir / "engineering_smoke"
        smoke_runs = []
        for index in (1, 2):
            run = _run_pass(
                spec=spec, source=source, input_dir=input_dir, runtime=runtime,
                output_dir=smoke_root / f"exact_run_{index}", observations=smoke_obs,
                render_by_key=render_by_key, verify_direct_forward=True,
                role="ENGINEERING_MARGIN_SMOKE_NOT_SCIENTIFIC_EVIDENCE",
            )
            smoke_runs.append(_jsonl(run / "decision_margins.jsonl"))
            gc.collect()
            import torch
            torch.cuda.empty_cache()
        acceptance = _smoke_acceptance(smoke_runs[0], smoke_runs[1])
        atomic_write_json(smoke_root / "acceptance.json", acceptance)
        if acceptance["status"] != "PASS":
            raise RuntimeError("engineering margin smoke failed; diagnostic was not started")
        phase = "calibration_margin_diagnostic"
        diagnostic_dir = _run_pass(
            spec=spec, source=source, input_dir=input_dir, runtime=runtime,
            output_dir=artifact_dir / "calibration_diagnostic", observations=observations,
            render_by_key=render_by_key, verify_direct_forward=False,
            role="STAGE0_CALIBRATION_MARGIN_DIAGNOSTIC_ONLY",
        )
        enriched = _enrich_image_gain(_jsonl(diagnostic_dir / "decision_margins.jsonl"))
        _write_jsonl(diagnostic_dir / "image_gain_records.jsonl", enriched)
        if not all(row["binary_reference_agrees"] for row in enriched):
            raise RuntimeError("registered binary predictions changed in diagnostic pass")
        atomic_write_json(artifact_dir / "runtime.json", {
            "schema_version": 1, "run_id": spec["run_id"], "gpu_preflight": gpu,
            "environment": environment_record(), "frozen_environment_contract": spec["environment_contract"],
            "total_submission_seconds": time.perf_counter() - started,
        })
        atomic_write_json(artifact_dir / "submission_manifest.json", {
            "schema_version": 1, "run_id": spec["run_id"],
            "run_status": "VALID_CALIBRATION_MARGIN_DIAGNOSTIC",
            "git_sha": spec["git_sha"], "diagnostic_config_sha256": spec["diagnostic_config_sha256"],
            "engineering_smoke_status": "PASS", "engineering_smoke_calls": 40,
            "calibration_diagnostic_calls": 1000,
            "locked_validation_pair_count_exposed_to_model": 0,
            "primary_metric_replaced": False, "gate_0_status": "NOT_RUN",
            "stage_1a_status": "BLOCKED", "compression_status": "NOT_RUN",
        })
        atomic_write_text(artifact_dir / "checksums.sha256", _checksums(artifact_dir))
        atomic_write_json(artifact_dir / "SUCCESS.json", {
            "schema_version": 1, "run_id": spec["run_id"],
            "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
        })
    except BaseException as exc:
        write_failure(artifact_dir, spec["run_id"], phase, exc)
        if (artifact_dir / "SUCCESS.json").exists():
            (artifact_dir / "SUCCESS.json").unlink()
        raise


def _cluster_bootstrap(
    rows: list[dict[str, Any]], statistic: Callable[[list[dict[str, Any]]], float],
    *, seed: int, resamples: int, confidence: float,
) -> dict[str, float | int]:
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(row["pair_id"], []).append(row)
    pair_ids = sorted(by_pair)
    point = statistic(rows)
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        sampled: list[dict[str, Any]] = []
        for draw, pair_id in enumerate(rng.choices(pair_ids, k=len(pair_ids))):
            sampled.extend({**row, "_bootstrap_cluster": f"{draw}:{pair_id}"} for row in by_pair[pair_id])
        values.append(statistic(sampled))
    values.sort()
    alpha = (1.0 - confidence) / 2.0
    low = values[max(0, int(alpha * resamples))]
    high = values[min(resamples - 1, int((1.0 - alpha) * resamples) - 1)]
    return {"estimate": point, "ci_low": low, "ci_high": high, "pair_count": len(pair_ids)}


def _mean(key: str) -> Callable[[list[dict[str, Any]]], float]:
    return lambda rows: sum(float(row[key]) for row in rows) / len(rows)


def analyze_margin_artifacts(artifact_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _jsonl(artifact_dir / "calibration_diagnostic" / "image_gain_records.jsonl")
    full = [row for row in rows if row["control_type"] == "FULL_INFORMATION"]
    if len(full) != 800 or len(rows) != 1000:
        raise RuntimeError("unexpected diagnostic artifact grain")
    seed, resamples, confidence = 20260906, 2000, 0.95
    components = sorted({row["component_type"] for row in full})
    overall = {
        key: _cluster_bootstrap(full, _mean(key), seed=seed, resamples=resamples, confidence=confidence)
        for key in ("correct_margin", "matched_blank_correct_margin", "image_gain")
    }
    per_component: dict[str, Any] = {}
    condition_rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    for component in components:
        subset = [row for row in full if row["component_type"] == component]
        per_component[component] = {
            key: _cluster_bootstrap(subset, _mean(key), seed=seed, resamples=resamples, confidence=confidence)
            for key in ("correct_margin", "matched_blank_correct_margin", "image_gain")
        }
        per_component[component]["accuracy"] = _cluster_bootstrap(
            subset, lambda x: sum(bool(row["binary_correct"]) for row in x) / len(x),
            seed=seed, resamples=resamples, confidence=confidence,
        )
        for font_id in sorted({row["font_id"] for row in subset}):
            for font_size in sorted({int(row["font_size"]) for row in subset}):
                condition = [row for row in subset if row["font_id"] == font_id and int(row["font_size"]) == font_size]
                condition_rows.append({
                    "component": component, "font_id": font_id, "font_size": font_size,
                    "accuracy": _cluster_bootstrap(
                        condition, lambda x: sum(bool(row["binary_correct"]) for row in x) / len(x),
                        seed=seed, resamples=resamples, confidence=confidence,
                    ),
                    "image_gain": _cluster_bootstrap(
                        condition, _mean("image_gain"), seed=seed, resamples=resamples, confidence=confidence,
                    ),
                })
        for member in ("a", "b"):
            member_subset = [row for row in subset if row["displayed_member"] == member]
            member_rows.append({
                "component": component, "displayed_canonical_member": member,
                "correct_margin": _cluster_bootstrap(member_subset, _mean("correct_margin"), seed=seed, resamples=resamples, confidence=confidence),
                "image_gain": _cluster_bootstrap(member_subset, _mean("image_gain"), seed=seed, resamples=resamples, confidence=confidence),
            })
    pair_rows = []
    for pair_id in sorted({row["pair_id"] for row in full}):
        subset = [row for row in full if row["pair_id"] == pair_id]
        pair_rows.append({
            "pair_id": pair_id, "component": subset[0]["component_type"],
            "accuracy": sum(bool(row["binary_correct"]) for row in subset) / len(subset),
            "mean_correct_margin": sum(row["correct_margin"] for row in subset) / len(subset),
            "mean_blank_correct_margin": sum(row["matched_blank_correct_margin"] for row in subset) / len(subset),
            "mean_image_gain": sum(row["image_gain"] for row in subset) / len(subset),
        })
    report = {
        "schema_version": 1,
        "evidence_status": "CALIBRATION_DIAGNOSTIC_ONLY_NOT_PRIMARY_METRIC",
        "independent_unit": "pair_id", "pair_count": 100,
        "exact_reruns_pooled": False, "locked_pair_count": 0,
        "overall": overall, "per_component": per_component,
        "condition_results": condition_rows, "canonical_member_results": member_rows,
        "binary_reference_agreement_rate": sum(row["binary_reference_agrees"] for row in rows) / len(rows),
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(output_dir / "margin_analysis.json", report)
    atomic_write_json(output_dir / "pair_margin_diagnostics.json", pair_rows)
    return report


def verify_diagnostic_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    def record(name: str, ok: bool, observed: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "observed": observed}
    record("kaggle_status", kaggle_status == "COMPLETE", kaggle_status)
    record("failure_absent", not (artifact_dir / "FAILURE.json").exists())
    record("success_marker", (artifact_dir / "SUCCESS.json").is_file())
    if (artifact_dir / "SUCCESS.json").is_file():
        checksum_ok = True
        for line in (artifact_dir / "checksums.sha256").read_text("utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            target = artifact_dir / relative
            checksum_ok = checksum_ok and target.is_file() and sha256_file(target) == expected
        record("artifact_checksums", checksum_ok)
        manifest = _load_json(artifact_dir / "submission_manifest.json")
        record("git_sha", manifest.get("git_sha") == submission["git_sha"])
        record("smoke_pass", _load_json(artifact_dir / "engineering_smoke" / "acceptance.json").get("status") == "PASS")
        diagnostic_rows = _jsonl(artifact_dir / "calibration_diagnostic" / "image_gain_records.jsonl")
        record("diagnostic_call_count", len(diagnostic_rows) == 1000, len(diagnostic_rows))
        record("binary_invariance", all(row.get("binary_reference_agrees") is True for row in diagnostic_rows))
        record("locked_unexposed", manifest.get("locked_validation_pair_count_exposed_to_model") == 0)
        record("primary_metric_unchanged", manifest.get("primary_metric_replaced") is False)
        record("no_compression", manifest.get("compression_status") == "NOT_RUN")
    valid = bool(checks) and all(item["ok"] for item in checks.values())
    return {"schema_version": 1, "verification_status": "VERIFIED" if valid else "INVALID", "hard_checks": checks}


def query_kaggle_status(kernel_id: str, root: Path) -> dict[str, Any]:
    result = subprocess.run(["kaggle", "kernels", "status", kernel_id], cwd=root, capture_output=True, text=True)
    raw = (result.stdout or result.stderr).strip()
    return {"returncode": result.returncode, "status": parse_kaggle_status(raw), "raw_output": raw}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    execute_remote_diagnostic(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
