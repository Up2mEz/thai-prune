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


def test_compressed_content_manifest_preserves_uncompressed_identity(
    tmp_path: Path,
) -> None:
    worker = _worker_module()
    payload = b'{"files":[]}\n'
    compressed = __import__("zlib").compress(payload, level=9)
    encoded = __import__("base64").b64encode(compressed).decode("ascii")
    expected = hashlib.sha256(payload).hexdigest()
    output = tmp_path / "manifest.json"

    record = worker._decode_verified_zlib_payload(encoded, output, expected)

    assert output.read_bytes() == payload
    assert record["sha256"] == expected
    assert record["encoding"] == "BASE64_ZLIB_LEVEL_9"


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
    source = tmp_path / "mounted-dataset" / "locked_source"
    (source / "renders").mkdir(parents=True)
    (source / "a.json").write_bytes(b"{}\n")
    (source / "renders/a.png").write_bytes(b"png")
    files = [
        {"path": "a.json", "bytes": 3, "sha256": hashlib.sha256(b"{}\n").hexdigest()},
        {"path": "renders/a.png", "bytes": 3, "sha256": hashlib.sha256(b"png").hexdigest()},
    ]
    content_manifest = {
        "member_count": 2,
        "total_uncompressed_bytes": 6,
        "files": files,
    }
    spec = {
        "locked_source_expanded_directory": "locked_source",
        "locked_content_manifest_sha256": "f" * 64,
        "original_transport_archive_sha256": "e" * 64,
    }

    record = worker._locate_and_verify_locked_source(tmp_path, content_manifest, spec)

    assert record["member_count"] == 2
    assert record["total_uncompressed_bytes"] == 6
    assert record["exact_path_set"] is True


def test_locked_source_dataset_fails_closed_on_content_change(tmp_path: Path) -> None:
    worker = _worker_module()
    source = tmp_path / "locked_source"
    source.mkdir()
    (source / "a.json").write_bytes(b"changed")
    content_manifest = {
        "member_count": 1,
        "total_uncompressed_bytes": 3,
        "files": [
            {"path": "a.json", "bytes": 3, "sha256": hashlib.sha256(b"old").hexdigest()}
        ],
    }
    spec = {
        "locked_source_expanded_directory": "locked_source",
        "locked_content_manifest_sha256": "f" * 64,
        "original_transport_archive_sha256": "e" * 64,
    }
    with pytest.raises(RuntimeError, match="size mismatch"):
        worker._locate_and_verify_locked_source(tmp_path, content_manifest, spec)
