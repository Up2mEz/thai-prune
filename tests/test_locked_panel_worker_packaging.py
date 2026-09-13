import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

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


def test_locked_source_dataset_is_located_and_verified(tmp_path: Path) -> None:
    worker = _worker_module()
    dataset = tmp_path / "mounted-dataset"
    dataset.mkdir()
    member = b"png"
    archive_manifest = {
        "registered_locked_pair_count": 100,
        "source_png_count": 800,
        "file_sha256": {"renders/a.png": hashlib.sha256(member).hexdigest()},
    }
    archive_manifest_bytes = json.dumps(archive_manifest).encode("utf-8")
    archive = dataset / "locked_source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("bundle_manifest.json", archive_manifest_bytes)
        bundle.writestr("renders/a.png", member)
    spec = {
        "locked_source_archive_filename": "locked_source.zip",
        "locked_source_dataset_manifest_filename": "locked_source_manifest.json",
        "locked_source_bundle_bytes": archive.stat().st_size,
        "locked_source_bundle_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "locked_source_archive_manifest_sha256": hashlib.sha256(archive_manifest_bytes).hexdigest(),
    }
    manifest = {
        "schema_version": 1,
        "scientific_scope": "AUTHORIZED_LOCKED_PANEL_SOURCE_448_RGB",
        "archive_filename": "locked_source.zip",
        "archive_bytes": spec["locked_source_bundle_bytes"],
        "archive_sha256": spec["locked_source_bundle_sha256"],
        "archive_manifest_sha256": spec["locked_source_archive_manifest_sha256"],
    }
    manifest_path = dataset / "locked_source_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    spec["locked_source_dataset_manifest_sha256"] = hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()

    record = worker._locate_and_verify_locked_source(tmp_path, spec)

    assert record["registered_locked_pair_count"] == 100
    assert record["source_png_count"] == 800


def test_locked_source_dataset_fails_closed_on_archive_change(tmp_path: Path) -> None:
    worker = _worker_module()
    (tmp_path / "locked_source.zip").write_bytes(b"changed")
    manifest = tmp_path / "locked_source_manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    spec = {
        "locked_source_archive_filename": "locked_source.zip",
        "locked_source_dataset_manifest_filename": "locked_source_manifest.json",
        "locked_source_bundle_bytes": 7,
        "locked_source_bundle_sha256": "0" * 64,
        "locked_source_archive_manifest_sha256": "1" * 64,
        "locked_source_dataset_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    with pytest.raises(RuntimeError, match="manifest content mismatch"):
        worker._locate_and_verify_locked_source(tmp_path, spec)
