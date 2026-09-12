"""Execute and analyze the frozen Qwen3.5 measurement-contract pilot."""

from __future__ import annotations

import argparse
import copy
import io
import json
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

from labbs2026.adapters.factory import build_adapter
from labbs2026.kaggle import atomic_write_json, atomic_write_text, cuda_preflight, load_runtime, sha256_file, write_failure
from labbs2026.stage0.bundle import extract_and_verify_calibration_bundle
from labbs2026.stage0.kaggle_backend import _checksums
from labbs2026.stage0.margin_diagnostic import _cluster_bootstrap, _mean
from labbs2026.stage0.measurement_contract_pilot import _anchor_mask, add_surrounding_layout
from labbs2026.step3 import environment_record, peak_rss_monitor, seed_everything


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def normalize_output(raw: str) -> str:
    return raw.replace("\r\n", "\n").replace("\r", "\n").strip()


def classify_output(raw: str, displayed: str, opposite: str) -> dict[str, Any]:
    normalized = normalize_output(raw)
    if "\n" in normalized:
        taxonomy = "output_contract_failure"
    elif normalized == "":
        taxonomy = "deletion"
    elif normalized == displayed:
        taxonomy = "correct_target"
    elif normalized == opposite:
        taxonomy = "opposite_member_substitution"
    else:
        taxonomy = "other_substitution"
    return {"normalized_output": normalized, "taxonomy": taxonomy, "target_correct": taxonomy == "correct_target"}


def _levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _selected(config: dict[str, Any]) -> list[str]:
    return [pair for group in config["selection"]["selected_pairs"].values() for pair in group]


def execute_remote(spec_path: Path) -> None:
    spec, source = json.loads(spec_path.read_text("utf-8")), Path.cwd()
    artifact = Path(spec["output_root"]) / spec["run_id"]
    artifact.mkdir(parents=True, exist_ok=True)
    phase, started = "preflight", time.perf_counter()
    try:
        config = _yaml(source / spec["config_path"])
        runtime = load_runtime(source / spec["runtime_path"])
        gpu = cuda_preflight(spec["requested_accelerator"])
        if config["status"] != "FROZEN_AUTHORIZED_FOR_PILOT_INFERENCE":
            raise RuntimeError("pilot is not frozen and authorized")
        selected = _selected(config)
        if len(selected) != 25 or len(set(selected)) != 25:
            raise RuntimeError("selected pair contract mismatch")
        phase = "open_bundle_verification"
        input_dir = Path(tempfile.mkdtemp(prefix="labbs-contract-pilot-")) / "extracted"
        bundle = extract_and_verify_calibration_bundle(source / config["source_bundle"], input_dir, config["source_bundle_sha256"])
        if bundle["locked_validation_pair_count_in_bundle"] != 0:
            raise RuntimeError("locked pair found in source bundle")
        pairs = {r["pair_id"]: r for r in json.loads((input_dir / "resolved_pairs.json").read_text("utf-8")) if r["pair_id"] in selected}
        renders = [r for r in json.loads((input_dir / "render_manifest.json").read_text("utf-8")) if r["pair_id"] in selected and r["condition_id"] in config["render_conditions"]]
        if set(pairs) != set(selected) or len(renders) != 100:
            raise RuntimeError("open pilot allocation mismatch")
        pair_inventory = {r["pair_id"]: r for r in _yaml(source / "configs/stage0/candidate_pairs.yaml")["pairs"]}
        model_config = copy.deepcopy(_yaml(source / config["model"]["config"]))
        model_config["generation"] = {
            "do_sample": config["decoding"]["do_sample"],
            "max_new_tokens": config["decoding"]["max_new_tokens"],
            "min_new_tokens": config["decoding"]["min_new_tokens"],
            "chat_template_kwargs": {"enable_thinking": config["decoding"]["enable_thinking"]},
            "output_contract": {"mode": "free_generation"},
        }
        adapter = build_adapter(model_config, source, runtime)
        seed_everything(int(config["uncertainty"]["seed"]))
        prompt = config["prompts"][config["conditions"]["B_isolated_transcription"]["prompt_id"]]
        cells, item_y = config["line_layout"]["cells_half_open"], config["line_layout"]["vertical_item_interval"]
        target_cell = (cells["target"][0], item_y[0], cells["target"][1], item_y[1])
        anchor_cells = [tuple(cells[k]) for k in ("anchor_1", "anchor_2", "anchor_3", "anchor_4")]
        rectangles = [(r["x"][0], r["y"][0], r["x"][1], r["y"][1]) for r in config["line_layout"]["separator_rectangles_half_open"]]
        rows, stimulus, failures = [], [], []
        with peak_rss_monitor() as memory:
            for render in sorted(renders, key=lambda r: (r["component_type"], r["pair_id"], r["condition_id"])):
                mask = _anchor_mask(font_path=source / render["font_path"], font_size=int(render["font_size"]), canvas_size=tuple(config["line_layout"]["canvas_size"]), item_y=tuple(item_y), anchor_cells=anchor_cells, anchors=config["conditions"]["C_line_layout_transcription"]["anchors"], separator_rectangles=rectangles)
                pair = pair_inventory[render["pair_id"]]
                for member in config["members"]:
                    displayed, opposite = pair[f"text_{member}"], pair[f"text_{'b' if member == 'a' else 'a'}"]
                    b_path = input_dir / render[f"image_{member}_path"]
                    c_path = input_dir / "condition_C" / f"{render['pair_id']}__{member}__{render['condition_id']}.png"
                    c_path.parent.mkdir(parents=True, exist_ok=True)
                    c_image, identity = add_surrounding_layout(Image.open(b_path).convert("RGB"), anchor_mask=mask, target_cell=target_cell)
                    c_image.save(c_path, optimize=False)
                    stimulus.append({"pair_id": render["pair_id"], "component_type": render["component_type"], "condition_id": render["condition_id"], "member": member, "B_png_sha256": sha256_file(b_path), "C_png_sha256": sha256_file(c_path), **identity})
                    for condition, image_path in (("B", b_path), ("C", c_path)):
                        observation_id = f"{render['pair_id']}|{member}|{render['condition_id']}|{condition}"
                        phase = f"condition_{condition}"
                        try:
                            result = adapter.transcribe_target(image_path, prompt, min_new_tokens=int(config["decoding"]["min_new_tokens"]))
                            scored = classify_output(result["raw_output"], displayed, opposite)
                            rows.append({"observation_id": observation_id, "pair_id": render["pair_id"], "component_type": render["component_type"], "condition_id": render["condition_id"], "displayed_member": member, "displayed_text": displayed, "opposite_text": opposite, "condition": condition, **scored, "raw_output": result["raw_output"], "generated_token_ids": result["generated_token_ids"], "visual_stage_metadata": result["visual_stage_metadata"], "resolved_generation_config": result["resolved_generation_config"], "raw_codepoint_edit_distance": _levenshtein(result["raw_output"], displayed)})
                        except BaseException as exc:
                            failures.append({"observation_id": observation_id, "phase": phase, "message": str(exc)[:1000]})
        _write_jsonl(artifact / "BC_raw_outputs.jsonl", rows)
        _write_jsonl(artifact / "stimulus_manifest.jsonl", stimulus)
        atomic_write_json(artifact / "execution_failures.json", failures)
        if failures or len(rows) != 400 or len(stimulus) != 200 or any(r["target_pixel_identity"] != "PASS" for r in stimulus):
            raise RuntimeError("pilot execution incomplete")
        counts = sorted({r["visual_stage_metadata"]["llm_visual_token_count"] for r in rows})
        if counts != [196]:
            raise RuntimeError(f"visual-token contract changed: {counts}")
        atomic_write_json(artifact / "runtime.json", {"schema_version": 1, "gpu_preflight": gpu, "environment": environment_record(), "frozen_environment_contract": spec["environment_contract"], "model_load_seconds": adapter.model_load_seconds, "peak_rss_bytes": memory["peak_rss_bytes"], "total_seconds": time.perf_counter() - started})
        atomic_write_json(artifact / "submission_manifest.json", {"schema_version": 1, "run_id": spec["run_id"], "git_sha": spec["git_sha"], "B_rows": 200, "C_rows": 200, "selected_pair_count": 25, "locked_pair_count": 0, "locked_validation_pair_count_exposed_to_model": 0, "target_pixel_identity_pass_count": 200, "visual_token_counts": counts, "compression_status": "NOT_RUN", "gate_0_status": "NOT_RUN", "backbone_screening_status": "NOT_RUN", "post_outcome_tuning": False})
        atomic_write_json(artifact / "run_spec.json", spec)
        atomic_write_text(artifact / "checksums.sha256", _checksums(artifact))
        atomic_write_json(artifact / "SUCCESS.json", {"schema_version": 1, "run_id": spec["run_id"], "checksums_sha256": sha256_file(artifact / "checksums.sha256")})
    except BaseException as exc:
        write_failure(artifact, spec["run_id"], phase, exc)
        raise


def _interval(rows: list[dict[str, Any]], key: str, config: dict[str, Any]) -> dict[str, Any]:
    u = config["uncertainty"]
    return _cluster_bootstrap(rows, _mean(key), seed=int(u["seed"]), resamples=int(u["resamples"]), confidence=float(u["confidence_level"]))


def analyze(artifact: Path, output: Path, config_path: Path, a_path: Path) -> dict[str, Any]:
    config, a_rows, bc = _yaml(config_path), _jsonl(a_path), _jsonl(artifact / "BC_raw_outputs.jsonl")
    key = lambda r: (r["pair_id"], r["displayed_member"], r["condition_id"])
    a, b, c = {key(r): r for r in a_rows}, {key(r): r for r in bc if r["condition"] == "B"}, {key(r): r for r in bc if r["condition"] == "C"}
    if not (len(a) == len(b) == len(c) == 200 and set(a) == set(b) == set(c)):
        raise RuntimeError("A/B/C paired key mismatch")
    combined = []
    for k in sorted(a):
        combined.append({"pair_id": k[0], "component_type": b[k]["component_type"], "A": float(a[k]["A_target_score"]), "B": float(b[k]["target_correct"]), "C": float(c[k]["target_correct"]), "delta_interface": float(b[k]["target_correct"]) - float(a[k]["A_target_score"]), "delta_surrounding": float(c[k]["target_correct"]) - float(b[k]["target_correct"])})
    metrics = {name: _interval(combined, name, config) for name in ("A", "B", "C", "delta_interface", "delta_surrounding")}
    per_component = {}
    for component in sorted({r["component_type"] for r in combined}):
        subset = [r for r in combined if r["component_type"] == component]
        per_component[component] = {name: _interval(subset, name, config) for name in ("A", "B", "C", "delta_interface", "delta_surrounding")}
    taxonomy = {condition: dict(Counter(r["taxonomy"] for r in bc if r["condition"] == condition)) for condition in ("B", "C")}
    taxonomy_by_component = {component: {condition: dict(Counter(r["taxonomy"] for r in bc if r["condition"] == condition and r["component_type"] == component)) for condition in ("B", "C")} for component in per_component}
    important = {name: metrics[name]["estimate"] >= config["primary_contrasts"]["important_effect_if_point_at_least"] and metrics[name]["ci_low"] > config["primary_contrasts"]["important_effect_if_ci_low_above"] for name in ("delta_interface", "delta_surrounding")}
    component_flag = False
    for name in important:
        vals = [per_component[x][name]["estimate"] for x in per_component]
        component_flag |= sum(v > 0 for v in vals) >= 1 and sum(v < 0 for v in vals) >= 1 and max(vals) - min(vals) >= config["decision_rule"]["component_flag"]["minimum_range_between_component_point_estimates"]
    failure_flag = False
    for condition in ("B", "C"):
        overall = taxonomy[condition].get("output_contract_failure", 0) / 200
        failure_flag |= overall >= config["decision_rule"]["failure_flag"]["output_contract_failure_rate_at_least"]
        for component in per_component:
            failure_flag |= taxonomy_by_component[component][condition].get("output_contract_failure", 0) / 40 >= config["decision_rule"]["failure_flag"]["output_contract_failure_rate_at_least"]
    if component_flag or failure_flag:
        decision = "MIXED_TARGETED_INSTRUMENT_REVIEW"
    elif any(important.values()):
        decision = "PIVOT_MEASUREMENT_DESIGN_FOR_FURTHER_OPEN_CALIBRATION"
    elif all(metrics[name]["ci_high"] <= config["primary_contrasts"]["sesoi_absolute"] for name in important):
        decision = "SECONDARY_BACKBONE_SCREENING"
    else:
        decision = "INCONCLUSIVE"
    report = {"schema_version": 1, "evidence_scope": "OPEN_CALIBRATION_ONLY_MEASUREMENT_DIAGNOSTIC", "independent_unit": "pair_id", "pair_count": 25, "locked_pair_count": 0, "metrics": metrics, "important_effect": important, "error_taxonomy": taxonomy, "error_taxonomy_by_component": taxonomy_by_component, "per_component_descriptive": per_component, "interpretability_flags": {"component_flag": component_flag, "output_contract_failure_flag": failure_flag}, "frozen_decision": decision, "gate_0_status": "NOT_RUN", "compression_status": "NOT_RUN", "human_review_checkpoint": "STOP"}
    output.mkdir(parents=True, exist_ok=False)
    atomic_write_json(output / "measurement_contract_pilot_analysis.json", report)
    _write_jsonl(output / "paired_observations.jsonl", combined)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path)
    args = parser.parse_args()
    if args.remote_spec:
        execute_remote(args.remote_spec)
        return 0
    raise SystemExit("use scripts/stage0_qwen35_measurement_contract_pilot.py")


if __name__ == "__main__":
    raise SystemExit(main())
