from __future__ import annotations

import json
from pathlib import Path

import yaml

from labbs2026.stage0.kaggle_backend import (
    KERNEL_METADATA,
    _check_runtime_contract,
    make_stage0_spec,
)


ROOT = Path(__file__).resolve().parents[1]


def test_stage0_kernel_metadata_is_exact() -> None:
    observed = json.loads(
        (ROOT / "infra/kaggle/stage0-kernel-metadata.json").read_text("utf-8")
    )

    assert observed == KERNEL_METADATA


def test_frozen_runtime_matches_calibration_model_config() -> None:
    runtime = yaml.safe_load(
        (ROOT / "configs/runtime/kaggle_t4.yaml").read_text("utf-8")
    )
    model = yaml.safe_load(
        (ROOT / "configs/stage0/qwen25_vl_3b_calibration.yaml").read_text("utf-8")
    )

    assert _check_runtime_contract(runtime, model) == []


def test_stage0_submission_spec_excludes_locked_validation() -> None:
    spec = make_stage0_spec(
        ROOT,
        ROOT / "configs/stage0/calibration_design.yaml",
        ROOT / "configs/runtime/kaggle_t4.yaml",
        ROOT / "configs/stage0/qwen25_vl_3b_calibration.yaml",
        "a" * 40,
    )

    assert spec["run_type"] == "STAGE0_CALIBRATION_ONLY"
    assert spec["exact_observations_per_run"] == 1000
    assert spec["total_model_calls"] == 2000
    assert spec["locked_validation_authorized"] is False
    assert spec["bundle_sha256"] == (
        "d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992"
    )
