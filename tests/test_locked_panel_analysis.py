import pytest

from labbs2026.stage0.locked_panel_analysis import (
    did_analysis,
    full_validity,
    registered_glmm_uses_fallback,
)


def _rows() -> list[dict]:
    rows = []
    for pair_index in range(100):
        pair_id = f"p{pair_index:03d}"
        for model in ("BASE", "SPECIALIZED"):
            for budget in ("B256_FULL", "B196", "B121", "B64"):
                for member in ("a", "b"):
                    for render in range(4):
                        exact = 1
                        if model == "BASE" and budget == "B64" and pair_index < 20:
                            exact = 0
                        rows.append({
                            "pair_id": pair_id,
                            "MODEL": model,
                            "BUDGET": budget,
                            "MEMBER": member,
                            "COMPONENT": "TONE_MARK",
                            "exact_correct": exact,
                            "codepoint_cer": float(not exact),
                            "output_contract_failure": False,
                            "error_category": "exact_target" if exact else "other_thai_substitution",
                            "FONT": f"f{render % 2}",
                            "FONT_SIZE": str(72 + 24 * (render // 2)),
                        })
    return rows


def test_did_analysis_preserves_pair_cluster_and_named_contrasts() -> None:
    result = did_analysis(_rows())
    assert result["pair_cluster_count"] == 100
    assert result["contrasts"]["DID_196"]["estimate"] == 0
    assert result["contrasts"]["DID_121"]["estimate"] == 0
    assert result["contrasts"]["DID_64"]["estimate"] == 0.2
    assert not result["contrasts"]["DID_64"]["ci_is_holm_adjusted"]


def test_full_validity_uses_full_only_and_overall_gate() -> None:
    engineering = {
        "call_count": 6400,
        "unique_call_count": 6400,
        "unauthorized_or_out_of_workload_locked_pair_count": 0,
        "token_count_distribution": {"64": 1600, "121": 1600, "196": 1600, "256": 1600},
    }
    validity = full_validity(_rows(), engineering)
    assert validity["status"] == "PASS"
    assert validity["primary_analysis_interpretable"]
    assert validity["component_capacity_is_not_implied"]


def test_successful_glmm_diagnostics_pass_uses_normal_path() -> None:
    assert registered_glmm_uses_fallback({
        "fit_status": "FIT_SUCCESS_DIAGNOSTICS_PASS",
        "diagnostics_available": True,
        "diagnostics_pass": True,
    }) is False


def test_successful_glmm_diagnostics_fail_uses_registered_fallback() -> None:
    assert registered_glmm_uses_fallback({
        "fit_status": "FIT_SUCCESS_DIAGNOSTICS_FAIL",
        "diagnostics_available": True,
        "diagnostics_pass": False,
    }) is True


@pytest.mark.parametrize("stage", ["FULL_MODEL_FIT", "NULL_MODEL_FIT"])
def test_eligible_numerical_fit_exception_uses_registered_fallback(stage) -> None:
    assert registered_glmm_uses_fallback({
        "fit_status": "FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE",
        "diagnostics_available": False,
        "fit_exception_class": ["simpleError", "error", "condition"],
        "fit_exception_message": "synthetic numerical fit failure",
        "fit_stage": stage,
        "fallback_eligibility": (
            "NUMERICAL_GLMM_FIT_EXCEPTION_FALLBACK_AMENDMENT_APPROVED"
        ),
    }) is True


def test_fit_exception_cannot_fabricate_failed_diagnostics() -> None:
    with pytest.raises(RuntimeError, match="must not fabricate diagnostics"):
        registered_glmm_uses_fallback({
            "fit_status": "FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE",
            "diagnostics_available": False,
            "diagnostics_pass": False,
            "fit_stage": "FULL_MODEL_FIT",
            "fallback_eligibility": (
                "NUMERICAL_GLMM_FIT_EXCEPTION_FALLBACK_AMENDMENT_APPROVED"
            ),
        })


@pytest.mark.parametrize(
    "payload",
    [
        {"fit_status": "FIT_EXCEPTION_NONELIGIBLE", "diagnostics_available": False},
        {"fit_status": "TECHNICAL_ANALYSIS_FAILURE", "diagnostics_available": False},
        {"fit_status": "FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE", "diagnostics_available": False,
         "fit_stage": "UNKNOWN", "fallback_eligibility": "NUMERICAL_GLMM_FIT_EXCEPTION_FALLBACK_AMENDMENT_APPROVED"},
    ],
)
def test_noneligible_ambiguous_or_invalid_fit_state_fails_closed(payload) -> None:
    with pytest.raises(RuntimeError):
        registered_glmm_uses_fallback(payload)
