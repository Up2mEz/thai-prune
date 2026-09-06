from __future__ import annotations

from pathlib import Path

from labbs2026.stage0.bundle import verify_bundle_roundtrip
from labbs2026.step3 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BUNDLE_SHA256 = "d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992"


def test_frozen_calibration_bundle_contains_no_locked_pairs() -> None:
    bundle = ROOT / "assets/stage0/calibration_input.zip"

    manifest = verify_bundle_roundtrip(bundle, EXPECTED_BUNDLE_SHA256)

    assert sha256_file(bundle) == EXPECTED_BUNDLE_SHA256
    assert manifest["calibration_pair_count"] == 100
    assert manifest["locked_validation_pair_count_in_bundle"] == 0
    assert manifest["render_condition_count"] == 4
    assert manifest["rendered_stimulus_count"] == 800
