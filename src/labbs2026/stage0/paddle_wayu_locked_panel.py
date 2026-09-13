"""Fail-closed execution for the authorized frozen one-shot locked panel."""

from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from labbs2026.kaggle import atomic_write_json, atomic_write_text, cuda_preflight, sha256_file, utc_now
from labbs2026.stage0.locked_panel_bundle import verify_locked_source_bundle
from labbs2026.stage0.paddle_wayu_smoke import (
    _environment,
    _jsonable,
    _loading_info_safe,
    _model_artifact_manifest,
    _validate_loading_info,
)
from labbs2026.stage0.resolution_pipeline import materialize_budget_image


FROZEN_DESIGN_SHA = "871996221a36a56a401fa040c239f55768561210"
FROZEN_DESIGN_FILE_SHA256 = "6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1"
FROZEN_PIPELINE_FILE_SHA256 = "8aea843de4ed3785ebfc016fff0ed3226ce9653497c9a46991d0ec4d8fc21ac6"
EXPECTED_CALLS = 6400


def _recursive_checksums(artifact_dir: Path) -> str:
    paths = sorted(
        (
            path for path in artifact_dir.rglob("*")
            if path.is_file() and path.name not in {"checksums.sha256", "SUCCESS.json"}
        ),
        key=lambda path: path.relative_to(artifact_dir).as_posix(),
    )
    return "".join(
        f"{sha256_file(path)}  {path.relative_to(artifact_dir).as_posix()}\n"
        for path in paths
    )


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _jsonl_append(handle: Any, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    handle.flush()


def _safe_call_id(row: dict[str, Any]) -> str:
    fields = (
        row["model_role"], row["pair_id"], row["condition_id"],
        row["member"], row["budget_id"],
    )
    return hashlib.sha256("|".join(fields).encode("utf-8")).hexdigest()


def build_workload(
    design: dict[str, Any],
    allocation: dict[str, Any],
    pairs: list[dict[str, Any]],
    renders: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    locked = list(allocation["allocation"]["locked_validation_pair_ids"])
    pair_by_id = {row["pair_id"]: row for row in pairs}
    render_by_key = {(row["pair_id"], row["condition_id"]): row for row in renders}
    condition_ids = list(design["dataset"]["render_conditions"])
    calls: list[dict[str, Any]] = []
    for model in design["models"]:
        for pair_id in locked:
            pair = pair_by_id[pair_id]
            for condition_id in condition_ids:
                render = render_by_key[(pair_id, condition_id)]
                for member in design["dataset"]["members"]:
                    other = "b" if member == "a" else "a"
                    source_key = f"image_{member}_path"
                    for budget in design["intervention"]["budgets"]:
                        row = {
                            "call_index": len(calls) + 1,
                            "model_role": model["role"],
                            "model_id": model["model_id"],
                            "revision": model["revision"],
                            "pair_id": pair_id,
                            "component_type": pair["component_type"],
                            "member": member,
                            "target": pair[f"text_{member}"],
                            "opposite_member": pair[f"text_{other}"],
                            "condition_id": condition_id,
                            "font_id": render["font_id"],
                            "font_size": int(render["font_size"]),
                            "source_zip_path": render[source_key],
                            "source_image_sha256": render[f"image_{member}_sha256"],
                            "budget_id": budget["budget_id"],
                            "input_resolution": budget["input_resolution"],
                            "min_pixels": budget["min_pixels"],
                            "max_pixels": budget["max_pixels"],
                            "expected_image_grid_thw": budget["image_grid_thw"],
                            "expected_pre_merge": budget["pre_merge_patches"],
                            "expected_llm_placeholders": budget["llm_image_placeholders"],
                            "prompt": design["prompt"],
                        }
                        row["call_id"] = _safe_call_id(row)
                        calls.append(row)
    if len(calls) != EXPECTED_CALLS or len({row["call_id"] for row in calls}) != EXPECTED_CALLS:
        raise RuntimeError("workload is not exactly 6,400 unique calls")
    counts = Counter(row["component_type"] for row in {row["pair_id"]: row for row in calls}.values())
    if len(locked) != 100 or set(counts.values()) != {20}:
        raise RuntimeError("locked pair/component allocation mismatch")
    if Counter(row["model_role"] for row in calls) != {"BASE": 3200, "SPECIALIZED": 3200}:
        raise RuntimeError("per-model call count mismatch")
    if set(Counter(row["budget_id"] for row in calls).values()) != {1600}:
        raise RuntimeError("per-budget call count mismatch")
    return calls


def _extract_sources(bundle: Path, destination: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(bundle) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError("unsafe locked bundle path")
        archive.extractall(destination)
    pairs = json.loads((destination / "resolved_pairs.json").read_text("utf-8"))
    renders = json.loads((destination / "render_manifest.json").read_text("utf-8"))
    return pairs, renders


def materialize_stimuli(
    workload: list[dict[str, Any]], source_root: Path, output_root: Path
) -> tuple[dict[tuple[str, str], Path], list[dict[str, Any]]]:
    images: dict[tuple[str, str], Path] = {}
    records = []
    unique = {
        (row["source_zip_path"], row["source_image_sha256"], row["budget_id"], tuple(row["input_resolution"]))
        for row in workload
    }
    for source_relative, source_sha, budget_id, size in sorted(unique):
        source = source_root / source_relative
        if sha256_file(source) != source_sha:
            raise RuntimeError("unexpected source image hash mismatch")
        output = output_root / budget_id / source_relative
        record = materialize_budget_image(source, output, size)
        if record["source_file_sha256"] != source_sha:
            raise RuntimeError("resize source provenance mismatch")
        record.update({
            "budget_id": budget_id,
            "source_zip_path": source_relative,
            "output_relative_path": output.relative_to(output_root.parent).as_posix(),
        })
        record.pop("source_path", None)
        record.pop("output_path", None)
        images[(source_relative, budget_id)] = output
        records.append(record)
    if len(records) != 3200:
        raise RuntimeError("expected 3,200 unique materialized stimuli")
    return images, records


def _run_model(
    model_spec: dict[str, Any],
    design: dict[str, Any],
    workload: list[dict[str, Any]],
    images: dict[tuple[str, str], Path],
    raw_path: Path,
    ledger_handle: Any,
    completed_before: int,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    role, model_id, revision = model_spec["role"], model_spec["model_id"], model_spec["revision"]
    selected = [row for row in workload if row["model_role"] == role]
    artifact = _model_artifact_manifest(model_id, revision)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    load_start = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model, loading_info = AutoModelForImageTextToText.from_pretrained(
        model_id, revision=revision, trust_remote_code=False, dtype=torch.float16,
        attn_implementation="sdpa", output_loading_info=True,
    )
    _validate_loading_info(loading_info)
    model = model.to("cuda").eval()
    load_seconds = time.perf_counter() - load_start
    manifest = {
        **artifact,
        "role": role,
        "model_class": type(model).__name__,
        "processor_class": type(processor).__name__,
        "processor": _jsonable(processor.to_dict()),
        "model_config": _jsonable(model.config.to_dict()),
        "generation_config": _jsonable(model.generation_config.to_dict()),
        "loading_info": _loading_info_safe(loading_info),
        "model_load_seconds": load_seconds,
    }
    latencies: list[float] = []
    completed = completed_before
    with raw_path.open("x", encoding="utf-8", newline="\n") as raw_handle:
        for frozen in selected:
            image_path = images[(frozen["source_zip_path"], frozen["budget_id"])]
            if sha256_file(image_path) == "":
                raise RuntimeError("unreadable materialized image")
            with Image.open(image_path) as opened:
                opened.load()
                if opened.mode != "RGB" or list(opened.size) != frozen["input_resolution"]:
                    raise RuntimeError("materialized image geometry mismatch")
                image = opened.copy()
            messages = [{"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": design["prompt"]},
            ]}]
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                processor_kwargs={
                    "min_pixels": int(frozen["min_pixels"]),
                    "max_pixels": int(frozen["max_pixels"]),
                },
            )
            input_ids = inputs["input_ids"].detach().cpu()
            input_length = int(input_ids.shape[-1])
            grid = [int(value) for value in inputs["image_grid_thw"][0].tolist()]
            n_pre = grid[0] * grid[1] * grid[2]
            merge = int(model.config.vision_config.spatial_merge_size)
            n_llm = grid[0] * (grid[1] // merge) * (grid[2] // merge)
            placeholders = int((input_ids == int(model.config.image_token_id)).sum().item())
            if (
                grid != frozen["expected_image_grid_thw"]
                or n_pre != frozen["expected_pre_merge"]
                or n_llm != frozen["expected_llm_placeholders"]
                or placeholders != frozen["expected_llm_placeholders"]
            ):
                raise RuntimeError("unexplained visual-token accounting")
            if not torch.isfinite(inputs["pixel_values"]).all().item():
                raise RuntimeError("NaN or Inf in processor tensor")
            inputs = inputs.to("cuda")
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.inference_mode():
                output = model.generate(
                    **inputs,
                    do_sample=False,
                    num_beams=1,
                    max_new_tokens=int(design["decoding"]["max_new_tokens"]),
                    use_cache=True,
                )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            output_cpu = output.detach().cpu()
            if output_cpu.ndim != 2 or output_cpu.shape[-1] < input_length:
                raise RuntimeError("invalid generated tensor shape")
            if not torch.equal(output_cpu[:, :input_length], input_ids):
                raise RuntimeError("generated output boundary corruption")
            generated = output_cpu[0, input_length:].tolist()
            raw = processor.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            if raw.encode("utf-8").decode("utf-8") != raw or "\ufffd" in raw:
                raise RuntimeError("Unicode decoding corruption")
            scientific = {
                **frozen,
                "materialized_image_sha256": sha256_file(image_path),
                "input_token_ids": input_ids[0].tolist(),
                "input_token_count": input_length,
                "full_output_token_ids": output_cpu[0].tolist(),
                "generated_token_ids": generated,
                "output_slice_start": input_length,
                "raw_output": raw,
            }
            _jsonl_append(raw_handle, scientific)
            engineering = {
                "call_index": frozen["call_index"],
                "call_id": frozen["call_id"],
                "input_resolution": frozen["input_resolution"],
                "image_grid_thw": grid,
                "pre_merge": n_pre,
                "projector_output": n_llm,
                "llm_image_placeholders": placeholders,
                "pixel_values_shape": list(inputs["pixel_values"].shape),
                "input_prefix_identity": True,
                "call_seconds": elapsed,
                "finite_processor_tensor": True,
            }
            _jsonl_append(ledger_handle, engineering)
            completed += 1
            if completed % 100 == 0:
                print(f"ENGINEERING_PROGRESS completed_calls={completed}/{EXPECTED_CALLS}", flush=True)
    runtime = {
        "role": role,
        "model_load_seconds": load_seconds,
        "call_count": len(selected),
        "inference_seconds_total": sum(latencies),
        "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved()),
    }
    del model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return manifest, runtime, completed


def execute_remote_panel(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text("utf-8"))
    artifact = Path(spec["output_root"]) / spec["run_id"]
    artifact.mkdir(parents=True, exist_ok=False)
    engineering = artifact / "engineering"
    sealed = artifact / "sealed"
    engineering.mkdir()
    sealed.mkdir()
    phase = "authorization"
    started = time.perf_counter()
    try:
        if not spec.get("locked_panel_authorized") or spec["frozen_design_git_sha"] != FROZEN_DESIGN_SHA:
            raise RuntimeError("locked-panel authorization mismatch")
        frozen_path = Path(spec["staged_frozen_design_path"])
        bundle_path = Path(spec["staged_locked_bundle_path"])
        if sha256_file(frozen_path) != FROZEN_DESIGN_FILE_SHA256:
            raise RuntimeError("frozen design blob mismatch")
        if sha256_file(Path.cwd() / "src/labbs2026/stage0/resolution_pipeline.py") != FROZEN_PIPELINE_FILE_SHA256:
            raise RuntimeError("frozen resolution pipeline implementation mismatch")
        design = _yaml(frozen_path)
        if design["execution"]["total_calls"] != EXPECTED_CALLS:
            raise RuntimeError("frozen workload count mismatch")
        bundle_manifest = verify_locked_source_bundle(bundle_path, spec["locked_source_bundle_sha256"])
        phase = "cuda_preflight"
        gpu = cuda_preflight(spec["requested_accelerator"])
        atomic_write_json(engineering / "environment_manifest.json", {
            "schema_version": 1, "gpu": gpu, "environment": _environment(),
        })
        phase = "source_and_stimulus_preparation"
        shutil.copyfile(bundle_path, sealed / "locked_source_bundle.zip")
        source_root = sealed / "source_448"
        pairs, renders = _extract_sources(bundle_path, source_root)
        allocation = _yaml(Path.cwd() / design["dataset"]["allocation_source"])
        workload = build_workload(design, allocation, pairs, renders)
        images, stimuli = materialize_stimuli(workload, source_root, sealed / "stimuli")
        atomic_write_text(sealed / "stimulus_manifest.jsonl", "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in stimuli
        ))
        atomic_write_text(sealed / "workload_manifest.jsonl", "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in workload
        ))
        phase = "model_execution"
        manifests, runtimes, completed = [], [], 0
        ledger_path = engineering / "call_ledger.jsonl"
        with ledger_path.open("x", encoding="utf-8", newline="\n") as ledger:
            for model_spec in design["models"]:
                manifest, runtime, completed = _run_model(
                    model_spec, design, workload, images,
                    sealed / f"raw_outputs_{model_spec['role'].lower()}.jsonl",
                    ledger, completed,
                )
                manifests.append(manifest)
                runtimes.append(runtime)
        if completed != EXPECTED_CALLS:
            raise RuntimeError("missing model calls")
        phase = "engineering_contract_validation"
        ledger_rows = [json.loads(line) for line in ledger_path.read_text("utf-8").splitlines()]
        if len(ledger_rows) != EXPECTED_CALLS or len({row["call_id"] for row in ledger_rows}) != EXPECTED_CALLS:
            raise RuntimeError("missing or duplicated engineering call ledger")
        token_counts = Counter(row["llm_image_placeholders"] for row in ledger_rows)
        if token_counts != {256: 1600, 196: 1600, 121: 1600, 64: 1600}:
            raise RuntimeError("unexpected aggregate token accounting")
        atomic_write_json(engineering / "model_revision_manifest.json", {"schema_version": 1, "models": manifests})
        atomic_write_json(engineering / "runtime_vram_report.json", {
            "schema_version": 1, "gpu": gpu, "models": runtimes,
            "total_seconds": time.perf_counter() - started,
        })
        for path in sealed.rglob("*"):
            if path.is_file():
                os.chmod(path, 0o444)
        atomic_write_json(engineering / "execution_manifest.json", {
            "schema_version": 1,
            "run_id": spec["run_id"],
            "run_type": "PADDLE_WAYU_FROZEN_ONE_SHOT_LOCKED_MODEL_BUDGET_PANEL",
            "execution_git_sha": spec["git_sha"],
            "frozen_design_git_sha": FROZEN_DESIGN_SHA,
            "frozen_design_sha256": FROZEN_DESIGN_FILE_SHA256,
            "frozen_pipeline_sha256": FROZEN_PIPELINE_FILE_SHA256,
            "registered_locked_pair_count": 100,
            "unauthorized_or_out_of_workload_locked_pair_count": 0,
            "source_png_count": bundle_manifest["source_png_count"],
            "materialized_stimulus_count": len(stimuli),
            "call_count": completed,
            "unique_call_count": len({row["call_id"] for row in ledger_rows}),
            "token_count_distribution": dict(sorted(token_counts.items())),
            "scientific_outputs_sealed": True,
            "scientific_analysis_run": False,
            "terminal_state": "SEALED_PENDING_LOCAL_VERIFICATION",
            "created_at_utc": utc_now(),
        })
        atomic_write_json(engineering / "failure_log.json", {"schema_version": 1, "failures": []})
        atomic_write_text(artifact / "checksums.sha256", _recursive_checksums(artifact))
        atomic_write_json(artifact / "SUCCESS.json", {
            "schema_version": 1,
            "run_id": spec["run_id"],
            "checksums_sha256": sha256_file(artifact / "checksums.sha256"),
            "scientific_outputs_sealed": True,
            "timestamp_utc": utc_now(),
        })
    except BaseException as exc:
        failure = {
            "schema_version": 1,
            "run_id": spec.get("run_id"),
            "classification": "LOCKED_PANEL_TECHNICAL_INVALID_SCIENTIFIC_OUTPUTS_REMAIN_SEALED",
            "phase": phase,
            "exception_type": type(exc).__name__,
            "message": str(exc)[:2000],
            "timestamp_utc": utc_now(),
        }
        atomic_write_json(engineering / "FAILURE.json", failure)
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    execute_remote_panel(parser.parse_args().remote_spec)
