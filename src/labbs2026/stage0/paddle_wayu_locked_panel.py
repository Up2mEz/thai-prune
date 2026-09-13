"""Fail-closed execution for the authorized frozen one-shot locked panel."""

from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from labbs2026.kaggle import atomic_write_json, atomic_write_text, cuda_preflight, sha256_file, utc_now
from labbs2026.stage0.locked_content_manifest import verify_expanded_locked_content
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
AUTHORIZATION_FILENAME = "AUTHORIZATION_VALIDATED.json"
CORE_OWNERSHIP_FILENAME = "CORE_OWNERSHIP_CLAIMED.json"
U_FFFD_FAILURE_REASON = "U_FFFD_REPLACEMENT_CHARACTER"
WHITESPACE_FAILURE_REASON = "INTERNAL_WHITESPACE_PRESENT_AFTER_PRIMARY_PARSE"
FROZEN_DECODE_KWARGS = {
    "skip_special_tokens": True,
    "clean_up_tokenization_spaces": False,
}


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


def _artifact_tree_has_symlink(root: Path) -> bool:
    pending = [root]
    while pending:
        directory = pending.pop()
        for child in directory.iterdir():
            if child.is_symlink():
                return True
            if child.is_dir():
                pending.append(child)
    return False


def _authorization_record(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid bootstrap authorization JSON") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RuntimeError("bootstrap authorization schema mismatch")
    identity_path = Path.cwd() / spec["execution_identity_config_path"]
    identity = _yaml(identity_path)
    exact = {
        "status": value.get("status") == "AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION",
        "authorization_only": value.get("authorization_only") is False,
        "run_id": value.get("run_id") == spec["run_id"],
        "identity_config_sha256": sha256_file(identity_path)
        == spec["execution_identity_config_sha256"],
        "identity_config_run_id": identity.get("run_id")
        == value.get("run_id")
        == spec["run_id"],
        "identity_config_attempt": identity.get("attempt")
        == value.get("attempt")
        == spec.get("attempt"),
        "authorization_label": value.get("authorization_label")
        == spec.get("authorization_label")
        == identity.get("status"),
        "original_scientific_design_commit": value.get("ORIGINAL_SCIENTIFIC_DESIGN_COMMIT")
        == spec["ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"]
        == identity.get("original_scientific_design_commit"),
        "protocol_amendment_commit": value.get("PROTOCOL_AMENDMENT_COMMIT")
        == spec["PROTOCOL_AMENDMENT_COMMIT"]
        == identity.get("protocol_amendment_commit"),
        "execution_commit": value.get("ATTEMPT5_EXECUTION_COMMIT")
        == spec["ATTEMPT5_EXECUTION_COMMIT"]
        == spec["git_sha"],
        "effective_protocol": value.get("effective_scientific_protocol")
        == spec["effective_scientific_protocol"],
        "dataset_id": value.get("kaggle_dataset_numeric_id")
        == spec["kaggle_dataset_numeric_id"],
        "dataset_version": value.get("kaggle_dataset_version")
        == spec["kaggle_dataset_version"],
        "scientific_contract": value.get("scientific_contract_valid") is True,
    }
    frozen = value.get("frozen_design")
    exact["frozen_design_sha256"] = (
        isinstance(frozen, dict)
        and frozen.get("sha256") == spec["frozen_design_sha256"]
        and frozen.get("expected_sha256") == spec["frozen_design_sha256"]
    )
    manifest = value.get("locked_content_manifest")
    exact["content_manifest_sha256"] = (
        isinstance(manifest, dict)
        and manifest.get("sha256") == spec["locked_content_manifest_sha256"]
        and manifest.get("expected_sha256") == spec["locked_content_manifest_sha256"]
    )
    source = value.get("locked_source_content")
    exact["source_verification"] = (
        isinstance(source, dict)
        and source.get("exact_path_set") is True
        and source.get("all_sizes_match") is True
        and source.get("all_sha256_match") is True
        and source.get("member_count") == spec["locked_content_member_count"]
        and source.get("total_uncompressed_bytes")
        == spec["locked_content_total_uncompressed_bytes"]
        and source.get("content_manifest_sha256")
        == spec["locked_content_manifest_sha256"]
        and source.get("original_transport_archive_sha256")
        == spec["original_transport_archive_sha256"]
        and source.get("expanded_source_directory") == spec["staged_locked_source_dir"]
    )
    if not all(exact.values()):
        raise RuntimeError(f"bootstrap authorization identity mismatch: {exact}")
    return value


def _create_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def claim_bootstrap_artifact_ownership(
    spec: dict[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    artifact = Path(spec["output_root"]) / spec["run_id"]
    if artifact.is_symlink() or not artifact.is_dir():
        raise RuntimeError("bootstrap artifact root must be a non-symlink directory")
    if _artifact_tree_has_symlink(artifact):
        raise RuntimeError("symlink in bootstrap artifact tree")
    engineering = artifact / "engineering"
    authorization_path = engineering / AUTHORIZATION_FILENAME
    disallowed = {
        "sealed": artifact / "sealed",
        "SUCCESS.json": artifact / "SUCCESS.json",
        "call_ledger.jsonl": engineering / "call_ledger.jsonl",
        CORE_OWNERSHIP_FILENAME: engineering / CORE_OWNERSHIP_FILENAME,
    }
    present = [name for name, path in disallowed.items() if path.exists()]
    if present:
        raise RuntimeError(f"pre-existing core artifact is forbidden: {present}")
    if {path.name for path in artifact.iterdir()} != {"engineering"}:
        raise RuntimeError("unexpected file or directory in bootstrap artifact root")
    if not engineering.is_dir():
        raise RuntimeError("bootstrap engineering directory is missing")
    if {path.name for path in engineering.iterdir()} != {AUTHORIZATION_FILENAME}:
        raise RuntimeError("unexpected bootstrap engineering inventory")
    if not authorization_path.is_file():
        raise RuntimeError("bootstrap authorization file is missing")
    authorization = _authorization_record(authorization_path, spec)
    claim = {
        "schema_version": 1,
        "run_id": spec["run_id"],
        "attempt": spec["attempt"],
        "authorization_label": spec["authorization_label"],
        "timestamp_utc": utc_now(),
        "authorization_artifact_sha256": sha256_file(authorization_path),
        "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": spec["ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"],
        "PROTOCOL_AMENDMENT_COMMIT": spec["PROTOCOL_AMENDMENT_COMMIT"],
        "ATTEMPT5_EXECUTION_COMMIT": spec["ATTEMPT5_EXECUTION_COMMIT"],
        "effective_scientific_protocol": spec["effective_scientific_protocol"],
        "frozen_design_sha256": spec["frozen_design_sha256"],
        "locked_content_manifest_sha256": spec["locked_content_manifest_sha256"],
    }
    _create_json_exclusive(engineering / CORE_OWNERSHIP_FILENAME, claim)
    return artifact, engineering, authorization


def initialize_artifact_handoff(
    spec: dict[str, Any],
) -> tuple[Path, Path, Path, dict[str, Any]]:
    artifact, engineering, authorization = claim_bootstrap_artifact_ownership(spec)
    sealed = artifact / "sealed"
    sealed.mkdir(exist_ok=False)
    return artifact, engineering, sealed, authorization


def _completed_call_count(ledger_path: Path) -> int:
    if not ledger_path.is_file():
        return 0
    with ledger_path.open("rb") as handle:
        return sum(
            chunk.count(b"\n")
            for chunk in iter(lambda: handle.read(1024 * 1024), b"")
        )


def _jsonl_append(handle: Any, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    handle.flush()


def classify_decoded_output_contract(raw: str) -> dict[str, Any]:
    """Classify a successfully decoded string without modifying its codepoints."""
    if raw.encode("utf-8").decode("utf-8") != raw:
        raise RuntimeError("Unicode decoding corruption")
    parsed = raw.strip()
    u_fffd_present = "\ufffd" in raw
    reason = None
    if u_fffd_present:
        reason = U_FFFD_FAILURE_REASON
    elif any(char.isspace() for char in parsed):
        reason = WHITESPACE_FAILURE_REASON
    return {
        "raw_output": raw,
        "u_fffd_present": u_fffd_present,
        "output_contract_failure": reason is not None,
        "output_contract_failure_reason": reason,
    }


def decode_generated_tokens(
    processor: Any,
    generated_token_ids: list[int],
    *,
    max_new_tokens: int,
) -> dict[str, Any]:
    """Apply the frozen decoder and attach sealed per-call termination metadata."""
    generated = [int(token_id) for token_id in generated_token_ids]
    if len(generated) > max_new_tokens:
        raise RuntimeError("generated token count exceeds frozen max_new_tokens")
    raw = processor.decode(generated, **FROZEN_DECODE_KWARGS)
    contract = classify_decoded_output_contract(raw)
    eos_value = processor.tokenizer.eos_token_id
    if eos_value is None:
        eos = set()
    elif isinstance(eos_value, int):
        eos = {eos_value}
    else:
        eos = {int(token_id) for token_id in eos_value}
    return {
        **contract,
        "generated_token_count": len(generated),
        "eos_reached": any(token_id in eos for token_id in generated),
        "max_new_tokens_reached": len(generated) == max_new_tokens,
    }


def engineering_progress_message(completed: int) -> str:
    """Return blinded live telemetry with no scientific identity or output."""
    return f"ENGINEERING_PROGRESS completed_calls={completed}/{EXPECTED_CALLS}"


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


def _copy_expanded_sources(source: Path, destination: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shutil.copytree(source, destination)
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
            decoded = decode_generated_tokens(
                processor,
                generated,
                max_new_tokens=int(design["decoding"]["max_new_tokens"]),
            )
            scientific = {
                **frozen,
                "materialized_image_sha256": sha256_file(image_path),
                "input_token_ids": input_ids[0].tolist(),
                "input_token_count": input_length,
                "full_output_token_ids": output_cpu[0].tolist(),
                "generated_token_ids": generated,
                "output_slice_start": input_length,
                **decoded,
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
                print(engineering_progress_message(completed), flush=True)
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
    engineering = artifact / "engineering"
    ledger_path = engineering / "call_ledger.jsonl"
    ownership_claimed = False
    phase = "artifact_ownership_adoption"
    started = time.perf_counter()
    try:
        artifact, engineering, sealed, _ = initialize_artifact_handoff(spec)
        ownership_claimed = True
        phase = "authorization"
        if not spec.get("locked_panel_authorized") or spec["frozen_design_git_sha"] != FROZEN_DESIGN_SHA:
            raise RuntimeError("locked-panel authorization mismatch")
        frozen_path = Path(spec["staged_frozen_design_path"])
        expanded_source_path = Path(spec["staged_locked_source_dir"])
        content_manifest_path = Path(spec["staged_locked_content_manifest_path"])
        if sha256_file(frozen_path) != FROZEN_DESIGN_FILE_SHA256:
            raise RuntimeError("frozen design blob mismatch")
        if sha256_file(Path.cwd() / "src/labbs2026/stage0/resolution_pipeline.py") != FROZEN_PIPELINE_FILE_SHA256:
            raise RuntimeError("frozen resolution pipeline implementation mismatch")
        design = _yaml(frozen_path)
        if design["execution"]["total_calls"] != EXPECTED_CALLS:
            raise RuntimeError("frozen workload count mismatch")
        if sha256_file(content_manifest_path) != spec["locked_content_manifest_sha256"]:
            raise RuntimeError("locked content manifest hash mismatch")
        content_manifest = json.loads(content_manifest_path.read_text("utf-8"))
        content_verification = verify_expanded_locked_content(
            expanded_source_path, content_manifest
        )
        bundle_manifest = json.loads(
            (expanded_source_path / "bundle_manifest.json").read_text("utf-8")
        )
        phase = "cuda_preflight"
        gpu = cuda_preflight(spec["requested_accelerator"])
        atomic_write_json(engineering / "environment_manifest.json", {
            "schema_version": 1, "gpu": gpu, "environment": _environment(),
        })
        phase = "source_and_stimulus_preparation"
        source_root = sealed / "source_448"
        pairs, renders = _copy_expanded_sources(expanded_source_path, source_root)
        allocation = _yaml(Path.cwd() / design["dataset"]["allocation_source"])
        if allocation["allocation"]["sha256"] != spec["locked_allocation_sha256"]:
            raise RuntimeError("locked allocation hash mismatch")
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
            "attempt": spec["attempt"],
            "authorization_label": spec["authorization_label"],
            "run_type": "PADDLE_WAYU_FROZEN_ONE_SHOT_LOCKED_MODEL_BUDGET_PANEL",
            "execution_git_sha": spec["git_sha"],
            "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": spec["ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"],
            "PROTOCOL_AMENDMENT_COMMIT": spec["PROTOCOL_AMENDMENT_COMMIT"],
            "ATTEMPT5_EXECUTION_COMMIT": spec["ATTEMPT5_EXECUTION_COMMIT"],
            "effective_scientific_protocol": spec["effective_scientific_protocol"],
            "frozen_design_git_sha": FROZEN_DESIGN_SHA,
            "frozen_design_sha256": FROZEN_DESIGN_FILE_SHA256,
            "frozen_pipeline_sha256": FROZEN_PIPELINE_FILE_SHA256,
            "runtime_config_sha256": spec["runtime_config_sha256"],
            "ORIGINAL_TRANSPORT_ARCHIVE_SHA256": spec["original_transport_archive_sha256"],
            "LOCKED_CONTENT_MANIFEST_SHA256": spec["locked_content_manifest_sha256"],
            "KAGGLE_DATASET_ID": spec["kaggle_dataset_numeric_id"],
            "KAGGLE_DATASET_VERSION": spec["kaggle_dataset_version"],
            "locked_content_member_count": content_verification["member_count"],
            "locked_content_total_uncompressed_bytes": content_verification["total_uncompressed_bytes"],
            "locked_allocation_sha256": spec["locked_allocation_sha256"],
            "model_revision_hashes": spec["model_revision_hashes"],
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
            "attempt": spec.get("attempt"),
            "authorization_label": spec.get("authorization_label"),
            "scientific_completed_call_count": _completed_call_count(ledger_path),
            "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": spec.get("ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"),
            "PROTOCOL_AMENDMENT_COMMIT": spec.get("PROTOCOL_AMENDMENT_COMMIT"),
            "ATTEMPT5_EXECUTION_COMMIT": spec.get("ATTEMPT5_EXECUTION_COMMIT"),
            "classification": "LOCKED_PANEL_TECHNICAL_INVALID_SCIENTIFIC_OUTPUTS_REMAIN_SEALED",
            "phase": phase,
            "exception_type": type(exc).__name__,
            "message": str(exc)[:2000],
            "traceback": traceback.format_exc()[-16000:],
            "subprocess_stderr": "",
            "timestamp_utc": utc_now(),
        }
        if ownership_claimed:
            atomic_write_json(engineering / "FAILURE.json", failure)
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--artifact-handoff-test-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.artifact_handoff_test_only:
        initialize_artifact_handoff(json.loads(arguments.remote_spec.read_text("utf-8")))
    else:
        execute_remote_panel(arguments.remote_spec)
