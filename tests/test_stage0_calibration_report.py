from labbs2026.stage0.calibration_report import _diagnostic_rows, _raw_format_audit


def _row(raw: str, expected: str | None = "A") -> dict:
    return {
        "raw_output": raw,
        "expected_label": expected,
        "candidate_a": "กา",
        "candidate_b": "ก่า",
    }


def test_diagnostic_leading_label_does_not_change_registered_raw_output() -> None:
    original = _row("A. กา")

    transformed = _diagnostic_rows([original])[0]

    assert transformed["parsed_output"] == "A"
    assert transformed["is_correct"] is True
    assert original == _row("A. กา")


def test_raw_format_audit_keeps_exact_parser_distinct_from_posthoc_shape() -> None:
    audit = _raw_format_audit([_row("A. กา"), _row("B", expected="B")])

    assert audit["registered_exact_ab_count"] == 1
    assert audit["leading_label_shape_count"] == 2
    assert audit["exact_selected_candidate_echo_count"] == 1
