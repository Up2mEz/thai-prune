from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from labbs2026.stage0.paddle_wayu_locked_panel import (
    AUTHORIZATION_FILENAME,
    CORE_OWNERSHIP_FILENAME,
    claim_bootstrap_artifact_ownership,
    initialize_artifact_handoff,
)


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "configs/runtime/kaggle_locked_panel_attempt5_transport.yaml"
IDENTITY_SHA256 = hashlib.sha256(IDENTITY.read_bytes()).hexdigest()


def _worker_module():
    path = ROOT / "infra/kaggle/paddle_wayu_locked_panel_worker.py"
    spec = importlib.util.spec_from_file_location("locked_panel_handoff_worker", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _spec(tmp_path: Path) -> dict:
    return {
        "output_root": str(tmp_path / "artifacts"),
        "run_id": "kaggle-paddle-wayu-locked-panel-attempt5",
        "attempt": 5,
        "authorization_label": "ATTEMPT5_FRESH_FULL_LOCKED_PANEL_AUTHORIZED",
        "git_sha": "e" * 40,
        "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": "871996221a36a56a401fa040c239f55768561210",
        "PROTOCOL_AMENDMENT_COMMIT": "ee9f8c4f85feea935f8c99d05005deea16c30442",
        "ATTEMPT5_EXECUTION_COMMIT": "e" * 40,
        "effective_scientific_protocol": "ORIGINAL_SCIENTIFIC_DESIGN_PLUS_U_FFFD_PER_CALL_PROTOCOL_AMENDMENT",
        "execution_identity_config_path": IDENTITY.relative_to(ROOT).as_posix(),
        "execution_identity_config_sha256": IDENTITY_SHA256,
        "frozen_design_sha256": "f" * 64,
        "locked_content_manifest_sha256": "c" * 64,
        "original_transport_archive_sha256": "a" * 64,
        "locked_content_member_count": 803,
        "locked_content_total_uncompressed_bytes": 3794984,
        "kaggle_dataset_numeric_id": 12006749,
        "kaggle_dataset_version": 1,
        "staged_locked_source_dir": "/kaggle/input/source/locked_source",
    }


def _authorization(spec: dict) -> dict:
    return {
        "schema_version": 1,
        "run_id": spec["run_id"],
        "attempt": spec["attempt"],
        "authorization_label": spec["authorization_label"],
        "status": "AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION",
        "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": spec["ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"],
        "PROTOCOL_AMENDMENT_COMMIT": spec["PROTOCOL_AMENDMENT_COMMIT"],
        "ATTEMPT5_EXECUTION_COMMIT": spec["ATTEMPT5_EXECUTION_COMMIT"],
        "effective_scientific_protocol": spec["effective_scientific_protocol"],
        "kaggle_dataset_numeric_id": spec["kaggle_dataset_numeric_id"],
        "kaggle_dataset_version": spec["kaggle_dataset_version"],
        "frozen_design": {
            "sha256": spec["frozen_design_sha256"],
            "expected_sha256": spec["frozen_design_sha256"],
        },
        "locked_content_manifest": {
            "sha256": spec["locked_content_manifest_sha256"],
            "expected_sha256": spec["locked_content_manifest_sha256"],
        },
        "locked_source_content": {
            "expanded_source_directory": spec["staged_locked_source_dir"],
            "member_count": spec["locked_content_member_count"],
            "total_uncompressed_bytes": spec["locked_content_total_uncompressed_bytes"],
            "content_manifest_sha256": spec["locked_content_manifest_sha256"],
            "original_transport_archive_sha256": spec["original_transport_archive_sha256"],
            "exact_path_set": True,
            "all_sizes_match": True,
            "all_sha256_match": True,
        },
        "scientific_contract_valid": True,
        "authorization_only": False,
    }


def _bootstrap(tmp_path: Path) -> tuple[dict, Path, Path]:
    spec = _spec(tmp_path)
    artifact = Path(spec["output_root"]) / spec["run_id"]
    authorization = _worker_module()._write_bootstrap_authorization(
        artifact, _authorization(spec)
    )
    return spec, artifact, authorization


def test_exact_expected_bootstrap_tree(tmp_path: Path) -> None:
    _, artifact, authorization = _bootstrap(tmp_path)
    assert authorization.is_file()
    assert {path.name for path in artifact.iterdir()} == {"engineering"}
    assert {path.name for path in (artifact / "engineering").iterdir()} == {
        AUTHORIZATION_FILENAME
    }


def test_valid_authorization_can_be_adopted(tmp_path: Path) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    claimed_artifact, engineering, record = claim_bootstrap_artifact_ownership(spec)
    assert claimed_artifact == artifact
    assert record["run_id"] == spec["run_id"]
    assert (engineering / CORE_OWNERSHIP_FILENAME).is_file()


def test_single_successful_claim_precedes_sealed_creation(tmp_path: Path) -> None:
    spec, artifact, authorization = _bootstrap(tmp_path)
    _, engineering, sealed, _ = initialize_artifact_handoff(spec)
    claim = json.loads((engineering / CORE_OWNERSHIP_FILENAME).read_text("utf-8"))
    assert sealed.is_dir()
    assert claim["authorization_artifact_sha256"] == hashlib.sha256(
        authorization.read_bytes()
    ).hexdigest()


def test_missing_authorization_file_fails_closed(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    (Path(spec["output_root"]) / spec["run_id"] / "engineering").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="engineering inventory"):
        initialize_artifact_handoff(spec)


def test_invalid_authorization_json_fails_closed(tmp_path: Path) -> None:
    spec, _, authorization = _bootstrap(tmp_path)
    authorization.write_text('{"truncated":', "utf-8")
    with pytest.raises(RuntimeError, match="invalid bootstrap authorization JSON"):
        initialize_artifact_handoff(spec)


def test_authorization_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    spec, _, authorization = _bootstrap(tmp_path)
    record = json.loads(authorization.read_text("utf-8"))
    record["run_id"] = "wrong-run"
    authorization.write_text(json.dumps(record), "utf-8")
    with pytest.raises(RuntimeError, match="authorization identity mismatch"):
        initialize_artifact_handoff(spec)


def test_attempt3_identity_is_rejected(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    spec["attempt"] = 3
    spec["authorization_label"] = (
        "HUMAN_APPROVED_EXPANDED_LOCKED_SOURCE_TRANSPORT_AND_ATTEMPT_3"
    )
    spec["run_id"] = "kaggle-paddle-wayu-locked-panel-attempt3"
    artifact = Path(spec["output_root"]) / spec["run_id"]
    _worker_module()._write_bootstrap_authorization(
        artifact, _authorization(spec)
    )
    with pytest.raises(RuntimeError, match="authorization identity mismatch"):
        initialize_artifact_handoff(spec)


def test_attempt_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    spec, _, authorization = _bootstrap(tmp_path)
    record = json.loads(authorization.read_text("utf-8"))
    record["attempt"] = 3
    authorization.write_text(json.dumps(record), "utf-8")
    with pytest.raises(RuntimeError, match="authorization identity mismatch"):
        initialize_artifact_handoff(spec)


def test_authorization_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    spec, _, authorization = _bootstrap(tmp_path)
    record = json.loads(authorization.read_text("utf-8"))
    record["frozen_design"]["sha256"] = "0" * 64
    authorization.write_text(json.dumps(record), "utf-8")
    with pytest.raises(RuntimeError, match="authorization identity mismatch"):
        initialize_artifact_handoff(spec)


def test_unexpected_regular_file_fails_closed(tmp_path: Path) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    (artifact / "unexpected.txt").write_text("unexpected", "utf-8")
    with pytest.raises(RuntimeError, match="unexpected file or directory"):
        initialize_artifact_handoff(spec)


def test_unexpected_directory_fails_closed(tmp_path: Path) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    (artifact / "unexpected").mkdir()
    with pytest.raises(RuntimeError, match="unexpected file or directory"):
        initialize_artifact_handoff(spec)


@pytest.mark.parametrize(
    ("relative", "is_directory", "error"),
    [
        ("sealed", True, "pre-existing core artifact"),
        ("SUCCESS.json", False, "pre-existing core artifact"),
        ("engineering/call_ledger.jsonl", False, "pre-existing core artifact"),
        (
            f"engineering/{CORE_OWNERSHIP_FILENAME}",
            False,
            "pre-existing core artifact",
        ),
    ],
)
def test_preexisting_core_artifacts_fail_closed(
    tmp_path: Path, relative: str, is_directory: bool, error: str
) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    path = artifact / relative
    if is_directory:
        path.mkdir(parents=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale", "utf-8")
    with pytest.raises(RuntimeError, match=error):
        initialize_artifact_handoff(spec)


def test_second_initialization_fails_closed(tmp_path: Path) -> None:
    spec, _, _ = _bootstrap(tmp_path)
    initialize_artifact_handoff(spec)
    with pytest.raises(RuntimeError, match="pre-existing core artifact"):
        initialize_artifact_handoff(spec)


def test_symlink_in_artifact_tree_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    target = tmp_path / "target.txt"
    target.write_text("target", "utf-8")
    link = artifact / "engineering" / "link"
    try:
        os.symlink(target, link)
    except OSError:
        original = Path.is_symlink
        authorization = artifact / "engineering" / AUTHORIZATION_FILENAME
        monkeypatch.setattr(
            Path,
            "is_symlink",
            lambda self: self == authorization or original(self),
        )
    with pytest.raises(RuntimeError, match="symlink"):
        initialize_artifact_handoff(spec)


def test_actual_bootstrap_to_core_boundary_stops_before_cuda(tmp_path: Path) -> None:
    spec, artifact, _ = _bootstrap(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), "utf-8")
    result = _worker_module()._launch_core(
        Path(sys.executable), ROOT, spec_path, handoff_test_only=True
    )
    assert result.returncode == 0, result.stderr
    assert (artifact / "engineering" / CORE_OWNERSHIP_FILENAME).is_file()
    assert (artifact / "sealed").is_dir()
    assert not (artifact / "engineering" / "call_ledger.jsonl").exists()
    assert not (artifact / "SUCCESS.json").exists()
    assert not (artifact / "engineering" / "FAILURE.json").exists()
