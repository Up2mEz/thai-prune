from pathlib import Path

from labbs2026.stage0.locked_panel_environment import (
    RUN_GLMM_SHA256,
    dockerfile_contract_failures,
    payload_failures,
    system_package_failures,
)


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "infra/analysis/paddle_wayu_locked_panel/Dockerfile"


def _valid_payload() -> dict:
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


def test_exact_repaired_packaging_contract_passes() -> None:
    assert dockerfile_contract_failures(DOCKERFILE.read_text("utf-8")) == []
    assert payload_failures(_valid_payload()) == []
    assert system_package_failures({"cmake": "3.28.3", "libuv1-dev": "1.48.0"}) == []


def test_missing_cmake_or_libuv_fails_validation() -> None:
    assert system_package_failures({"libuv1-dev": "1.48.0"}) == ["cmake"]
    assert system_package_failures({"cmake": "3.28.3"}) == ["libuv1-dev"]


def test_dockerfile_requires_system_capabilities_and_fail_closed_assertion() -> None:
    text = DOCKERFILE.read_text("utf-8")
    assert "cmake_build_dependency" in dockerfile_contract_failures(text.replace("cmake gfortran", "gfortran"))
    assert "libuv_build_dependency" in dockerfile_contract_failures(text.replace("libuv1-dev ", ""))
    assert "fail_closed_validator" in dockerfile_contract_failures(
        text.replace("RUN Rscript /opt/locked-panel/validate_environment.R", "")
    )


def test_error_swallowing_is_rejected() -> None:
    text = DOCKERFILE.read_text("utf-8") + "\nRUN false || true\n"
    assert "error_swallowing_operator" in dockerfile_contract_failures(text)


def test_missing_entrypoint_and_wrong_hash_fail_validation() -> None:
    missing = _valid_payload()
    missing["RUN_GLMM_PRESENT"] = False
    assert "RUN_GLMM_PRESENT" in payload_failures(missing)
    wrong_hash = _valid_payload()
    wrong_hash["RUN_GLMM_SHA256"] = "0" * 64
    assert "RUN_GLMM_SHA256" in payload_failures(wrong_hash)


def test_wrong_r_or_package_version_and_failed_library_load_fail_validation() -> None:
    wrong_r = _valid_payload()
    wrong_r["R_VERSION"] = "4.5.3"
    assert "R_VERSION" in payload_failures(wrong_r)
    wrong_package = _valid_payload()
    wrong_package["package_versions"]["lme4"] = "1.1-37"
    assert "package_version:lme4" in payload_failures(wrong_package)
    failed_load = _valid_payload()
    failed_load["libraries_loaded"]["detectseparation"] = False
    assert "library_load:detectseparation" in payload_failures(failed_load)
