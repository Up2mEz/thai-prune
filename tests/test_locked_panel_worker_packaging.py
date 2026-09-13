import hashlib
import importlib.util
import json
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
        {
            "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": "871996221a36a56a401fa040c239f55768561210",
            "PROTOCOL_AMENDMENT_COMMIT": "ee9f8c4f85feea935f8c99d05005deea16c30442",
            "attempt": 5,
            "run_id": "kaggle-paddle-wayu-locked-panel-attempt5",
            "authorization_label": "ATTEMPT5_FRESH_FULL_LOCKED_PANEL_AUTHORIZED",
            "ATTEMPT5_EXECUTION_COMMIT": "e" * 40,
            "git_sha": "e" * 40,
            "effective_scientific_protocol": "ORIGINAL_SCIENTIFIC_DESIGN_PLUS_U_FFFD_PER_CALL_PROTOCOL_AMENDMENT",
        },
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
            {
                "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": "871996221a36a56a401fa040c239f55768561210",
                "PROTOCOL_AMENDMENT_COMMIT": "ee9f8c4f85feea935f8c99d05005deea16c30442",
                "attempt": 5,
                "run_id": "kaggle-paddle-wayu-locked-panel-attempt5",
                "authorization_label": "ATTEMPT5_FRESH_FULL_LOCKED_PANEL_AUTHORIZED",
                "ATTEMPT5_EXECUTION_COMMIT": "e" * 40,
                "git_sha": "e" * 40,
                "effective_scientific_protocol": "ORIGINAL_SCIENTIFIC_DESIGN_PLUS_U_FFFD_PER_CALL_PROTOCOL_AMENDMENT",
            },
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


def test_runtime_import_preflight_covers_real_execution_imports() -> None:
    worker = _worker_module()
    required = {
        "accelerate",
        "huggingface_hub",
        "numpy",
        "PIL",
        "torch",
        "torchvision",
        "transformers",
        "yaml",
        "qwen_vl_utils",
        "AutoModelForImageTextToText",
        "AutoProcessor",
        "labbs2026.stage0.paddle_wayu_locked_panel",
        "labbs2026.stage0.paddle_wayu_smoke",
        "labbs2026.stage0.resolution_pipeline",
    }
    configured = "\n".join(
        f"{module}: {statement}"
        for module, statement in worker.RUNTIME_IMPORT_PREFLIGHT
    )
    assert all(name in configured for name in required)
    assert "wrapt" not in configured


def test_bootstrap_failure_channel_does_not_require_run_artifact_root(
    tmp_path: Path,
) -> None:
    worker = _worker_module()
    output_root = tmp_path / "artifacts"
    run_id = "blocked-artifact"
    artifact = output_root / run_id
    artifact.parent.mkdir(parents=True)
    artifact.write_text("not a directory", "utf-8")
    failure = {
        "schema_version": 1,
        "run_id": run_id,
        "exception_type": "FileExistsError",
    }

    external = output_root / "_bootstrap_failures" / f"{run_id}.json"
    worker._json(external, failure)

    assert json.loads(external.read_text("utf-8")) == failure
    assert artifact.is_file()
