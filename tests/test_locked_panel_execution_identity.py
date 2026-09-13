from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import yaml

from labbs2026.stage0.paddle_wayu_locked_panel import (
    FROZEN_DESIGN_FILE_SHA256,
    FROZEN_DESIGN_SHA,
    FROZEN_PIPELINE_FILE_SHA256,
)


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT3 = ROOT / "configs/runtime/kaggle_locked_panel_attempt3_transport.yaml"
ATTEMPT4 = ROOT / "configs/runtime/kaggle_locked_panel_attempt4_transport.yaml"


def _yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text("utf-8"))
    assert isinstance(value, dict)
    return value


def _lifecycle_module():
    path = ROOT / "scripts/paddle_wayu_locked_panel.py"
    spec = importlib.util.spec_from_file_location("locked_panel_lifecycle", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_attempt4_execution_identity_is_exact_and_committed_once() -> None:
    identity = _yaml(ATTEMPT4)
    lifecycle = _lifecycle_module()
    assert lifecycle.TRANSPORT_CONFIG == ATTEMPT4
    assert identity["attempt"] == 4
    assert identity["status"] == "LOCKED_PANEL_RERUN_AUTHORIZED"
    assert identity["run_id"] == "kaggle-paddle-wayu-locked-panel-attempt4"


def test_attempt4_transport_changes_only_execution_identity() -> None:
    attempt3 = _yaml(ATTEMPT3)
    attempt4 = _yaml(ATTEMPT4)
    for key in ("status", "attempt", "run_id"):
        attempt3.pop(key, None)
        attempt4.pop(key, None)
    assert attempt4 == attempt3


def test_frozen_scientific_files_remain_exact() -> None:
    design = ROOT / "configs/stage0/overall_model_budget_design.yaml"
    pipeline = ROOT / "src/labbs2026/stage0/resolution_pipeline.py"
    assert FROZEN_DESIGN_SHA == "871996221a36a56a401fa040c239f55768561210"
    assert hashlib.sha256(design.read_bytes()).hexdigest() == FROZEN_DESIGN_FILE_SHA256
    assert hashlib.sha256(pipeline.read_bytes()).hexdigest() == FROZEN_PIPELINE_FILE_SHA256
