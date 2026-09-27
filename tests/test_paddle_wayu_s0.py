import json
import zipfile
from pathlib import Path

import pytest

from labbs2026.stage0.paddle_wayu_s0 import (
    analyze_records,
    audit_selection,
    build_workload,
    classify_output,
    codepoint_edit_distance,
    load_yaml,
    primary_parse,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/paddle_wayu_s0_open_calibration.yaml"


def _frozen():
    config = load_yaml(CONFIG)
    design = load_yaml(ROOT / config["source_design"])
    inventory = load_yaml(ROOT / config["candidate_inventory"])
    with zipfile.ZipFile(ROOT / config["source_bundle"]) as archive:
        render_rows = json.loads(archive.read("render_manifest.json"))
    return config, design, build_workload(config, design, inventory, render_rows)


def test_primary_parser_and_error_taxonomy_are_frozen():
    assert primary_parse(" \nก่า\t ") == "ก่า"
    assert primary_parse("ก่า\nข่า") == "ก่า\nข่า"
    assert classify_output("ก่า", "ก่า", "กา") == "exact_target"
    assert classify_output("กา", "ก่า", "กา") == "opposite_member_substitution"
    assert classify_output("", "ก่า", "กา") == "deletion_or_empty"
    assert classify_output("ก่า ข่า", "ก่า", "กา") == "output_contract_failure"
    assert classify_output("ข่า", "ก่า", "กา") == "other_thai_substitution"
    assert classify_output("abc", "ก่า", "กา") == "non_thai_output"
    assert codepoint_edit_distance("ก่า", "กา") == 1


def test_exact_workload_and_locked_audit():
    config, design, workload = _frozen()
    assert len(workload) == 1520
    assert sum(row["model_role"] == "BASE" for row in workload) == 760
    assert sum(row["model_role"] == "SPECIALIZED" for row in workload) == 760
    assert len({row["pair_id"] for row in workload}) == 95
    assert len({(row["pair_id"], row["condition_id"], row["member"]) for row in workload}) == 760
    audit = audit_selection(config, design, workload)
    assert audit["valid"]
    assert audit["locked_pair_count"] == 0
    assert set(audit["component_pair_counts"].values()) == {19}


def test_pair_clustered_analysis_uses_eight_observations_per_pair():
    config = load_yaml(CONFIG)
    config["analysis"]["bootstrap_resamples"] = 100
    records = []
    for role, exact in (("BASE", False), ("SPECIALIZED", True)):
        for pair_id, component in (("p1", "TONE_MARK"), ("p2", "TONE_MARK")):
            for index in range(8):
                records.append({
                    "model_role": role, "pair_id": pair_id,
                    "component_type": component, "primary_exact": exact,
                    "codepoint_cer": 0.0 if exact else 1.0,
                    "error_category": "exact_target" if exact else "other_thai_substitution",
                    "thai_output": True, "output_length_codepoints": 2,
                    "nfc_exact": exact, "font_id": "font", "font_size": 72,
                })
    result = analyze_records(records, config)
    assert result["overall"]["BASE"]["exact_accuracy"]["estimate"] == 0.0
    assert result["overall"]["SPECIALIZED"]["exact_accuracy"]["estimate"] == 1.0
    assert result["delta_model_specialized_minus_base"]["estimate"] == 1.0
    assert len(result["pair_level"]) == 4


def test_analysis_rejects_incomplete_pair_cluster():
    config = load_yaml(CONFIG)
    with pytest.raises(RuntimeError, match="pair aggregation count"):
        analyze_records([{"model_role": "BASE", "pair_id": "p", "component_type": "TONE_MARK"}], config)
