from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "sha256:7328bb5ac82d574e2d895018981a8cf18b0ae8e73c9b90bf1ce0b350ed7091df"
CONTRACT = ROOT / "infra/analysis/paddle_wayu_locked_panel/glmm_failure_contract.R"
RUN_GLMM = ROOT / "infra/analysis/paddle_wayu_locked_panel/run_glmm.R"


def _run_r(expression: str) -> subprocess.CompletedProcess[str]:
    mount = f"{CONTRACT.resolve()}:/contract.R:ro"
    return subprocess.run(
        [
            "docker", "run", "--rm", "-v", mount,
            "--entrypoint", "Rscript", IMAGE, "-e", expression,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("stage", ["FULL_MODEL_FIT", "NULL_MODEL_FIT"])
def test_synthetic_numerical_fit_exception_is_structured_by_stage(stage) -> None:
    expression = (
        "library(jsonlite); source('/contract.R'); "
        f"result <- run_registered_fit_stage('{stage}', function() {{ "
        "condition <- simpleError('synthetic numerical failure', "
        "call=quote(pwrssUpdate())); stop(condition) }); "
        "cat(toJSON(result, auto_unbox=TRUE, null='null'))"
    )
    result = _run_r(expression)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["fit_status"] == "FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE"
    assert payload["diagnostics_available"] is False
    assert "diagnostics_pass" not in payload
    assert payload["fit_stage"] == stage
    assert payload["fit_exception_call"] == "pwrssUpdate"


def test_synthetic_success_is_not_labeled_as_exception() -> None:
    result = _run_r(
        "library(jsonlite); source('/contract.R'); "
        "result <- run_registered_fit_stage('FULL_MODEL_FIT', function() 42); "
        "cat(toJSON(result, auto_unbox=TRUE))"
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"fit_status": "FIT_SUCCESS", "fit_result": 42}


@pytest.mark.parametrize("call_name", ["read.csv", "model.matrix", "library", "write_json"])
def test_nonfit_and_technical_exceptions_remain_fatal(call_name) -> None:
    expression = (
        "source('/contract.R'); "
        "run_registered_fit_stage('FULL_MODEL_FIT', function() { "
        f"condition <- simpleError('synthetic technical failure', call=quote({call_name}())); "
        "stop(condition) })"
    )
    result = _run_r(expression)
    assert result.returncode != 0
    assert "synthetic technical failure" in result.stderr


def test_malformed_input_package_and_formula_checks_are_outside_fit_exception_router() -> None:
    source = RUN_GLMM.read_text("utf-8")
    router_position = source.index('run_registered_fit_stage(\n  "FULL_MODEL_FIT"')
    assert source.index('stop("analysis columns mismatch")') < router_position
    assert source.index('stop("analysis input contains missing values")') < router_position
    assert source.index('stop("MODEL coding mismatch")') < router_position
    assert source.index('library(lme4)') < router_position
    assert source.index('stop("lme4 version mismatch")') < router_position
    assert source.index("full_formula <- exact_correct ~ MODEL * BUDGET") < router_position
    assert source.index('stop("registered model matrix contains non-finite values")') < router_position


def test_malformed_synthetic_input_is_fatal_and_does_not_emit_fit_state(tmp_path) -> None:
    input_path = tmp_path / "malformed.csv"
    output_path = tmp_path / "glmm_result.json"
    input_path.write_text(
        "call_id\n" + "\n".join(f"synthetic-{index}" for index in range(6400)) + "\n",
        "utf-8",
    )
    mounts = [
        f"{tmp_path.resolve()}:/analysis",
        f"{RUN_GLMM.resolve()}:/opt/locked-panel/run_glmm.R:ro",
        f"{CONTRACT.resolve()}:/opt/locked-panel/glmm_failure_contract.R:ro",
    ]
    command = ["docker", "run", "--rm"]
    for mount in mounts:
        command.extend(["-v", mount])
    command.extend([
        IMAGE,
        "/analysis/malformed.csv",
        "/analysis/glmm_result.json",
    ])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "analysis columns mismatch" in result.stderr
    assert not output_path.exists()


def test_eligibility_is_call_class_based_not_observed_message_based() -> None:
    source = CONTRACT.read_text("utf-8")
    assert "Downdated VtV is not positive definite" not in source
    assert "conditionMessage(error) ==" not in source
    assert '"pwrssUpdate"' in source
