"""Report-assembly tests: separation of concerns is the property under test."""

from __future__ import annotations

import pytest

from labbs2026.region_ocr.report import (
    absolute_cer,
    build_report,
    component_breakdown,
    generation_health,
)

BUDGETS = ("75", "50", "25")
KI_TONE = "\u0e01\u0e35\u0e48"
KI = "\u0e01\u0e35"


def _records(n=6):
    out = []
    conditions = ["FULL"] + [f"{p}_{b}" for b in BUDGETS for p in ("PRUNE_GRID", "RR")]
    for i in range(n):
        for cond in conditions:
            out.append({
                "image_id": f"img_{i:03d}",
                "source_photo_id": f"ph_{i // 2}",
                "reference": KI_TONE,
                "parsed_output": KI_TONE if cond == "FULL" else KI,
                "condition_id": cond,
                "reached_max_new_tokens": False,
            })
    return out


def test_generation_health_is_reported_per_condition_and_apart_from_cer() -> None:
    records = _records(3)
    for r in records:
        if r["condition_id"] == "PRUNE_GRID_25":
            r["reached_max_new_tokens"] = True
            r["parsed_output"] = ""
    health = generation_health(records)
    assert health["PRUNE_GRID_25"]["truncated"] == 3
    assert health["PRUNE_GRID_25"]["empty"] == 3
    assert health["FULL"]["truncated"] == 0
    # and it does not leak into the CER table
    assert "truncated" not in absolute_cer(records)["FULL"]


def test_absolute_cer_reports_macro_and_micro_per_condition() -> None:
    table = absolute_cer(_records(4))
    assert table["FULL"]["macro_cer"] == pytest.approx(0.0)
    assert table["RR_50"]["macro_cer"] == pytest.approx(1 / 3)
    assert "micro_cer" in table["RR_50"]


def test_component_breakdown_is_labelled_diagnostic_only() -> None:
    out = component_breakdown(_records(2))
    assert out["status"] == "DESCRIPTIVE_DIAGNOSTIC_ONLY"
    tone = out["by_condition"]["RR_50"]["TONE_MARK"]
    assert tone["deletion"] == 2  # both regions dropped the tone mark
    assert out["by_condition"]["FULL"]["TONE_MARK"]["deletion"] == 0


def test_build_report_carries_both_populations_and_the_caveats() -> None:
    report = build_report(_records(8), budgets=BUDGETS, resamples=50, seed=1,
                          execution_failures=0)
    assert report["status"] == "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE"
    assert report["primary"]["population"] == "ALL_ELIGIBLE"
    assert report["secondary"]["population"] == "CER_FULL_ZERO"
    assert report["failures_scored_as_cer_one"] is False
    assert any("redundancy" in item for item in report["limitations"])
    assert any("non-negative by construction" in item for item in report["limitations"])


def test_build_report_counts_failures_without_scoring_them() -> None:
    report = build_report(_records(4), budgets=BUDGETS, resamples=20, seed=2,
                          execution_failures=7)
    assert report["execution_failures"] == 7
    assert report["observations"] == 4 * 7
