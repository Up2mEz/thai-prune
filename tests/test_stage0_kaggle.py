from __future__ import annotations

import json
from pathlib import Path

import yaml

from labbs2026.stage0.kaggle_backend import (
    KERNEL_METADATA,
    _check_runtime_contract,
    make_stage0_spec,
)
from labbs2026.stage0.repair_v2 import (
    KERNEL_METADATA as REPAIR_KERNEL_METADATA,
    canonical_smoke_selection_sha256,
    make_repair_spec,
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


def test_repair_v2_kernel_metadata_is_exact() -> None:
    observed = json.loads(
        (ROOT / "infra/kaggle/stage0-repair-v2-kernel-metadata.json").read_text(
            "utf-8"
        )
    )

    assert observed == REPAIR_KERNEL_METADATA


def test_repair_v2_smoke_selection_hash_is_frozen() -> None:
    repair = yaml.safe_load(
        (ROOT / "configs/stage0/calibration_repair_v2.yaml").read_text("utf-8")
    )
    smoke = repair["engineering_smoke"]

    assert canonical_smoke_selection_sha256(smoke) == smoke["selection_sha256"]
    assert smoke["scientific_evidence"] is False
    assert smoke["total_model_calls"] == 40


def test_repair_v2_spec_keeps_locked_validation_sealed() -> None:
    spec = make_repair_spec(
        ROOT,
        ROOT / "configs/stage0/calibration_repair_v2.yaml",
        ROOT / "configs/runtime/kaggle_t4.yaml",
        "a" * 40,
    )

    assert spec["run_type"] == "STAGE0_CALIBRATION_REPAIR_V2"
    assert spec["smoke"]["total_model_calls"] == 40
    assert spec["repaired_calibration"]["total_model_calls"] == 2000
    assert spec["locked_validation_authorized"] is False
    assert spec["gate_0_status"] == "NOT_RUN"
    assert spec["stage_1a_status"] == "BLOCKED"


def test_repair_v2_runtime_contract_is_exact() -> None:
    runtime = yaml.safe_load(
        (ROOT / "configs/runtime/kaggle_t4.yaml").read_text("utf-8")
    )
    model = yaml.safe_load(
        (
            ROOT / "configs/stage0/qwen25_vl_3b_calibration_repair_v2.yaml"
        ).read_text("utf-8")
    )

    assert _check_runtime_contract(runtime, model) == []
