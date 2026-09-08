"""Pre-registered Qwen3.5 measurement diagnostic on open calibration data only."""

from __future__ import annotations

import argparse
import gc
import json
import math
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import yaml
from PIL import Image, ImageChops

from labbs2026.adapters.factory import build_adapter, validate_model_config
from labbs2026.kaggle import (
    _check_remote_ref,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    cuda_preflight,
    load_runtime,
    parse_kaggle_status,
    render_worker,
    sha256_file,
    utc_now,
    write_failure,
)
from labbs2026.stage0.bundle import extract_and_verify_calibration_bundle
from labbs2026.stage0.kaggle_backend import _checksums
from labbs2026.stage0.margin_diagnostic import _cluster_bootstrap, _mean
from labbs2026.stage0.run import make_observation_plan
from labbs2026.step3 import environment_record, peak_rss_monitor, seed_everything


KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-qwen3-5-measurement-diagnostic",
    "title": "LabBS2026 Qwen3.5 Measurement Diagnostic",
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


def canonical_choice(label: str, orientation: str) -> str:
    if label not in {"A", "B"} or orientation not in {"A_THEN_B", "B_THEN_A"}:
        raise ValueError("invalid label/orientation")
    if orientation == "A_THEN_B":
        return "a" if label == "A" else "b"
    return "b" if label == "A" else "a"


def swapped_observation(row: dict[str, Any], template: str) -> dict[str, Any]:
    orientation = "B_THEN_A" if row["orientation"] == "A_THEN_B" else "A_THEN_B"
    expected = "B" if row["expected_label"] == "A" else "A"
    return {
        **row,
        "observation_id": row["observation_id"] + "|order=swapped",
        "candidate_a": row["candidate_b"],
        "candidate_b": row["candidate_a"],
        "candidate_a_lexical_status": row["candidate_b_lexical_status"],
        "candidate_b_lexical_status": row["candidate_a_lexical_status"],
        "orientation": orientation,
        "expected_label": expected,
        "prompt": template.format(candidate_a=row["candidate_b"], candidate_b=row["candidate_a"]),
        "candidate_order": "swapped",
    }


def rescue_image(source: Path, destination: Path, *, target_extent: int = 320) -> dict[str, Any]:
    image = Image.open(source).convert("RGB")
    background = Image.new("RGB", image.size, "white")
    bbox = ImageChops.difference(image, background).getbbox()
    if bbox is None:
        raise RuntimeError(f"no foreground content in {source}")
    left, top, right, bottom = bbox
    left, top = max(0, left - 8), max(0, top - 8)
    right, bottom = min(image.width, right + 8), min(image.height, bottom + 8)
    crop = image.crop((left, top, right, bottom))
    scale = target_extent / max(crop.size)
    size = tuple(max(1, round(value * scale)) for value in crop.size)
    enlarged = crop.resize(size, Image.Resampling.BICUBIC)
    rescued = Image.new("RGB", image.size, "white")
    origin = ((image.width - size[0]) // 2, (image.height - size[1]) // 2)
    rescued.paste(enlarged, origin)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rescued.save(destination, optimize=False)
    return {
        "source_bbox": [left, top, right, bottom],
        "source_crop_size": list(crop.size),
        "rescued_content_size": list(size),
        "canvas_size": list(image.size),
        "target_extent": target_extent,
        "resample": "BICUBIC",
    }


def signal_present(interval: dict[str, float | int], criteria: dict[str, Any]) -> bool:
    return (
        float(interval["estimate"]) >= float(criteria["signal_present_if_point_at_least"])
        and float(interval["ci_low"]) > float(criteria["signal_present_if_ci_low_above"])
    )


def classify_root_cause(
    d1_position_following: dict[str, float | int],
    d2_corrected_accuracy: dict[str, float | int],
    d3_retrieval_accuracy: dict[str, float | int],
    d4_rescue_gain: dict[str, float | int],
    criteria: dict[str, Any],
) -> dict[str, Any]:
    interface = float(d1_position_following["ci_low"]) >= float(
        criteria["position_following_interface_evidence_if_ci_low_at_least"]
    )
    d2_signal = signal_present(d2_corrected_accuracy, criteria)
    d3_signal = signal_present(d3_retrieval_accuracy, criteria)
    rescue = (
        float(d4_rescue_gain["estimate"]) >= float(criteria["rescue_gain_if_point_at_least"])
        and float(d4_rescue_gain["ci_low"]) > float(criteria["rescue_gain_if_ci_low_above"])
    )
    if interface and not d2_signal and rescue:
        root = "mixed"
    elif interface and (d2_signal or d3_signal):
        root = "measurement/interface"
    elif not interface and not d2_signal and not d3_signal and rescue:
        root = "visual representation"
    else:
        root = "inconclusive"
    return {
        "classification": root,
        "interface_evidence": interface,
        "d2_signal_present": d2_signal,
        "d3_signal_present": d3_signal,
        "d4_rescue_gain_present": rescue,
        "action": criteria["action_map"][root],
    }


def _tracked_tree_clean(root: Path) -> bool:
    unstaged = subprocess.run(["git", "diff", "--quiet"], cwd=root).returncode == 0
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode == 0
    return unstaged and staged


def diagnostic_preflight(root: Path, config_path: Path, runtime_path: Path) -> dict[str, Any]:
    root, config_path, runtime_path = root.resolve(), config_path.resolve(), runtime_path.resolve()
    config = _load_yaml(config_path)
    frozen = config["frozen_inputs"]
    runtime = load_runtime(runtime_path)
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    design = _load_yaml(root / frozen["calibration_design"])
    calibration = set(design["allocation"]["calibration_pair_ids"])
    locked = set(design["allocation"]["locked_validation_pair_ids"])
    remote_sha, remote_error = _check_remote_ref(
        root, runtime["source"]["repository_url"], runtime["source"]["remote_ref"]
    )
    checks = {
        "tracked_tree_clean": {"ok": _tracked_tree_clean(root), "git_sha": git_sha},
        "frozen_status": {"ok": config["status"] == "FROZEN_BEFORE_DIAGNOSTIC_OUTCOME"},
        "bundle_hash": {
            "ok": sha256_file(root / frozen["calibration_input_bundle"])
            == frozen["calibration_input_bundle_sha256"]
        },
        "pair_partition": {
            "ok": len(calibration) == len(locked) == 100 and not calibration & locked,
            "calibration_count": len(calibration), "locked_count": len(locked),
        },
        "model": {"ok": validate_model_config(_load_yaml(root / frozen["model_config"])) == "qwen35"},
        "prohibitions": {"ok": all(value is False for value in config["prohibitions"].values())},
        "remote_ref": {
            "ok": remote_error is None and remote_sha == git_sha,
            "remote_sha": remote_sha, "local_sha": git_sha, "error": remote_error,
        },
    }
    return {"schema_version": 1, "valid": all(item["ok"] for item in checks.values()), "checks": checks}


def make_spec(root: Path, config_path: Path, runtime_path: Path, git_sha: str) -> dict[str, Any]:
    config, runtime = _load_yaml(config_path), load_runtime(runtime_path)
    frozen = config["frozen_inputs"]
    design = _load_yaml(root / frozen["calibration_design"])
    paths = {
        "diagnostic_config_path": config_path.relative_to(root).as_posix(),
        "runtime_path": runtime_path.relative_to(root).as_posix(),
        "design_path": frozen["calibration_design"],
        "model_config_path": frozen["model_config"],
        "prompt_config_path": frozen["prompt_parser"],
        "bundle_path": frozen["calibration_input_bundle"],
        "protocol_path": frozen["protocol"],
        "override_lock_path": frozen["dependency_override_lock"],
        "worker_template_path": "infra/kaggle/qwen35_measurement_diagnostic_worker.py",
    }
    hashes = {key.replace("_path", "_sha256"): sha256_file(root / value) for key, value in paths.items()}
    return {
        "schema_version": 1,
        "run_type": "QWEN35_OPEN_CALIBRATION_MEASUREMENT_DIAGNOSTIC_D1_D4",
        "run_id": f"kaggle-qwen35-measurement-{git_sha[:12]}-{hashes['diagnostic_config_sha256'][:8]}",
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"], "git_sha": git_sha,
        **paths, **hashes,
        "bundle_sha256": frozen["calibration_input_bundle_sha256"],
        "allocation_sha256": frozen["pair_allocation_sha256"],
        "calibration_pair_ids": design["allocation"]["calibration_pair_ids"],
        "requested_accelerator": runtime["accelerator"],
        "environment_contract": runtime["evidence_environment_contract"],
        "source_dir": runtime["paths"]["source_dir"], "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "qwen35_override_lock": runtime["uv"]["qwen35_override_lock"],
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "kernel_id": KERNEL_METADATA["id"],
        "locked_validation_authorized": False, "compression_status": "NOT_RUN",
        "gate_0_status": "NOT_RUN", "created_at_utc": utc_now(),
    }


def prepare_staging(root: Path, config_path: Path, runtime_path: Path) -> dict[str, Any]:
    preflight = diagnostic_preflight(root, config_path, runtime_path)
    if not preflight["valid"]:
        raise RuntimeError("measurement diagnostic preflight failed")
    git_sha = preflight["checks"]["tracked_tree_clean"]["git_sha"]
    spec = make_spec(root, config_path, runtime_path, git_sha)
    run_dir, staging = root / "runs/kaggle" / spec["run_id"], None
    staging = run_dir / "staging"
    staging.mkdir(parents=True, exist_ok=False)
    template = root / spec["worker_template_path"]
    atomic_write_text(staging / "worker.py", render_worker(template.read_text("utf-8"), spec))
    metadata = dict(KERNEL_METADATA)
    atomic_write_json(staging / "kernel-metadata.json", metadata)
    spec["generated_worker_sha256"] = sha256_file(staging / "worker.py")
    atomic_write_json(run_dir / "submission.json", spec)
    atomic_write_json(run_dir / "preflight.json", preflight)
    return {"run_id": spec["run_id"], "run_dir": str(run_dir), "submit_command": build_submit_command(staging)}


def _ab_result(adapter: Any, image_path: Path, row: dict[str, Any], order: str) -> dict[str, Any]:
    result = adapter.predict_with_decision_logits(image_path, row["prompt"])
    prediction = result.prediction.parsed_output
    if prediction is None:
        raise RuntimeError("A/B diagnostic parser failure")
    return {
        "pair_id": row["pair_id"], "component_type": row["component_type"],
        "condition_id": row["condition_id"], "displayed_member": row["displayed_member"],
        "order": order, "orientation": row["orientation"], "expected_label": row["expected_label"],
        "prediction": prediction, "canonical_choice": canonical_choice(prediction, row["orientation"]),
        "correct": prediction == row["expected_label"], "logit_A": result.logit_a,
        "logit_B": result.logit_b, "visual_stage_metadata": asdict(result.prediction.metadata),
    }


def _score_row(adapter: Any, image_path: Path, prompt: str, pair: dict[str, Any], blank: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    a = adapter.score_candidate_sequence(image_path, prompt, pair["text_a"])
    b = adapter.score_candidate_sequence(image_path, prompt, pair["text_b"])
    corrected_a = a["sum_log_probability"] - blank["a"]["sum_log_probability"]
    corrected_b = b["sum_log_probability"] - blank["b"]["sum_log_probability"]
    mean_corrected_a = a["mean_log_probability"] - blank["a"]["mean_log_probability"]
    mean_corrected_b = b["mean_log_probability"] - blank["b"]["mean_log_probability"]
    displayed = meta["displayed_member"]
    return {
        **meta, "pair_id": pair["pair_id"], "component_type": pair["component_type"],
        "candidate_a": a, "candidate_b": b,
        "raw_choice": "a" if a["sum_log_probability"] >= b["sum_log_probability"] else "b",
        "corrected_choice": "a" if corrected_a >= corrected_b else "b",
        "mean_corrected_choice": "a" if mean_corrected_a >= mean_corrected_b else "b",
        "raw_correct": (a["sum_log_probability"] >= b["sum_log_probability"]) == (displayed == "a"),
        "corrected_correct": (corrected_a >= corrected_b) == (displayed == "a"),
        "mean_corrected_correct": (mean_corrected_a >= mean_corrected_b) == (displayed == "a"),
        "corrected_margin_a_minus_b": corrected_a - corrected_b,
        "mean_corrected_margin_a_minus_b": mean_corrected_a - mean_corrected_b,
    }


def execute_remote(spec_path: Path) -> None:
    spec, source = _load_json(spec_path), Path.cwd()
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    phase, started = "cuda_preflight", time.perf_counter()
    try:
        runtime = load_runtime(source / spec["runtime_path"])
        gpu = cuda_preflight(spec["requested_accelerator"])
        phase = "bundle_verification"
        input_dir = Path("/tmp/labbs2026-qwen35-measurement-input")
        bundle = extract_and_verify_calibration_bundle(source / spec["bundle_path"], input_dir, spec["bundle_sha256"])
        if bundle["allocation_sha256"] != spec["allocation_sha256"]:
            raise RuntimeError("allocation mismatch")
        config = _load_yaml(source / spec["diagnostic_config_path"])
        design = _load_yaml(source / spec["design_path"])
        prompt_template = _load_yaml(source / spec["prompt_config_path"])["prompt_template"]
        pairs = _load_json(input_dir / "resolved_pairs.json")
        renders = _load_json(input_dir / "render_manifest.json")
        observations = make_observation_plan(design, pairs, renders, prompt_template)
        full = [row for row in observations if row["control_type"] == "FULL_INFORMATION"]
        observed_ids = {row["pair_id"] for row in full}
        if len(full) != 800 or observed_ids != set(spec["calibration_pair_ids"]):
            raise RuntimeError("diagnostic plan is not the 100-pair open calibration split")
        model_config = _load_yaml(source / spec["model_config_path"])
        adapter = build_adapter(model_config, source, runtime)
        seed_everything(int(config["uncertainty"]["cluster_bootstrap_seed"]))
        blank_path = artifact_dir / "controls/blank.png"
        blank_path.parent.mkdir(parents=True)
        Image.new("RGB", (448, 448), "white").save(blank_path, optimize=False)
        transcription_prompt = config["diagnostics"]["D2_candidate_scoring"]["prompt"]
        pair_by_id = {row["pair_id"]: row for row in pairs if row["pair_id"] in observed_ids}
        failures: list[dict[str, Any]] = []
        with peak_rss_monitor() as memory:
            phase = "D1_position_swap"
            d1_rows = []
            for row in full:
                image_path = input_dir / row["image_path"]
                try:
                    original = {**row, "candidate_order": "registered"}
                    swapped = swapped_observation(row, prompt_template)
                    first = _ab_result(adapter, image_path, original, "registered")
                    second = _ab_result(adapter, image_path, swapped, "swapped")
                    d1_rows.append({
                        "pair_id": row["pair_id"], "component_type": row["component_type"],
                        "condition_id": row["condition_id"], "displayed_member": row["displayed_member"],
                        "registered": first, "swapped": second,
                        "content_consistent": first["canonical_choice"] == second["canonical_choice"],
                        "position_following": first["prediction"] == second["prediction"],
                        "registered_correct": first["correct"], "swapped_correct": second["correct"],
                    })
                except BaseException as exc:
                    failures.append({"phase": phase, "observation_id": row["observation_id"], "message": str(exc)[:1000]})
            _write_jsonl(artifact_dir / "D1_position_swap.jsonl", d1_rows)

            phase = "D2_candidate_scoring"
            blank_scores = {}
            for pair_id in sorted(observed_ids):
                pair = pair_by_id[pair_id]
                blank_scores[pair_id] = {
                    "a": adapter.score_candidate_sequence(blank_path, transcription_prompt, pair["text_a"]),
                    "b": adapter.score_candidate_sequence(blank_path, transcription_prompt, pair["text_b"]),
                }
            d2_rows = []
            for row in full:
                pair = pair_by_id[row["pair_id"]]
                try:
                    d2_rows.append(_score_row(
                        adapter, input_dir / row["image_path"], transcription_prompt, pair,
                        blank_scores[row["pair_id"]], {
                            "condition_id": row["condition_id"], "displayed_member": row["displayed_member"],
                            "image_path": row["image_path"],
                        },
                    ))
                except BaseException as exc:
                    failures.append({"phase": phase, "observation_id": row["observation_id"], "message": str(exc)[:1000]})
            _write_jsonl(artifact_dir / "D2_candidate_scoring.jsonl", d2_rows)
            atomic_write_json(artifact_dir / "D2_blank_scores.json", blank_scores)

            phase = "D3_representation"
            d3_rows = []
            import torch
            import torch.nn.functional as F
            by_pair: dict[str, list[dict[str, Any]]] = {}
            for row in full:
                by_pair.setdefault(row["pair_id"], []).append(row)
            for pair_id in sorted(by_pair):
                reps: dict[tuple[str, str], Any] = {}
                rows = by_pair[pair_id]
                for row in rows:
                    result = adapter.visual_representation(input_dir / row["image_path"], transcription_prompt)
                    reps[(row["condition_id"], row["displayed_member"])] = F.normalize(
                        result["representation"].flatten(), dim=0
                    )
                conditions = sorted({row["condition_id"] for row in rows})
                for condition in conditions:
                    for member in ("a", "b"):
                        other = "b" if member == "a" else "a"
                        train = [item for item in conditions if item != condition]
                        same_centroid = F.normalize(torch.stack([reps[(item, member)] for item in train]).mean(0), dim=0)
                        other_centroid = F.normalize(torch.stack([reps[(item, other)] for item in train]).mean(0), dim=0)
                        query = reps[(condition, member)]
                        same_sim = float(torch.dot(query, same_centroid).item())
                        other_sim = float(torch.dot(query, other_centroid).item())
                        d3_rows.append({
                            "pair_id": pair_id, "component_type": pair_by_id[pair_id]["component_type"],
                            "condition_id": condition, "displayed_member": member,
                            "same_member_similarity": same_sim, "other_member_similarity": other_sim,
                            "similarity_margin": same_sim - other_sim, "retrieval_correct": same_sim > other_sim,
                            "representation_shape": list(result["shape"]),
                        })
                del reps
                gc.collect()
            _write_jsonl(artifact_dir / "D3_representation.jsonl", d3_rows)

            phase = "D4_visual_rescue"
            source_condition = config["diagnostics"]["D4_visual_rescue"]["source_condition"]
            source_rows = [row for row in full if row["condition_id"] == source_condition]
            rescue_root = artifact_dir / "D4_rescue_images"
            d4_ab, d4_score, rescue_manifest = [], [], []
            for row in source_rows:
                rescued_path = rescue_root / f"{row['pair_id']}__{row['displayed_member']}.png"
                rescue_meta = rescue_image(input_dir / row["image_path"], rescued_path)
                rescue_manifest.append({"pair_id": row["pair_id"], "displayed_member": row["displayed_member"], **rescue_meta})
                original = {**row, "candidate_order": "registered", "condition_id": "VISUAL_RESCUE"}
                swapped = swapped_observation(original, prompt_template)
                first = _ab_result(adapter, rescued_path, original, "registered")
                second = _ab_result(adapter, rescued_path, swapped, "swapped")
                d4_ab.append({
                    "pair_id": row["pair_id"], "component_type": row["component_type"],
                    "displayed_member": row["displayed_member"], "registered": first, "swapped": second,
                    "content_consistent": first["canonical_choice"] == second["canonical_choice"],
                    "position_following": first["prediction"] == second["prediction"],
                })
                d4_score.append(_score_row(
                    adapter, rescued_path, transcription_prompt, pair_by_id[row["pair_id"]],
                    blank_scores[row["pair_id"]], {
                        "condition_id": "VISUAL_RESCUE", "displayed_member": row["displayed_member"],
                        "image_path": rescued_path.name,
                    },
                ))
            _write_jsonl(artifact_dir / "D4_rescue_ab.jsonl", d4_ab)
            _write_jsonl(artifact_dir / "D4_rescue_scoring.jsonl", d4_score)
            atomic_write_json(artifact_dir / "D4_rescue_manifest.json", rescue_manifest)

        if failures or len(d1_rows) != 800 or len(d2_rows) != 800 or len(d3_rows) != 800 or len(d4_score) != 200:
            atomic_write_json(artifact_dir / "execution_failures.json", failures)
            raise RuntimeError("D1-D4 execution was incomplete")
        atomic_write_json(artifact_dir / "execution_failures.json", failures)
        visual_counts = {
            item["registered"]["visual_stage_metadata"]["llm_visual_token_count"]
            for item in d1_rows + d4_ab
        }
        if visual_counts != {196}:
            raise RuntimeError(f"visual accounting changed: {visual_counts}")
        atomic_write_json(artifact_dir / "runtime.json", {
            "schema_version": 1, "run_id": spec["run_id"], "gpu_preflight": gpu,
            "environment": environment_record(), "frozen_environment_contract": spec["environment_contract"],
            "model_load_seconds": adapter.model_load_seconds, "peak_rss_bytes": memory["peak_rss_bytes"],
            "total_submission_seconds": time.perf_counter() - started,
        })
        atomic_write_json(artifact_dir / "submission_manifest.json", {
            "schema_version": 1, "run_id": spec["run_id"], "git_sha": spec["git_sha"],
            "run_status": "VALID_OPEN_CALIBRATION_MEASUREMENT_DIAGNOSTIC",
            "D1_rows": len(d1_rows), "D2_rows": len(d2_rows), "D3_rows": len(d3_rows),
            "D4_rows": len(d4_score), "locked_validation_pair_count_exposed_to_model": 0,
            "primary_metric_replaced": False, "compression_status": "NOT_RUN",
            "gate_0_status": "NOT_RUN", "visual_token_counts": sorted(visual_counts),
        })
        atomic_write_json(artifact_dir / "run_spec.json", spec)
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


def _interval(rows: list[dict[str, Any]], key: str, config: dict[str, Any]) -> dict[str, float | int]:
    uncertainty = config["uncertainty"]
    return _cluster_bootstrap(
        rows, _mean(key), seed=int(uncertainty["cluster_bootstrap_seed"]),
        resamples=int(uncertainty["cluster_bootstrap_resamples"]),
        confidence=float(uncertainty["confidence_level"]),
    )


def _paired_rescue_gain(base: list[dict[str, Any]], rescue: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, float | int]:
    base_by = {(row["pair_id"], row["displayed_member"]): row for row in base}
    contrasts = [{
        "pair_id": row["pair_id"],
        "gain": float(row["corrected_correct"]) - float(base_by[(row["pair_id"], row["displayed_member"])]["corrected_correct"]),
    } for row in rescue]
    return _interval(contrasts, "gain", config)


def analyze_artifacts(artifact_dir: Path, output_dir: Path, config_path: Path) -> dict[str, Any]:
    config = _load_yaml(config_path)
    d1, d2 = _jsonl(artifact_dir / "D1_position_swap.jsonl"), _jsonl(artifact_dir / "D2_candidate_scoring.jsonl")
    d3 = _jsonl(artifact_dir / "D3_representation.jsonl")
    d4_ab, d4_score = _jsonl(artifact_dir / "D4_rescue_ab.jsonl"), _jsonl(artifact_dir / "D4_rescue_scoring.jsonl")
    source_condition = config["diagnostics"]["D4_visual_rescue"]["source_condition"]
    d2_source = [row for row in d2 if row["condition_id"] == source_condition]
    summarize = lambda rows, keys: {key: _interval(rows, key, config) for key in keys}
    report = {
        "schema_version": 1, "evidence_status": "OPEN_CALIBRATION_MEASUREMENT_DIAGNOSTIC_ONLY",
        "independent_unit": "pair_id", "pair_count": 100, "locked_pair_count": 0,
        "D1": summarize(d1, ["content_consistent", "position_following", "registered_correct", "swapped_correct"]),
        "D2": summarize(d2, ["raw_correct", "corrected_correct", "mean_corrected_correct"]),
        "D3": summarize(d3, ["retrieval_correct", "similarity_margin"]),
        "D4": {
            **summarize(d4_ab, ["content_consistent", "position_following"]),
            **summarize(d4_score, ["raw_correct", "corrected_correct", "mean_corrected_correct"]),
            "corrected_accuracy_gain_vs_source": _paired_rescue_gain(d2_source, d4_score, config),
        },
        "per_component": {},
    }
    for component in sorted({row["component_type"] for row in d1}):
        subset = lambda rows: [row for row in rows if row["component_type"] == component]
        report["per_component"][component] = {
            "D1": summarize(subset(d1), ["content_consistent", "position_following"]),
            "D2": summarize(subset(d2), ["corrected_correct"]),
            "D3": summarize(subset(d3), ["retrieval_correct", "similarity_margin"]),
            "D4": {
                "corrected_correct": _interval(subset(d4_score), "corrected_correct", config),
                "gain_vs_source": _paired_rescue_gain(subset(d2_source), subset(d4_score), config),
            },
        }
    report["root_cause"] = classify_root_cause(
        report["D1"]["position_following"], report["D2"]["corrected_correct"],
        report["D3"]["retrieval_correct"], report["D4"]["corrected_accuracy_gain_vs_source"],
        config["decision_criteria"],
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(output_dir / "measurement_diagnostic_analysis.json", report)
    return report


def verify_artifacts(artifact_dir: Path, submission: dict[str, Any], kaggle_status: str) -> dict[str, Any]:
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
        record("D1_rows", manifest.get("D1_rows") == 800, manifest.get("D1_rows"))
        record("D2_rows", manifest.get("D2_rows") == 800, manifest.get("D2_rows"))
        record("D3_rows", manifest.get("D3_rows") == 800, manifest.get("D3_rows"))
        record("D4_rows", manifest.get("D4_rows") == 200, manifest.get("D4_rows"))
        record("locked_unexposed", manifest.get("locked_validation_pair_count_exposed_to_model") == 0)
        record("primary_metric_unchanged", manifest.get("primary_metric_replaced") is False)
        record("no_compression", manifest.get("compression_status") == "NOT_RUN")
        record("visual_count_unchanged", manifest.get("visual_token_counts") == [196])
    valid = bool(checks) and all(item["ok"] for item in checks.values())
    return {"schema_version": 1, "verification_status": "VERIFIED" if valid else "INVALID", "hard_checks": checks}


def query_status(kernel_id: str, root: Path) -> dict[str, Any]:
    result = subprocess.run(["kaggle", "kernels", "status", kernel_id], cwd=root, capture_output=True, text=True)
    return {"returncode": result.returncode, "status": parse_kaggle_status(result.stdout, result.stderr), "stdout": result.stdout, "stderr": result.stderr}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path)
    args = parser.parse_args()
    if args.remote_spec:
        execute_remote(args.remote_spec)
        return 0
    raise SystemExit("use scripts/stage0_qwen35_measurement_diagnostic.py")


if __name__ == "__main__":
    raise SystemExit(main())
