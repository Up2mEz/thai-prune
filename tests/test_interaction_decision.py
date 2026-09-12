import pytest

from labbs2026.stage0.interaction_decision import classify_interaction


def _p(**updates: float) -> dict[str, float]:
    values = {"DID_196": 0.20, "DID_121": 0.20, "DID_64": 0.20}
    values.update(updates)
    return values


def _d(**updates: float) -> dict[str, float]:
    values = {"DID_196": 0.0, "DID_121": 0.0, "DID_64": 0.0}
    values.update(updates)
    return values


def test_meaningful_interaction_requires_omnibus_holm_and_sesoi() -> None:
    assert classify_interaction(0.01, _d(DID_121=-0.10), _p(DID_121=0.05)) == (
        "MEANINGFUL_MODEL_BUDGET_INTERACTION_SUPPORTED"
    )


def test_significant_omnibus_below_sesoi_is_labeled_below_sesoi() -> None:
    assert classify_interaction(0.05, _d(DID_64=0.0999), _p(DID_64=0.01)) == (
        "INTERACTION_DETECTED_BELOW_PLANNED_SESOI"
    )


def test_meaningful_observed_did_without_holm_survival_is_suggestive() -> None:
    assert classify_interaction(0.01, _d(DID_196=0.11), _p(DID_196=0.051)) == (
        "SUGGESTIVE_MEANINGFUL_INTERACTION_NOT_CONFIRMED"
    )


def test_nonsignificant_omnibus_overrides_large_did_without_claiming_equivalence() -> None:
    assert classify_interaction(0.051, _d(DID_64=0.30), _p(DID_64=0.001)) == (
        "NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE"
    )


def test_classifier_rejects_missing_contrast() -> None:
    with pytest.raises(ValueError):
        classify_interaction(0.01, {"DID_196": 0.1}, _p())
