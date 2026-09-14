from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from labbs2026.stage0.locked_panel_environment import RUN_GLMM_SHA256


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/paddle_wayu_locked_panel.py"


def _lifecycle_module():
    spec = importlib.util.spec_from_file_location("locked_panel_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _payload() -> dict:
    return {
        "status": "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATED",
        "R_VERSION": "4.5.2",
        "package_versions": {
            "lme4": "1.1.38",
            "detectseparation": "0.3",
            "jsonlite": "2.0.0",
        },
        "libraries_loaded": {
            "lme4": True,
            "detectseparation": True,
            "jsonlite": True,
        },
        "RUN_GLMM_PATH": "/opt/locked-panel/run_glmm.R",
        "RUN_GLMM_PRESENT": True,
        "RUN_GLMM_PARSEABLE": True,
        "RUN_GLMM_SHA256": RUN_GLMM_SHA256,
    }


def _completed(returncode: int = 0, *, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _accepted_inspect(module, *, image_id: str | None = None) -> str:
    return json.dumps([
        {
            "Id": image_id or module.ACCEPTED_ANALYSIS_IMAGE,
            "RepoDigests": [
                "labbs2026-locked-panel-r@"
                + module.ACCEPTED_ANALYSIS_IMAGE
            ],
            "Config": {"Entrypoint": ["Rscript", "/opt/locked-panel/run_glmm.R"]},
        }
    ])


def _mock_valid_image(module) -> Mock:
    return Mock(side_effect=[
        _completed(stdout=_accepted_inspect(module)),
        _completed(stdout=json.dumps(_payload()) + "\n"),
    ])


def test_exact_accepted_image_resolves_and_contract_matches(monkeypatch) -> None:
    module = _lifecycle_module()
    run = _mock_valid_image(module)
    monkeypatch.setattr(module.subprocess, "run", run)

    result = module.verify_accepted_analysis_image()

    assert result["status"] == "ACCEPTED_ANALYSIS_IMAGE_VERIFIED"
    assert result["accepted_identity"] == result["resolved_image_id"]
    assert result["environment"]["RUN_GLMM_SHA256"] == RUN_GLMM_SHA256
    assert result["environment"]["package_versions"] == _payload()["package_versions"]
    assert result["image_acquisition"] == "NONE"
    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0] == ["docker", "image", "inspect", module.ACCEPTED_ANALYSIS_IMAGE]
    assert commands[1][0:5] == ["docker", "run", "--rm", "--entrypoint", "Rscript"]


def test_dry_run_reaches_pre_data_boundary_without_reading_outputs(monkeypatch, tmp_path) -> None:
    module = _lifecycle_module()
    validation = {
        "status": "ACCEPTED_ANALYSIS_IMAGE_VERIFIED",
        "accepted_identity": module.ACCEPTED_ANALYSIS_IMAGE,
    }
    monkeypatch.setattr(module, "verify_accepted_analysis_image", lambda: validation)
    write_inputs = Mock(side_effect=AssertionError("scientific data access occurred"))
    monkeypatch.setattr(module, "write_analysis_inputs", write_inputs)

    result = module.analyze(
        tmp_path,
        {"run_id": "kaggle-paddle-wayu-locked-panel-attempt5"},
        dry_run_before_data_access=True,
    )

    assert result["status"] == "PINNED_ANALYSIS_RUNNER_VALIDATED"
    assert result["scientific_data_accessed"] is False
    assert result["write_analysis_inputs_called"] is False
    assert result["registered_r_command"][0:4] == ["docker", "run", "--rm", "-v"]
    assert result["registered_r_command"][9] == module.ACCEPTED_ANALYSIS_IMAGE
    assert result["registered_r_command"][6].endswith(":/opt/locked-panel/run_glmm.R:ro")
    assert result["registered_r_command"][8].endswith(
        ":/opt/locked-panel/glmm_failure_contract.R:ro"
    )
    write_inputs.assert_not_called()


def test_missing_image_fails_without_acquisition(monkeypatch) -> None:
    module = _lifecycle_module()
    run = Mock(return_value=_completed(returncode=1, stderr="No such image"))
    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="unavailable"):
        module.verify_accepted_analysis_image()
    assert run.call_count == 1


@pytest.mark.parametrize("reference", ["wrong-image:latest", "mutable-local-tag"])
def test_wrong_image_or_mutable_tag_fails_identity(monkeypatch, reference) -> None:
    module = _lifecycle_module()
    monkeypatch.setattr(module, "ACCEPTED_ANALYSIS_IMAGE", reference)
    run = Mock(return_value=_completed(stdout=_accepted_inspect(module, image_id="sha256:" + "0" * 64)))
    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="identity mismatch"):
        module.verify_accepted_analysis_image()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda payload: payload.update(RUN_GLMM_SHA256="0" * 64), "RUN_GLMM_SHA256"),
        (lambda payload: payload.update(R_VERSION="4.5.3"), "R_VERSION"),
        (
            lambda payload: payload["package_versions"].update(lme4="1.1.37"),
            "package_version:lme4",
        ),
        (
            lambda payload: (
                payload["package_versions"].pop("detectseparation"),
                payload["libraries_loaded"].update(detectseparation=False),
            ),
            "package_version:detectseparation",
        ),
    ],
)
def test_environment_contract_mismatch_fails(monkeypatch, mutation, expected) -> None:
    module = _lifecycle_module()
    payload = _payload()
    mutation(payload)
    run = Mock(side_effect=[
        _completed(stdout=_accepted_inspect(module)),
        _completed(stdout=json.dumps(payload) + "\n"),
    ])
    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(RuntimeError, match=expected):
        module.verify_accepted_analysis_image()


def test_launcher_has_no_build_pull_or_install_execution_path() -> None:
    module = _lifecycle_module()
    source = inspect.getsource(module.verify_accepted_analysis_image) + inspect.getsource(module.analyze)
    assert '["docker", "build"' not in source
    assert '["docker", "pull"' not in source
    assert "apt-get" not in source
    assert "install.packages" not in source
    assert "remotes::install_version" not in source
