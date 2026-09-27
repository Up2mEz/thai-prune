import json
from pathlib import Path

import numpy as np

from labbs2026.stage0.measurement_readiness import (
    _logit_shifted,
    headroom_class,
)


def test_headroom_classification_uses_sesoi_multiples():
    assert headroom_class(0.20) == "ADEQUATE_HEADROOM"
    assert headroom_class(0.10) == "MARGINAL_HEADROOM"
    assert headroom_class(0.0999) == "FLOOR_LIMITED"


def test_logit_shift_hits_requested_marginal_drop():
    values = np.array([0.05, 0.25, 0.50, 0.80])
    shifted = _logit_shifted(values, 0.10)
    assert np.isclose(shifted.mean(), values.mean() - 0.10)
    assert np.all(shifted <= values)


def test_preserved_s0_artifact_has_no_locked_access():
    root = Path(__file__).resolve().parents[1]
    candidates = list((root / "runs/kaggle").glob("kaggle-paddle-wayu-s0-*/fetched/artifacts/*/locked_set_audit.json"))
    if not candidates:
        return
    audit = json.loads(candidates[-1].read_text("utf-8"))
    assert audit["locked_pair_count"] == 0
    assert audit["valid"]
