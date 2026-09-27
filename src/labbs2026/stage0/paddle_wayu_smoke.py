"""Fail-closed, non-scientific PaddleOCR-VL / Wayu engineering smoke."""

from __future__ import annotations

import gc
import hashlib
import json
import platform
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from labbs2026.kaggle import (
    atomic_write_json,
    atomic_write_text,
    cuda_preflight,
    sha256_file,
    utc_now,
)


RECOMMENDATIONS = {
    "ENGINEERING_SMOKE_PASS_S0_READY_PROPOSED",
    "ENGINEERING_REPAIR_REQUIRED",
    "COMPUTE_BACKEND_INFEASIBLE",
    "MODEL_PAIR_IMPLEMENTATION_INCOMPATIBLE",
}


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


def build_workload(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the exact deterministic 40-call order without model outcomes."""
    selected = config["selection"]
    condition = config["render_condition"]
    calls: list[dict[str, Any]] = []
    for model in config["models"]:
        for repeat in range(1, int(selected["exact_repeats"]) + 1):
            for pair_id in selected["pair_ids"]:
                for member in selected["members"]:
                    calls.append(
                        {
                            "call_index": len(calls) + 1,
                            "model_role": model["role"],
                            "model_id": model["model_id"],
                            "revision": model["revision"],
                            "repeat": repeat,
                            "pair_id": pair_id,
                            "member": member,
                            "condition_id": condition,
                            "zip_path": (
                                f"renders/{condition}/{pair_id}__{member}.png"
                            ),
                            "image_sha256": config["expected_image_sha256"][
                                pair_id
                            ][member],
                            "prompt": config["prompt"],
                        }
                    )
    if len(calls) != int(selected["expected_calls"]):
        raise RuntimeError("workload call count differs from frozen expectation")
    return calls


def audit_locked_set(
    config: dict[str, Any], calibration_design: dict[str, Any]
) -> dict[str, Any]:
    selected = set(config["selection"]["pair_ids"])
    calibration = set(calibration_design["allocation"]["calibration_pair_ids"])
    locked = set(calibration_design["allocation"]["locked_validation_pair_ids"])
    exposed = sorted(selected & calibration)
    locked_exposed = sorted(selected & locked)
    result = {
        "schema_version": 1,
        "selected_pair_ids": sorted(selected),
        "already_exposed_open_calibration_pair_ids": exposed,
        "locked_pair_ids_exposed": locked_exposed,
        "locked_pair_count": len(locked_exposed),
        "valid": selected <= calibration and not locked_exposed,
    }
    return result


def repeat_consistency(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in records:
        key = (row["model_role"], row["pair_id"], row["member"])
        groups.setdefault(key, []).append(row)
    checks: list[dict[str, Any]] = []
    for key, rows in sorted(groups.items()):
        rows.sort(key=lambda row: row["repeat"])
        first = rows[0]
        fields = (
            "input_token_ids",
            "generated_token_ids",
            "decoded_output",
            "image_grid_thw",
            "visual_token_counts",
            "intermediate_shapes",
        )
        consistent = len(rows) == 2 and all(
            row[field] == first[field] for row in rows[1:] for field in fields
        )
        checks.append(
            {
                "model_role": key[0],
                "pair_id": key[1],
                "member": key[2],
                "repeat_count": len(rows),
                "exact_repeat_consistent": consistent,
            }
        )
    return {
        "schema_version": 1,
        "group_count": len(checks),
        "all_exact_repeats_consistent": bool(checks)
        and all(row["exact_repeat_consistent"] for row in checks),
        "checks": checks,
    }


def cross_model_prompt_consistency(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in records:
        key = (row["pair_id"], row["member"], row["repeat"])
        groups.setdefault(key, []).append(row)
    checks = []
    for key, rows in sorted(groups.items()):
        rows.sort(key=lambda row: row["model_role"])
        consistent = (
            len(rows) == 2
            and rows[0]["prompt"] == rows[1]["prompt"] == "OCR:"
            and rows[0]["image_sha256"] == rows[1]["image_sha256"]
            and rows[0]["input_token_ids"] == rows[1]["input_token_ids"]
        )
        checks.append(
            {
                "pair_id": key[0],
                "member": key[1],
                "repeat": key[2],
                "same_semantic_prompt_image_and_input_ids": consistent,
            }
        )
    return {
        "schema_version": 1,
        "all_consistent": bool(checks)
        and all(row["same_semantic_prompt_image_and_input_ids"] for row in checks),
        "checks": checks,
    }


def _first_tensor(value: Any) -> Any:
    import torch

    if isinstance(value, torch.Tensor):
        return value
    last = getattr(value, "last_hidden_state", None)
    if isinstance(last, torch.Tensor):
        return last
    if isinstance(value, (tuple, list)):
        for item in value:
            found = _first_tensor(item)
            if found is not None:
                return found
    return None


def _resolve_module(model: Any, path: str) -> Any:
    current = model
    for part in path.split("."):
        if not hasattr(current, part):
            raise AttributeError(f"required module path missing: {path} at {part}")
        current = getattr(current, part)
    return current


def _hook_collector(
    target: dict[str, list[dict[str, Any]]], name: str
) -> Callable[..., None]:
    def capture(_module: Any, _inputs: Any, output: Any) -> None:
        import torch

        tensor = _first_tensor(output)
        if tensor is None:
            target[name].append({"shape": None, "finite": False})
            return
        target[name].append(
            {
                "shape": list(tensor.shape),
                "dtype": str(tensor.dtype),
                "finite": bool(torch.isfinite(tensor).all().item()),
            }
        )

    return capture


def _environment() -> dict[str, Any]:
    import torch
    import transformers

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
    }


def _loading_info_safe(info: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _jsonable(info.get(key, []))
        for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")
    }


def _allowed_unexpected(key: str) -> bool:
    return "packing_position_embedding" in key or "vision_model.head" in key


def _validate_loading_info(info: dict[str, Any]) -> None:
    if info.get("missing_keys") or info.get("mismatched_keys") or info.get("error_msgs"):
        raise RuntimeError(f"incompatible model loading info: {_loading_info_safe(info)}")
    unexpected = [
        key for key in info.get("unexpected_keys", []) if not _allowed_unexpected(key)
    ]
    if unexpected:
        raise RuntimeError(f"unexpected generative-core keys: {unexpected}")


def _prepare_images(
    source_zip: Path,
    workload: list[dict[str, Any]],
    destination: Path,
) -> dict[str, Path]:
    unique = {(row["zip_path"], row["image_sha256"]) for row in workload}
    resolved: dict[str, Path] = {}
    with zipfile.ZipFile(source_zip) as archive:
        for zip_path, expected_hash in sorted(unique):
            payload = archive.read(zip_path)
            if _sha_bytes(payload) != expected_hash:
                raise RuntimeError(f"input image hash mismatch: {zip_path}")
            output = destination / Path(zip_path).name
            output.write_bytes(payload)
            resolved[zip_path] = output
    return resolved


def _model_artifact_manifest(model_id: str, revision: str) -> dict[str, Any]:
    from huggingface_hub import HfApi, hf_hub_download

    info = HfApi().model_info(model_id, revision=revision, files_metadata=True)
    if info.sha != revision:
        raise RuntimeError(f"checkpoint revision mismatch: {model_id}: {info.sha}")
    files = {}
    for name in (
        "config.json",
        "preprocessor_config.json",
        "processor_config.json",
        "tokenizer_config.json",
        "chat_template.jinja",
        "model.safetensors",
    ):
        path = Path(hf_hub_download(model_id, name, revision=revision))
        files[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    return {
        "model_id": model_id,
        "requested_revision": revision,
        "resolved_revision": info.sha,
        "last_modified": str(info.last_modified),
        "files": files,
    }


def _run_one_model(
    model_spec: dict[str, Any],
    config: dict[str, Any],
    workload: list[dict[str, Any]],
    images: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    role = model_spec["role"]
    selected = [row for row in workload if row["model_role"] == role]
    revision = model_spec["revision"]
    model_id = model_spec["model_id"]
    artifact = _model_artifact_manifest(model_id, revision)

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        model_id,
        revision=revision,
        trust_remote_code=False,
    )
    model, loading_info = AutoModelForImageTextToText.from_pretrained(
        model_id,
        revision=revision,
        trust_remote_code=False,
        dtype=torch.float16,
        attn_implementation=config["loading"]["attention_implementation"],
        output_loading_info=True,
    )
    _validate_loading_info(loading_info)
    model = model.to("cuda").eval()
    load_seconds = time.perf_counter() - load_started

    module_paths = config["required_module_paths"]
    modules = {name: _resolve_module(model, path) for name, path in module_paths.items()}
    model_manifest = {
        **artifact,
        "role": role,
        "model_class": type(model).__name__,
        "processor_class": type(processor).__name__,
        "processor": _jsonable(processor.to_dict()),
        "model_config": _jsonable(model.config.to_dict()),
        "generation_config": _jsonable(model.generation_config.to_dict()),
        "loading_info": _loading_info_safe(loading_info),
        "required_module_paths": {
            name: {"path": module_paths[name], "class": type(module).__name__}
            for name, module in modules.items()
        },
        "model_load_seconds": load_seconds,
    }

    records: list[dict[str, Any]] = []
    call_seconds: list[float] = []
    for frozen_call in selected:
        captures: dict[str, list[dict[str, Any]]] = {
            name: []
            for name in (
                "patch_embeddings",
                "vision_encoder",
                "post_encoder_norm",
                "projector",
                "language_logits",
            )
        }
        handles = [
            modules[name].register_forward_hook(_hook_collector(captures, name))
            for name in captures
        ]
        try:
            with Image.open(images[frozen_call["zip_path"]]) as source_image:
                image = source_image.convert("RGB").copy()
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": config["prompt"]},
                    ],
                }
            ]
            inputs = processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
            input_ids_cpu = inputs["input_ids"].detach().cpu()
            input_length = int(input_ids_cpu.shape[-1])
            grid = [int(value) for value in inputs["image_grid_thw"][0].tolist()]
            temporal, height, width = grid
            n_pre = temporal * height * width
            merge = int(model.config.vision_config.spatial_merge_size)
            n_llm = temporal * (height // merge) * (width // merge)
            placeholder_count = int(
                (input_ids_cpu == int(model.config.image_token_id)).sum().item()
            )
            if placeholder_count != n_llm:
                raise RuntimeError(
                    f"visual-token mismatch: placeholders={placeholder_count}, expected={n_llm}"
                )
            inputs = inputs.to("cuda")
            torch.cuda.synchronize()
            started = time.perf_counter()
            with torch.inference_mode():
                output_ids = model.generate(
                    **inputs,
                    do_sample=False,
                    num_beams=1,
                    max_new_tokens=int(config["decoding"]["max_new_tokens"]),
                    use_cache=True,
                )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            call_seconds.append(elapsed)
            output_cpu = output_ids.detach().cpu()
            if output_cpu.shape[-1] < input_length or not torch.equal(
                output_cpu[:, :input_length], input_ids_cpu
            ):
                raise RuntimeError("generated output cannot be isolated from input tokens")
            generated = output_cpu[0, input_length:].tolist()
            decoded = processor.decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            ).strip()
            if decoded.encode("utf-8").decode("utf-8") != decoded or "\ufffd" in decoded:
                raise RuntimeError("Unicode decoding corruption")
            expected = config["expected_shapes"]
            for name in (
                "patch_embeddings",
                "vision_encoder",
                "post_encoder_norm",
                "projector",
            ):
                values = captures[name]
                if len(values) != 1 or not values[0]["finite"]:
                    raise RuntimeError(f"invalid {name} capture: {values}")
            if not captures["language_logits"] or not all(
                value["finite"] for value in captures["language_logits"]
            ):
                raise RuntimeError(
                    f"invalid language logits: {captures['language_logits']}"
                )
            patch_shape = captures["patch_embeddings"][0]["shape"]
            encoder_shape = captures["vision_encoder"][0]["shape"]
            post_shape = captures["post_encoder_norm"][0]["shape"]
            projector_shape = captures["projector"][0]["shape"]
            if (
                patch_shape[-1] != int(expected["vision_hidden_size"])
                or encoder_shape[-1] != int(expected["vision_hidden_size"])
                or post_shape[-1] != int(expected["vision_hidden_size"])
                or projector_shape[-1] != int(expected["projector_hidden_size"])
            ):
                raise RuntimeError("intermediate hidden-size mismatch")
            if (
                int(torch.tensor(patch_shape[:-1]).prod().item()) != n_pre
                or int(torch.tensor(encoder_shape[:-1]).prod().item()) != n_pre
                or int(torch.tensor(post_shape[:-1]).prod().item()) != n_pre
                or int(torch.tensor(projector_shape[:-1]).prod().item()) != n_llm
            ):
                raise RuntimeError("intermediate visual-position count mismatch")
            records.append(
                {
                    **frozen_call,
                    "scientific_use": "FORBIDDEN_ENGINEERING_OBSERVATION_ONLY",
                    "input_token_ids": input_ids_cpu[0].tolist(),
                    "input_token_count": input_length,
                    "full_output_token_ids": output_cpu[0].tolist(),
                    "generated_token_ids": generated,
                    "decoded_output": decoded,
                    "output_slice_start": input_length,
                    "output_prefix_identity": True,
                    "unicode_utf8_roundtrip": True,
                    "pixel_values_shape": list(inputs["pixel_values"].shape),
                    "image_grid_thw": grid,
                    "visual_token_counts": {
                        "pre_merge": n_pre,
                        "projector_output": n_llm,
                        "llm_image_placeholders": placeholder_count,
                    },
                    "intermediate_shapes": captures,
                    "call_seconds": elapsed,
                }
            )
        finally:
            for handle in handles:
                handle.remove()

    runtime = {
        "role": role,
        "model_load_seconds": load_seconds,
        "call_count": len(records),
        "inference_seconds_total": sum(call_seconds),
        "inference_seconds_per_call": call_seconds,
        "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        "allocated_before_unload_bytes": int(torch.cuda.memory_allocated()),
    }
    del model
    del processor
    gc.collect()
    torch.cuda.empty_cache()
    runtime["allocated_after_unload_bytes"] = int(torch.cuda.memory_allocated())
    return records, model_manifest, runtime


def _checksums(artifact_dir: Path) -> str:
    names = sorted(
        path.name
        for path in artifact_dir.iterdir()
        if path.is_file() and path.name not in {"checksums.sha256", "SUCCESS.json"}
    )
    return "".join(f"{sha256_file(artifact_dir / name)}  {name}\n" for name in names)


def execute_remote_smoke(remote_spec_path: Path) -> None:
    spec = json.loads(remote_spec_path.read_text("utf-8"))
    source_root = Path.cwd()
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=False)
    failure_log = {"schema_version": 1, "failures": []}
    started = time.perf_counter()
    phase = "configuration"
    try:
        config_path = source_root / spec["config_path"]
        config = _yaml(config_path)
        if config["status"] != "APPROVED_FOR_ENGINEERING_SMOKE_ONLY":
            raise RuntimeError("smoke authorization status mismatch")
        if any(config["prohibitions"].values()):
            raise RuntimeError("prohibition contract must contain only false values")
        source_zip = source_root / config["source_bundle"]
        if sha256_file(source_zip) != config["source_bundle_sha256"]:
            raise RuntimeError("source bundle hash mismatch")
        workload = build_workload(config)
        locked_audit = audit_locked_set(
            config, _yaml(source_root / config["source_design"])
        )
        atomic_write_json(artifact_dir / "locked_set_audit.json", locked_audit)
        if not locked_audit["valid"] or locked_audit["locked_pair_count"] != 0:
            raise RuntimeError("locked-validation pair exposure detected")
        atomic_write_json(
            artifact_dir / "workload_manifest.json",
            {"schema_version": 1, "call_count": len(workload), "calls": workload},
        )

        phase = "cuda_preflight"
        gpu = cuda_preflight(spec["requested_accelerator"])
        environment = _environment()
        atomic_write_json(
            artifact_dir / "environment_manifest.json",
            {"schema_version": 1, "gpu": gpu, "environment": environment},
        )

        phase = "input_extraction"
        image_dir = artifact_dir / "input_pngs"
        image_dir.mkdir()
        images = _prepare_images(source_zip, workload, image_dir)

        phase = "model_execution"
        records: list[dict[str, Any]] = []
        model_manifests = []
        model_runtimes = []
        for model_spec in config["models"]:
            model_records, manifest, runtime = _run_one_model(
                model_spec, config, workload, images
            )
            records.extend(model_records)
            model_manifests.append(manifest)
            model_runtimes.append(runtime)
            atomic_write_text(
                artifact_dir / "raw_outputs.jsonl",
                "".join(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                    for row in records
                ),
            )

        phase = "engineering_validation"
        if len(records) != 40:
            raise RuntimeError(f"observed call count is {len(records)}, expected 40")
        repeats = repeat_consistency(records)
        prompt_consistency = cross_model_prompt_consistency(records)
        if not repeats["all_exact_repeats_consistent"]:
            raise RuntimeError("deterministic exact-repeat failure")
        if not prompt_consistency["all_consistent"]:
            raise RuntimeError("cross-model prompt/input construction mismatch")
        atomic_write_json(artifact_dir / "model_revision_manifest.json", {
            "schema_version": 1,
            "models": model_manifests,
        })
        atomic_write_json(artifact_dir / "repeat_consistency_report.json", repeats)
        atomic_write_json(
            artifact_dir / "prompt_consistency_report.json", prompt_consistency
        )
        atomic_write_json(
            artifact_dir / "processor_grid_token_report.json",
            {
                "schema_version": 1,
                "calls": [
                    {
                        key: row[key]
                        for key in (
                            "call_index",
                            "model_role",
                            "pair_id",
                            "member",
                            "repeat",
                            "image_sha256",
                            "pixel_values_shape",
                            "image_grid_thw",
                            "input_token_count",
                            "visual_token_counts",
                        )
                    }
                    for row in records
                ],
            },
        )
        atomic_write_json(
            artifact_dir / "intermediate_tensor_shapes.json",
            {
                "schema_version": 1,
                "scientific_comparison": "FORBIDDEN",
                "calls": [
                    {
                        "call_index": row["call_index"],
                        "model_role": row["model_role"],
                        "pair_id": row["pair_id"],
                        "member": row["member"],
                        "repeat": row["repeat"],
                        "intermediate_shapes": row["intermediate_shapes"],
                    }
                    for row in records
                ],
            },
        )
        atomic_write_json(
            artifact_dir / "runtime_vram_report.json",
            {
                "schema_version": 1,
                "gpu": gpu,
                "models": model_runtimes,
                "total_seconds": time.perf_counter() - started,
            },
        )
        atomic_write_json(artifact_dir / "failure_log.json", failure_log)
        recommendation = "ENGINEERING_SMOKE_PASS_S0_READY_PROPOSED"
        atomic_write_json(
            artifact_dir / "recommendation.json",
            {
                "schema_version": 1,
                "recommendation": recommendation,
                "automatic_stage_s0_authorization": False,
                "terminal_state": "HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE",
            },
        )
        manifest = {
            "schema_version": 1,
            "run_id": spec["run_id"],
            "run_type": "PADDLE_WAYU_NON_SCIENTIFIC_40_CALL_ENGINEERING_SMOKE",
            "status": "ENGINEERING_SMOKE_PASS",
            "scientific_use": "FORBIDDEN",
            "git_sha": spec["git_sha"],
            "remote_ref": spec["remote_ref"],
            "config_path": spec["config_path"],
            "config_sha256": spec["config_sha256"],
            "runtime_sha256": spec["runtime_sha256"],
            "source_bundle_sha256": config["source_bundle_sha256"],
            "call_count": len(records),
            "locked_pair_count": 0,
            "recommendation": recommendation,
            "terminal_state": "HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE",
            "created_at_utc": utc_now(),
        }
        atomic_write_json(artifact_dir / "manifest.json", manifest)
        atomic_write_text(artifact_dir / "checksums.sha256", _checksums(artifact_dir))
        atomic_write_json(
            artifact_dir / "SUCCESS.json",
            {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
                "timestamp_utc": utc_now(),
            },
        )
    except BaseException as exc:
        failure = {
            "phase": phase,
            "exception_type": type(exc).__name__,
            "message": str(exc)[:4000],
            "timestamp_utc": utc_now(),
        }
        failure_log["failures"].append(failure)
        atomic_write_json(artifact_dir / "failure_log.json", failure_log)
        atomic_write_json(
            artifact_dir / "FAILURE.json",
            {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "classification": "ENGINEERING_SMOKE_FAILED",
                **failure,
            },
        )
        raise


def verify_fetched_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["kaggle_complete"] = kaggle_status == "COMPLETE"
    checks["success_present"] = (artifact_dir / "SUCCESS.json").is_file()
    checks["failure_absent"] = not (artifact_dir / "FAILURE.json").exists()
    required = {
        "manifest.json",
        "model_revision_manifest.json",
        "environment_manifest.json",
        "workload_manifest.json",
        "raw_outputs.jsonl",
        "repeat_consistency_report.json",
        "prompt_consistency_report.json",
        "processor_grid_token_report.json",
        "intermediate_tensor_shapes.json",
        "runtime_vram_report.json",
        "failure_log.json",
        "locked_set_audit.json",
        "recommendation.json",
        "checksums.sha256",
    }
    checks["required_artifacts"] = all((artifact_dir / name).is_file() for name in required)
    try:
        manifest = json.loads((artifact_dir / "manifest.json").read_text("utf-8"))
        repeats = json.loads(
            (artifact_dir / "repeat_consistency_report.json").read_text("utf-8")
        )
        prompt = json.loads(
            (artifact_dir / "prompt_consistency_report.json").read_text("utf-8")
        )
        locked = json.loads((artifact_dir / "locked_set_audit.json").read_text("utf-8"))
        recommendation = json.loads(
            (artifact_dir / "recommendation.json").read_text("utf-8")
        )
        rows = [
            json.loads(line)
            for line in (artifact_dir / "raw_outputs.jsonl").read_text("utf-8").splitlines()
            if line
        ]
        declared = {}
        for line in (artifact_dir / "checksums.sha256").read_text("utf-8").splitlines():
            digest, name = line.split(maxsplit=1)
            declared[name.strip()] = digest
        checks["checksums"] = all(
            (artifact_dir / name).is_file()
            and sha256_file(artifact_dir / name) == digest
            for name, digest in declared.items()
        )
        checks["identity"] = (
            manifest["run_id"] == submission["run_id"]
            and manifest["git_sha"] == submission["git_sha"]
            and manifest["config_sha256"] == submission["config_sha256"]
            and manifest["runtime_sha256"] == submission["runtime_sha256"]
        )
        checks["exact_40_calls"] = len(rows) == manifest["call_count"] == 40
        checks["locked_zero"] = locked["locked_pair_count"] == 0
        checks["repeat_consistency"] = repeats["all_exact_repeats_consistent"]
        checks["prompt_consistency"] = prompt["all_consistent"]
        checks["recommendation"] = (
            recommendation["recommendation"]
            == "ENGINEERING_SMOKE_PASS_S0_READY_PROPOSED"
            and recommendation["recommendation"] in RECOMMENDATIONS
        )
        checks["no_scientific_authorization"] = (
            manifest["scientific_use"] == "FORBIDDEN"
            and recommendation["automatic_stage_s0_authorization"] is False
        )
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        checks["artifact_parse"] = False
    return {
        "schema_version": 1,
        "verification_status": "VERIFIED" if checks and all(checks.values()) else "INVALID",
        "checks": checks,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    execute_remote_smoke(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
