from __future__ import annotations

from pathlib import Path

from labbs2026.stage0.paddle_wayu_u_fffd_protocol_amendment import (
    _derive_s0_fields,
    _literal_ufffd_evidence,
)


def test_amended_derivation_changes_only_ufffd_failure_taxonomy() -> None:
    row = {
        "raw_output": "�",
        "target": "ก",
        "opposite_member": "ข",
    }
    old = _derive_s0_fields(row, amended=False)
    amended = _derive_s0_fields(row, amended=True)
    assert old["raw_output"] == amended["raw_output"] == "�"
    assert old["parsed_output"] == amended["parsed_output"] == "�"
    assert old["primary_exact"] == amended["primary_exact"] is False
    assert old["codepoint_cer"] == amended["codepoint_cer"] == 1.0
    assert old["error_category"] == "non_thai_output"
    assert amended["error_category"] == "output_contract_failure"


def test_non_ufffd_s0_style_output_is_semantically_identical() -> None:
    row = {
        "raw_output": " ก ",
        "target": "ก",
        "opposite_member": "ข",
    }
    assert _derive_s0_fields(row, amended=False) == _derive_s0_fields(row, amended=True)


def test_literal_ufffd_evidence_requires_exact_open_diagnostic_sequence() -> None:
    value = {
        "synthetic_tokenizer_diagnostic": {
            role: {
                "literal_ufffd_case": {
                    "token_ids": [94377],
                    "token_pieces": ["�"],
                    "processor_decode": "�",
                    "tokenizer_decode": "�",
                    "processor_contains_ufffd": True,
                    "processor_equals_tokenizer": True,
                }
            }
            for role in ("BASE", "SPECIALIZED")
        }
    }
    assert _literal_ufffd_evidence(value)["valid"]


def test_validator_source_never_reads_attempt4_scientific_content() -> None:
    source = Path(
        "src/labbs2026/stage0/paddle_wayu_u_fffd_protocol_amendment.py"
    ).read_text("utf-8")
    assert "zipfile" not in source
    assert ".read_text" not in source.split("attempt4 = attempt4_zip_path.resolve()", 1)[1]
