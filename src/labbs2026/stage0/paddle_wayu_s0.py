"""Frozen Paddle/Wayu S0 open-calibration baseline runner and analysis."""

from __future__ import annotations

import gc
import json
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

from labbs2026.kaggle import atomic_write_json, atomic_write_text, cuda_preflight, sha256_file, utc_now
from labbs2026.stage0.paddle_wayu_smoke import (
    _checksums,
    _environment,
    _jsonable,
    _loading_info_safe,
    _model_artifact_manifest,
    _validate_loading_info,
)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def primary_parse(raw_output: str) -> str:
    """Frozen primary parser: only remove leading/trailing whitespace."""
    return raw_output.strip()


def codepoint_edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def classify_output(parsed: str, target: str, opposite: str) -> str:
    if parsed == target:
        return "exact_target"
    if parsed == opposite:
        return "opposite_member_substitution"
    if parsed == "":
        return "deletion_or_empty"
    if any(char.isspace() for char in parsed):
        return "output_contract_failure"
    if any("\u0e00" <= char <= "\u0e7f" for char in parsed):
        return "other_thai_substitution"
    return "non_thai_output"


def build_workload(config: dict[str, Any], design: dict[str, Any], inventory: dict[str, Any], render_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calibration = list(design["allocation"]["calibration_pair_ids"])
    excluded = set(config["selection"]["excluded_smoke_pair_ids"])
    selected = [pair_id for pair_id in calibration if pair_id not in excluded]
    pair_meta = {row["pair_id"]: row for row in inventory["pairs"]}
    render_meta = {(row["condition_id"], row["pair_id"]): row for row in render_rows}
    calls: list[dict[str, Any]] = []
    for model in config["models"]:
        for pair_id in selected:
            pair = pair_meta[pair_id]
            for condition_id in config["selection"]["condition_ids"]:
                render = render_meta[(condition_id, pair_id)]
                for member in config["selection"]["members"]:
                    other = "b" if member == "a" else "a"
                    calls.append({
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
                        "zip_path": render[f"image_{member}_path"],
                        "image_sha256": render[f"image_{member}_sha256"],
                        "prompt": config["prompt"],
                    })
    expected = int(config["selection"]["expected_calls"])
    if len(calls) != expected:
        raise RuntimeError(f"workload count {len(calls)} != {expected}")
    return calls


def audit_selection(config: dict[str, Any], design: dict[str, Any], workload: list[dict[str, Any]]) -> dict[str, Any]:
    calibration = set(design["allocation"]["calibration_pair_ids"])
    locked = set(design["allocation"]["locked_validation_pair_ids"])
    observed = {row["pair_id"] for row in workload}
    counts = Counter(row["component_type"] for row in {row["pair_id"]: row for row in workload}.values())
    locked_seen = sorted(observed & locked)
    return {
        "schema_version": 1,
        "selected_pair_count": len(observed),
        "component_pair_counts": dict(sorted(counts.items())),
        "excluded_smoke_pair_ids": config["selection"]["excluded_smoke_pair_ids"],
        "locked_pair_ids_exposed": locked_seen,
        "locked_pair_count": len(locked_seen),
        "valid": observed <= calibration and not locked_seen and len(observed) == 95 and set(counts.values()) == {19},
    }


def _prepare_images(source_zip: Path, workload: list[dict[str, Any]], destination: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    unique = {(row["zip_path"], row["image_sha256"]) for row in workload}
    with zipfile.ZipFile(source_zip) as archive:
        for zip_path, expected in sorted(unique):
            payload = archive.read(zip_path)
            import hashlib
            if hashlib.sha256(payload).hexdigest() != expected:
                raise RuntimeError(f"input image hash mismatch: {zip_path}")
            output = destination / zip_path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
            resolved[zip_path] = output
    return resolved


def _run_model(model_spec: dict[str, Any], config: dict[str, Any], workload: list[dict[str, Any]], images: dict[str, Path], raw_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
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
        attn_implementation=config["loading"]["attention_implementation"], output_loading_info=True,
    )
    _validate_loading_info(loading_info)
    model = model.to("cuda").eval()
    load_seconds = time.perf_counter() - load_start
    manifest = {
        **artifact, "role": role, "model_class": type(model).__name__,
        "processor_class": type(processor).__name__, "processor": _jsonable(processor.to_dict()),
        "model_config": _jsonable(model.config.to_dict()), "generation_config": _jsonable(model.generation_config.to_dict()),
        "loading_info": _loading_info_safe(loading_info), "model_load_seconds": load_seconds,
    }
    records, latencies = [], []
    for frozen in selected:
        with Image.open(images[frozen["zip_path"]]) as source:
            image = source.convert("RGB").copy()
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": config["prompt"]}]}]
        inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
        input_ids = inputs["input_ids"].detach().cpu()
        input_length = int(input_ids.shape[-1])
        grid = [int(value) for value in inputs["image_grid_thw"][0].tolist()]
        n_pre = grid[0] * grid[1] * grid[2]
        merge = int(model.config.vision_config.spatial_merge_size)
        n_llm = grid[0] * (grid[1] // merge) * (grid[2] // merge)
        placeholders = int((input_ids == int(model.config.image_token_id)).sum().item())
        expected = config["expected_visual_tokens"]
        if grid != expected["image_grid_thw"] or n_pre != expected["pre_merge"] or n_llm != expected["projector_output"] or placeholders != expected["llm_image_placeholders"]:
            raise RuntimeError(f"unexplained visual-token accounting: {grid}, {n_pre}, {n_llm}, {placeholders}")
        inputs = inputs.to("cuda")
        torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(**inputs, do_sample=False, num_beams=1, max_new_tokens=int(config["decoding"]["max_new_tokens"]), use_cache=True)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        latencies.append(elapsed)
        output_cpu = output.detach().cpu()
        if output_cpu.shape[-1] < input_length or not torch.equal(output_cpu[:, :input_length], input_ids):
            raise RuntimeError("generated output cannot be isolated from input tokens")
        generated = output_cpu[0, input_length:].tolist()
        raw = processor.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        if raw.encode("utf-8").decode("utf-8") != raw or "\ufffd" in raw:
            raise RuntimeError("Unicode decoding corruption")
        parsed = primary_parse(raw)
        distance = codepoint_edit_distance(parsed, frozen["target"])
        row = {
            **frozen, "input_token_ids": input_ids[0].tolist(), "input_token_count": input_length,
            "full_output_token_ids": output_cpu[0].tolist(), "generated_token_ids": generated,
            "output_slice_start": input_length, "output_prefix_identity": True,
            "raw_output": raw, "parsed_output": parsed,
            "primary_exact": parsed == frozen["target"],
            "nfc_exact": unicodedata.normalize("NFC", parsed) == unicodedata.normalize("NFC", frozen["target"]),
            "error_category": classify_output(parsed, frozen["target"], frozen["opposite_member"]),
            "codepoint_edit_distance": distance, "codepoint_cer": distance / max(1, len(frozen["target"])),
            "thai_output": any("\u0e00" <= char <= "\u0e7f" for char in parsed),
            "output_length_codepoints": len(parsed), "pixel_values_shape": list(inputs["pixel_values"].shape),
            "image_grid_thw": grid, "visual_token_counts": {"pre_merge": n_pre, "projector_output": n_llm, "llm_image_placeholders": placeholders},
            "call_seconds": elapsed,
        }
        records.append(row)
        if len(records) % 25 == 0:
            atomic_write_text(raw_path, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records))
    atomic_write_text(raw_path, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records))
    runtime = {"role": role, "model_load_seconds": load_seconds, "call_count": len(records), "inference_seconds_total": sum(latencies), "peak_cuda_allocated_bytes": int(torch.cuda.max_memory_allocated()), "peak_cuda_reserved_bytes": int(torch.cuda.max_memory_reserved())}
    del model, processor
    gc.collect(); torch.cuda.empty_cache()
    return records, manifest, runtime


def _bootstrap(values: np.ndarray, resamples: int, seed: int) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    return {"estimate": float(values.mean()), "ci_low": float(np.quantile(draws, 0.025)), "ci_high": float(np.quantile(draws, 0.975)), "cluster_count": int(len(values))}


def analyze_records(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    resamples, seed = int(config["analysis"]["bootstrap_resamples"]), int(config["analysis"]["bootstrap_seed"])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[(row["model_role"], row["pair_id"])].append(row)
    pair_rows = []
    for (role, pair_id), rows in sorted(grouped.items()):
        if len(rows) != 8:
            raise RuntimeError(f"pair aggregation count != 8: {role}/{pair_id}")
        pair_rows.append({"model_role": role, "pair_id": pair_id, "component_type": rows[0]["component_type"], "exact_accuracy": float(np.mean([r["primary_exact"] for r in rows])), "cer": float(np.mean([r["codepoint_cer"] for r in rows]))})
    overall = {}
    for role in ("BASE", "SPECIALIZED"):
        rows = [row for row in pair_rows if row["model_role"] == role]
        overall[role] = {"exact_accuracy": _bootstrap(np.array([r["exact_accuracy"] for r in rows]), resamples, seed), "cer": _bootstrap(np.array([r["cer"] for r in rows]), resamples, seed + 1)}
    base = {row["pair_id"]: row["exact_accuracy"] for row in pair_rows if row["model_role"] == "BASE"}
    specialized = {row["pair_id"]: row["exact_accuracy"] for row in pair_rows if row["model_role"] == "SPECIALIZED"}
    delta = np.array([specialized[key] - base[key] for key in sorted(base)])
    components = {}
    for component in sorted({row["component_type"] for row in pair_rows}):
        components[component] = {}
        for role in ("BASE", "SPECIALIZED"):
            values = np.array([row["exact_accuracy"] for row in pair_rows if row["model_role"] == role and row["component_type"] == component])
            components[component][role] = _bootstrap(values, resamples, seed)
    taxonomy = {}
    descriptives = {}
    for role in ("BASE", "SPECIALIZED"):
        rows = [row for row in records if row["model_role"] == role]
        taxonomy[role] = dict(sorted(Counter(row["error_category"] for row in rows).items()))
        descriptives[role] = {
            "thai_output_rate": float(np.mean([row["thai_output"] for row in rows])),
            "mean_output_length_codepoints": float(np.mean([row["output_length_codepoints"] for row in rows])),
            "nfc_exact_accuracy": float(np.mean([row["nfc_exact"] for row in rows])),
            "by_font_size": [{"font_id": key[0], "font_size": key[1], "exact_accuracy": float(np.mean([r["primary_exact"] for r in rows if (r["font_id"], r["font_size"]) == key]))} for key in sorted({(r["font_id"], r["font_size"]) for r in rows})],
        }
    return {"schema_version": 1, "analysis_scope": "S0_OPEN_CALIBRATION_BASELINE_ONLY", "overall": overall, "delta_model_specialized_minus_base": _bootstrap(delta, resamples, seed + 2), "components": components, "error_taxonomy_counts": taxonomy, "descriptives": descriptives, "pair_level": pair_rows, "fixed_accuracy_pass_threshold": None}


def execute_remote_s0(remote_spec_path: Path) -> None:
    spec = json.loads(remote_spec_path.read_text("utf-8")); root = Path.cwd()
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]; artifact_dir.mkdir(parents=True, exist_ok=False)
    failures: dict[str, Any] = {"schema_version": 1, "failures": []}; phase = "configuration"; started = time.perf_counter()
    try:
        config = load_yaml(root / spec["config_path"])
        if config["status"] != "APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY" or any(config["prohibitions"].values()):
            raise RuntimeError("S0 authorization/prohibition contract mismatch")
        source_zip = root / config["source_bundle"]
        if sha256_file(source_zip) != config["source_bundle_sha256"]:
            raise RuntimeError("source bundle hash mismatch")
        design = load_yaml(root / config["source_design"]); inventory = load_yaml(root / config["candidate_inventory"])
        with zipfile.ZipFile(source_zip) as archive:
            render_rows = json.loads(archive.read("render_manifest.json"))
        workload = build_workload(config, design, inventory, render_rows)
        audit = audit_selection(config, design, workload)
        atomic_write_json(artifact_dir / "locked_set_audit.json", audit)
        if not audit["valid"]: raise RuntimeError("selection or locked-set audit failed")
        atomic_write_json(artifact_dir / "workload_manifest.json", {"schema_version": 1, "call_count": len(workload), "calls": workload})
        phase = "cuda_preflight"; gpu = cuda_preflight(spec["requested_accelerator"])
        atomic_write_json(artifact_dir / "environment_manifest.json", {"schema_version": 1, "gpu": gpu, "environment": _environment()})
        phase = "input_extraction"; image_dir = artifact_dir / "input_pngs"; image_dir.mkdir(); images = _prepare_images(source_zip, workload, image_dir)
        phase = "model_execution"; records, manifests, runtimes = [], [], []
        for model_spec in config["models"]:
            model_records, manifest, runtime = _run_model(model_spec, config, workload, images, artifact_dir / f"raw_outputs_{model_spec['role'].lower()}.jsonl")
            records.extend(model_records); manifests.append(manifest); runtimes.append(runtime)
        if len(records) != 1520: raise RuntimeError(f"observed call count {len(records)} != 1520")
        atomic_write_text(artifact_dir / "raw_outputs.jsonl", "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
        phase = "contract_validation"
        cross: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in records: cross[(row["pair_id"], row["condition_id"], row["member"])].append(row)
        if not all(len(rows) == 2 and rows[0]["prompt"] == rows[1]["prompt"] == "OCR:" and rows[0]["image_sha256"] == rows[1]["image_sha256"] and rows[0]["input_token_ids"] == rows[1]["input_token_ids"] for rows in cross.values()):
            raise RuntimeError("cross-model prompt/image/input construction mismatch")
        atomic_write_json(artifact_dir / "model_revision_manifest.json", {"schema_version": 1, "models": manifests})
        atomic_write_json(artifact_dir / "token_accounting_report.json", {"schema_version": 1, "all_calls_expected_full_information_counts": True, "expected": config["expected_visual_tokens"], "call_count": len(records)})
        atomic_write_json(artifact_dir / "runtime_vram_report.json", {"schema_version": 1, "gpu": gpu, "models": runtimes, "total_seconds": time.perf_counter() - started})
        phase = "analysis"; analysis = analyze_records(records, config); atomic_write_json(artifact_dir / "analysis.json", analysis)
        atomic_write_json(artifact_dir / "failure_log.json", failures)
        atomic_write_json(artifact_dir / "manifest.json", {"schema_version": 1, "run_id": spec["run_id"], "run_type": "PADDLE_WAYU_S0_OPEN_CALIBRATION_BASELINE", "status": "S0_COMPLETE_PENDING_HUMAN_REVIEW", "git_sha": spec["git_sha"], "config_sha256": spec["config_sha256"], "call_count": len(records), "pair_count": 95, "locked_pair_count": 0, "terminal_state": "HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION", "created_at_utc": utc_now()})
        atomic_write_text(artifact_dir / "checksums.sha256", _checksums(artifact_dir))
        atomic_write_json(artifact_dir / "SUCCESS.json", {"schema_version": 1, "run_id": spec["run_id"], "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"), "timestamp_utc": utc_now()})
    except BaseException as exc:
        failure = {"phase": phase, "exception_type": type(exc).__name__, "message": str(exc)[:4000], "timestamp_utc": utc_now()}
        failures["failures"].append(failure); atomic_write_json(artifact_dir / "failure_log.json", failures)
        atomic_write_json(artifact_dir / "FAILURE.json", {"schema_version": 1, "run_id": spec["run_id"], "classification": "S0_TECHNICAL_INVALID", **failure})
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--remote-spec", type=Path, required=True)
    execute_remote_s0(parser.parse_args().remote_spec)
