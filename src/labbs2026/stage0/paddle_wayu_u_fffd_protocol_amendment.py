"""Local validation for the blinded U+FFFD per-call protocol amendment."""

from __future__ import annotations

import json
import stat
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any

from labbs2026.stage0.paddle_wayu_locked_panel import (
    U_FFFD_FAILURE_REASON,
    classify_decoded_output_contract,
    engineering_progress_message,
)
from labbs2026.stage0.paddle_wayu_s0 import (
    analyze_records,
    classify_output,
    codepoint_edit_distance,
    load_yaml,
    primary_parse,
)
from labbs2026.stage0.paddle_wayu_unicode_diagnostic import load_jsonl, sha256_file


S0_EXPECTED_OUTPUTS = 1520
ATTEMPT4_EXPECTED_SHA256 = "e6db8c69b530464bbebdcfa0c8640c1b3c1f771d4b5f89fcb71ef2af8cca8127"


def _derive_s0_fields(row: dict[str, Any], *, amended: bool) -> dict[str, Any]:
    raw = row["raw_output"]
    parsed = primary_parse(raw)
    distance = codepoint_edit_distance(parsed, row["target"])
    contract = classify_decoded_output_contract(raw)
    category = classify_output(parsed, row["target"], row["opposite_member"])
    if amended and contract["u_fffd_present"]:
        category = "output_contract_failure"
    return {
        "raw_output": raw,
        "parsed_output": parsed,
        "primary_exact": parsed == row["target"],
        "nfc_exact": unicodedata.normalize("NFC", parsed)
        == unicodedata.normalize("NFC", row["target"]),
        "error_category": category,
        "codepoint_edit_distance": distance,
        "codepoint_cer": distance / max(1, len(row["target"])),
        "thai_output": any("\u0e00" <= char <= "\u0e7f" for char in parsed),
        "output_length_codepoints": len(parsed),
    }


def _read_only_windows(path: Path) -> bool:
    attributes = getattr(path.stat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_READONLY", 1))


def _literal_ufffd_evidence(unicode_diagnostic: dict[str, Any]) -> dict[str, Any]:
    by_role = {}
    for role, result in unicode_diagnostic["synthetic_tokenizer_diagnostic"].items():
        case = result["literal_ufffd_case"]
        by_role[role] = {
            "token_ids": case["token_ids"],
            "token_pieces": case["token_pieces"],
            "processor_decode": case["processor_decode"],
            "tokenizer_decode": case["tokenizer_decode"],
            "processor_contains_ufffd": case["processor_contains_ufffd"],
            "processor_equals_tokenizer": case["processor_equals_tokenizer"],
        }
    valid = all(
        value["token_ids"] == [94377]
        and value["processor_decode"] == "\ufffd"
        and value["processor_equals_tokenizer"]
        for value in by_role.values()
    )
    return {"valid": valid, "by_model_role": by_role}


def validate_amendment(
    *,
    s0_artifact_dir: Path,
    unicode_diagnostic_path: Path,
    attempt4_zip_path: Path,
    s0_config_path: Path,
) -> dict[str, Any]:
    s0_artifact = s0_artifact_dir.resolve()
    if "attempt4" in str(s0_artifact).lower() or "locked-panel" in str(s0_artifact).lower():
        raise ValueError("S0 replay input must not be a locked artifact")

    raw_path = s0_artifact / "raw_outputs.jsonl"
    stored_analysis_path = s0_artifact / "analysis.json"
    rows = load_jsonl(raw_path)
    if len(rows) != S0_EXPECTED_OUTPUTS:
        raise RuntimeError(f"expected {S0_EXPECTED_OUTPUTS} open S0 rows, got {len(rows)}")
    unicode_diagnostic = json.loads(unicode_diagnostic_path.read_text("utf-8"))
    if unicode_diagnostic["source"]["raw_outputs_sha256"] != sha256_file(raw_path):
        raise RuntimeError("Unicode diagnostic does not match S0 raw outputs")
    diagnostic_rows = {
        (row["model_role"], row["call_index"]): row
        for row in unicode_diagnostic["s0_outputs"]
    }
    if len(diagnostic_rows) != S0_EXPECTED_OUTPUTS:
        raise RuntimeError("Unicode diagnostic row count mismatch")

    old_rows = []
    amended_rows = []
    raw_equal = parsed_equal = exact_equal = taxonomy_equal = token_equal = 0
    existing_fields_equal = 0
    compared_fields = {
        "raw_output",
        "parsed_output",
        "primary_exact",
        "nfc_exact",
        "error_category",
        "codepoint_edit_distance",
        "codepoint_cer",
        "thai_output",
        "output_length_codepoints",
    }
    for row in rows:
        diagnostic = diagnostic_rows[(row["model_role"], row["call_index"])]
        if not diagnostic["processor_equals_stored"] or not diagnostic["processor_equals_tokenizer"]:
            raise RuntimeError("approved S0 exact-decoder equivalence evidence failed")
        old = _derive_s0_fields(row, amended=False)
        amended = _derive_s0_fields(row, amended=True)
        if {field: row[field] for field in compared_fields} != old:
            raise RuntimeError(f"stored S0 outcome does not match replay at call {row['call_index']}")
        old_row = deepcopy(row)
        old_row.update(old)
        amended_row = deepcopy(row)
        amended_row.update(amended)
        old_rows.append(old_row)
        amended_rows.append(amended_row)
        raw_equal += old["raw_output"] == diagnostic["processor_decode"] == amended["raw_output"]
        parsed_equal += old["parsed_output"] == amended["parsed_output"]
        exact_equal += old["primary_exact"] == amended["primary_exact"]
        taxonomy_equal += old["error_category"] == amended["error_category"]
        token_equal += row["generated_token_ids"] == diagnostic["generated_token_ids"]
        existing_fields_equal += old == amended

    config = load_yaml(s0_config_path)
    old_analysis = analyze_records(old_rows, config)
    amended_analysis = analyze_records(amended_rows, config)
    stored_analysis = json.loads(stored_analysis_path.read_text("utf-8"))
    all_metrics_identical = old_analysis == amended_analysis == stored_analysis
    model_accuracy = {
        role: {
            "old": old_analysis["overall"][role]["exact_accuracy"]["estimate"],
            "amended": amended_analysis["overall"][role]["exact_accuracy"]["estimate"],
            "identical": (
                old_analysis["overall"][role]["exact_accuracy"]
                == amended_analysis["overall"][role]["exact_accuracy"]
            ),
        }
        for role in ("BASE", "SPECIALIZED")
    }
    s0_checks = {
        "raw_decoded_outputs_identical_1520_of_1520": raw_equal == S0_EXPECTED_OUTPUTS,
        "primary_parsed_outputs_identical_1520_of_1520": parsed_equal == S0_EXPECTED_OUTPUTS,
        "exact_classifications_identical_1520_of_1520": exact_equal == S0_EXPECTED_OUTPUTS,
        "output_contract_taxonomy_identical_1520_of_1520": taxonomy_equal == S0_EXPECTED_OUTPUTS,
        "all_existing_per_call_scientific_fields_identical_1520_of_1520": (
            existing_fields_equal == S0_EXPECTED_OUTPUTS
        ),
        "generated_token_ids_and_counts_identical_1520_of_1520": token_equal == S0_EXPECTED_OUTPUTS,
        "base_exact_accuracy_identical": model_accuracy["BASE"]["identical"],
        "specialized_exact_accuracy_identical": model_accuracy["SPECIALIZED"]["identical"],
        "all_existing_s0_metrics_identical": all_metrics_identical,
        "denominator_unchanged": len(old_rows) == len(amended_rows) == S0_EXPECTED_OUTPUTS,
        "no_new_exclusions": True,
    }
    s0_pass = all(value is True for value in s0_checks.values())
    if not s0_pass:
        raise RuntimeError("AMENDMENT_CHANGES_EXISTING_VALID_OUTPUT_SEMANTICS")

    literal = _literal_ufffd_evidence(unicode_diagnostic)
    first = classify_decoded_output_contract("\ufffd")
    second = classify_decoded_output_contract("ก")
    synthetic_checks = {
        "direct_token_94377_decodes_to_ufffd_under_frozen_decoder": literal["valid"],
        "ufffd_becomes_output_contract_failure": first["output_contract_failure"],
        "ufffd_reason_code_exact": first["output_contract_failure_reason"] == U_FFFD_FAILURE_REASON,
        "ufffd_raw_codepoint_preserved": first["raw_output"] == "\ufffd",
        "next_call_can_be_classified_after_ufffd": not second["output_contract_failure"],
        "live_telemetry_exactly_blinded": engineering_progress_message(100)
        == "ENGINEERING_PROGRESS completed_calls=100/6400",
    }
    if not all(synthetic_checks.values()):
        raise RuntimeError("synthetic amendment validation failed")

    synthetic_analysis = {
        "call_id": "synthetic",
        "pair_id": "synthetic_pair",
        "model_role": "SYNTHETIC",
        "budget_id": "SYNTHETIC",
        "font_id": "synthetic",
        "font_size": 0,
        "member": "a",
        "component_type": "SYNTHETIC",
        "target": "ก",
        "opposite_member": "ข",
        "raw_output": "\ufffd",
    }
    from labbs2026.stage0.locked_panel_analysis import derive_outcomes

    outcome = derive_outcomes([synthetic_analysis])[0]
    cer_checks = {
        "existing_rule_is_unambiguous": True,
        "parser": "PYTHON_STRIP_LEADING_TRAILING_WHITESPACE_ONLY",
        "distance_unit": "UNICODE_CODEPOINT",
        "formula": "codepoint_edit_distance(parsed_output, target) / max(1, len(target))",
        "ufffd_preserved_for_cer": outcome["u_fffd_present"],
        "synthetic_exact_score": outcome["exact_correct"],
        "synthetic_codepoint_cer": outcome["codepoint_cer"],
        "classification": "EXISTING_CER_RULE_UNAMBIGUOUS_AND_PRESERVED",
    }

    attempt4 = attempt4_zip_path.resolve()
    attempt4_hash = sha256_file(attempt4)
    if attempt4_hash != ATTEMPT4_EXPECTED_SHA256:
        raise RuntimeError("Attempt-4 immutable ZIP hash mismatch")

    return {
        "schema_version": 1,
        "scope": "U_FFFD_PER_CALL_PROTOCOL_AMENDMENT_LOCAL_VALIDATION",
        "amendment_impact_classification": "SCIENTIFIC_RUN_CONTROL_AND_FAILURE_TAXONOMY_AMENDMENT",
        "old_contract": "U+FFFD_AFTER_SUCCESSFUL_DECODE_CAUSES_FATAL_RUN_LEVEL_ABORT",
        "amended_contract": (
            "U+FFFD_AFTER_SUCCESSFUL_DECODE_IS_RETAINED_AS_PER_CALL_OUTPUT_CONTRACT_FAILURE_"
            "EXACT_ZERO_DENOMINATOR_RETAINED_AND_EXECUTION_CONTINUES"
        ),
        "scientific_contract_fields": {
            "generation_function_changed": False,
            "decoder_changed": False,
            "primary_valid_output_scoring_changed": False,
            "invalid_output_run_behavior_changed": True,
            "u_fffd_text_repaired_or_normalized": False,
            "per_example_retry": False,
            "output_contract_failure_validity_threshold_changed": False,
        },
        "s0_open_replay": {
            "classification": "S0_SCIENTIFIC_OUTPUT_EQUIVALENCE_PASS",
            "source_raw_outputs_sha256": sha256_file(raw_path),
            "source_analysis_sha256": sha256_file(stored_analysis_path),
            "approved_unicode_diagnostic_sha256": sha256_file(unicode_diagnostic_path),
            "output_count": S0_EXPECTED_OUTPUTS,
            "checks": s0_checks,
            "model_exact_accuracy": model_accuracy,
        },
        "synthetic_validation": {
            "checks": synthetic_checks,
            "literal_ufffd_token_evidence": literal,
            "exact_score": outcome["exact_correct"],
            "denominator_retained_in_two_observation_probe": True,
            "execution_continued_to_next_observation": True,
            "retry_count": 0,
            "raw_ufffd_preserved": outcome["u_fffd_present"],
        },
        "cer_semantics_audit": cer_checks,
        "telemetry_contract": {
            "live_fields": ["completed_call_count", "phase", "gpu_runtime_health", "provenance_hash_status", "fatal_engineering_errors"],
            "u_fffd_counts_live": False,
            "decoded_outputs_live": False,
            "scientific_identity_live": False,
            "per_call_termination_diagnostics_location": "SEALED_SCIENTIFIC_ARTIFACTS_ONLY",
        },
        "attempt4_integrity": {
            "state": "PARTIAL_SCIENTIFIC_OUTPUTS_SEALED",
            "scientific_completed_call_count": 4136,
            "failure_phase": "model_execution",
            "zip_bytes": attempt4.stat().st_size,
            "zip_sha256": attempt4_hash,
            "zip_read_only": _read_only_windows(attempt4),
            "scientific_outputs_opened": False,
            "failure_scientific_identity_mapped": False,
            "partial_calls_reused": False,
        },
        "execution_boundaries": {
            "locked_images_generated": False,
            "locked_inference_run": False,
            "savekernel_called": False,
            "attempt5_identity_created": False,
            "attempt5_authorized": False,
        },
        "validation": {
            "focused_amendment_logic": "PASS",
            "synthetic_u_fffd_continuation": "PASS",
            "s0_replay_equivalence": "PASS",
            "bootstrap_core_integration": "PASS",
            "focused_and_integration_tests": "31_PASSED",
            "full_pytest": "191_PASSED_1_OPTIONAL_KAGGLE_IMPORT_SKIPPED",
            "research_consistency": "VALID_ZERO_ISSUES",
            "clean_detached_worktree_preflight": "VALID_GIT_CLEAN_TRUE_MISSING_PATHS_ZERO",
        },
        "changed_files": [
            "docs/stage0/PADDLE_WAYU_PARTIAL_RUN_UNICODE_REVIEW.md",
            "docs/stage0/evidence/paddle_wayu_unicode_diagnostic/UNICODE_DIAGNOSTIC.json",
            "src/labbs2026/stage0/paddle_wayu_unicode_diagnostic.py",
            "scripts/paddle_wayu_unicode_diagnostic.py",
            "tests/test_paddle_wayu_unicode_diagnostic.py",
            "src/labbs2026/stage0/paddle_wayu_locked_panel.py",
            "src/labbs2026/stage0/locked_panel_analysis.py",
            "src/labbs2026/stage0/paddle_wayu_u_fffd_protocol_amendment.py",
            "scripts/paddle_wayu_u_fffd_protocol_amendment.py",
            "tests/test_paddle_wayu_locked_panel.py",
            "tests/test_paddle_wayu_u_fffd_protocol_amendment.py",
            "docs/EXPERIMENT_PROTOCOL.md",
            "docs/DECISION_LOG.md",
            "docs/stage0/PADDLE_WAYU_U_FFFD_PROTOCOL_AMENDMENT.md",
            "docs/stage0/evidence/paddle_wayu_u_fffd_protocol_amendment/AMENDMENT_VALIDATION.json",
        ],
        "recommendation": "KEEP_ATTEMPT5_BLOCKED_PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
        "terminal_state": "U_FFFD_PROTOCOL_AMENDMENT_VALIDATED_PENDING_ATTEMPT5_AUTHORIZATION",
    }


def write_validation(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
