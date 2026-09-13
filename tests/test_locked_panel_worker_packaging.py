import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def _worker_module():
    path = ROOT / "infra/kaggle/paddle_wayu_locked_panel_worker.py"
    spec = importlib.util.spec_from_file_location("locked_panel_worker", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_packaged_design_hash_parse_and_contract(tmp_path: Path) -> None:
    worker = _worker_module()
    payload = (ROOT / "configs/stage0/overall_model_budget_design.yaml").read_bytes()
    encoded = __import__("base64").b64encode(payload).decode("ascii")
    expected = hashlib.sha256(payload).hexdigest()
    output = tmp_path / "frozen_design.yaml"
    record = worker._decode_verified_payload(encoded, output, expected)
    assert record["file_size"] == len(payload)
    assert record["sha256"] == expected
    design = yaml.safe_load(output.read_text("utf-8"))
    worker._validate_scientific_contract(
        design,
        {"SCIENTIFIC_DESIGN_COMMIT": "871996221a36a56a401fa040c239f55768561210"},
    )


def test_packaged_design_contract_fails_closed_on_change() -> None:
    worker = _worker_module()
    design = yaml.safe_load(
        (ROOT / "configs/stage0/overall_model_budget_design.yaml").read_text("utf-8")
    )
    design["prompt"] = "changed"
    with pytest.raises(RuntimeError, match="frozen scientific contract mismatch"):
        worker._validate_scientific_contract(
            design,
            {"SCIENTIFIC_DESIGN_COMMIT": "871996221a36a56a401fa040c239f55768561210"},
        )
