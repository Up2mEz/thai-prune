"""No-data validation for the registered locked-panel analysis image."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


IMAGE = "labbs2026-locked-panel-r:4.5.2-lme4-1.1-38"
ORIGINAL_EXECUTION_COMMIT = "1fa4cdda6ebe37faf215e574a6a5db467beda1cb"
ORIGINAL_REGISTERED_ANALYSIS_ENVIRONMENT = (
    f"{IMAGE}@{ORIGINAL_EXECUTION_COMMIT}"
)
BASE_IMAGE = "rocker/r-ver:4.5.2"
BASE_IMAGE_DIGEST = "sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c"
EXPECTED_R_VERSION = "4.5.2"
EXPECTED_PACKAGE_VERSIONS = {
    "lme4": "1.1.38",
    "detectseparation": "0.3",
    "jsonlite": "2.0.0",
}
EXPECTED_SYSTEM_PACKAGES = ("cmake", "libuv1-dev")
EXPECTED_ENTRYPOINT = ["Rscript", "/opt/locked-panel/run_glmm.R"]
RUN_GLMM_SHA256 = "e30341f261995fb15a7136132a9edc94b7b4752c604e95af7c45c2b966aaec1e"

STATISTICAL_SOURCE_HASHES = {
    "configs/stage0/overall_model_budget_design.yaml": (
        "6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1"
    ),
    "configs/stage0/paddle_wayu_locked_panel_execution.yaml": (
        "13e184c493121f2aff38db68326832c89b6116f643adea38cbca516437e460d2"
    ),
    "infra/analysis/paddle_wayu_locked_panel/run_glmm.R": RUN_GLMM_SHA256,
    "scripts/paddle_wayu_locked_panel.py": (
        "1590b805baefb2f0ea9feba8ad191d88363f737390671977a9727efcadfe2197"
    ),
    "src/labbs2026/stage0/interaction_decision.py": (
        "2b8b024cdd2f446cc4684d460acc06c243d9e3c6369c5df43d69d03b321b0d7f"
    ),
    "src/labbs2026/stage0/locked_panel_analysis.py": (
        "5d0a38197e1e167d9165bdcfcfe88c00e0f9e74d4859975aff06310e931fc70d"
    ),
}

ALLOWED_PACKAGING_PATHS = {
    "docs/DECISION_LOG.md",
    "docs/stage0/PADDLE_WAYU_ANALYSIS_PACKAGING_AMENDMENT.md",
    "infra/analysis/paddle_wayu_locked_panel/Dockerfile",
    "infra/analysis/paddle_wayu_locked_panel/validate_environment.R",
    "scripts/validate_paddle_wayu_analysis_environment.py",
    "src/labbs2026/stage0/locked_panel_environment.py",
    "tests/test_locked_panel_environment.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dockerfile_contract_failures(text: str) -> list[str]:
    """Return packaging-contract failures without running Docker."""

    required_fragments = {
        "base_image_digest": f"FROM {BASE_IMAGE}@{BASE_IMAGE_DIGEST}",
        "cmake_build_dependency": "build-essential cmake gfortran",
        "libuv_build_dependency": "libuv1-dev libxml2-dev",
        "cmake_capability_assertion": "command -v cmake",
        "libuv_capability_assertion": "test -f /usr/include/uv.h",
        "run_glmm_copy": "COPY run_glmm.R /opt/locked-panel/run_glmm.R",
        "validator_copy": "COPY validate_environment.R /opt/locked-panel/validate_environment.R",
        "fail_closed_validator": "RUN Rscript /opt/locked-panel/validate_environment.R",
        "registered_entrypoint": 'ENTRYPOINT ["Rscript", "/opt/locked-panel/run_glmm.R"]',
    }
    failures = [name for name, fragment in required_fragments.items() if fragment not in text]
    if "|| true" in text:
        failures.append("error_swallowing_operator")
    return failures


def payload_failures(payload: dict[str, Any]) -> list[str]:
    """Validate the in-container R report independently of Docker transport."""

    failures = []
    if payload.get("status") != "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATED":
        failures.append("status")
    if payload.get("R_VERSION") != EXPECTED_R_VERSION:
        failures.append("R_VERSION")
    actual_packages = payload.get("package_versions", {})
    loaded = payload.get("libraries_loaded", {})
    for package_name, version in EXPECTED_PACKAGE_VERSIONS.items():
        if actual_packages.get(package_name) != version:
            failures.append(f"package_version:{package_name}")
        if loaded.get(package_name) is not True:
            failures.append(f"library_load:{package_name}")
    if payload.get("RUN_GLMM_PATH") != EXPECTED_ENTRYPOINT[1]:
        failures.append("RUN_GLMM_PATH")
    if payload.get("RUN_GLMM_PRESENT") is not True:
        failures.append("RUN_GLMM_PRESENT")
    if payload.get("RUN_GLMM_PARSEABLE") is not True:
        failures.append("RUN_GLMM_PARSEABLE")
    if payload.get("RUN_GLMM_SHA256") != RUN_GLMM_SHA256:
        failures.append("RUN_GLMM_SHA256")
    return failures


def system_package_failures(packages: dict[str, str]) -> list[str]:
    return [name for name in EXPECTED_SYSTEM_PACKAGES if not packages.get(name)]


def _run(root: Path, command: list[str]) -> str:
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout)[-4000:]
        raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n{detail}")
    return result.stdout


def _source_checks(root: Path) -> dict[str, bool]:
    return {
        relative: (root / relative).is_file() and sha256_file(root / relative) == expected
        for relative, expected in STATISTICAL_SOURCE_HASHES.items()
    }


def _parse_system_report(text: str) -> tuple[dict[str, str], dict[str, str]]:
    os_release: dict[str, str] = {}
    packages: dict[str, str] = {}
    section = "os"
    for line in text.splitlines():
        if line == "--PACKAGES--":
            section = "packages"
            continue
        if section == "os" and "=" in line:
            key, value = line.split("=", 1)
            os_release[key] = value.strip('"')
        elif section == "packages" and "\t" in line:
            name, version = line.split("\t", 1)
            packages[name] = version
    return os_release, packages


def validate_image(root: Path, image: str = IMAGE) -> dict[str, Any]:
    """Validate an analysis image without mounting or reading scientific data."""

    dockerfile = root / "infra/analysis/paddle_wayu_locked_panel/Dockerfile"
    dockerfile_failures = dockerfile_contract_failures(dockerfile.read_text("utf-8"))
    source_checks = _source_checks(root)
    docker_server = _run(root, ["docker", "version", "--format", "{{.Server.Version}}"])
    inspect = json.loads(_run(root, ["docker", "image", "inspect", image]))[0]
    r_output = _run(
        root,
        [
            "docker", "run", "--rm", "--entrypoint", "Rscript", image,
            "/opt/locked-panel/validate_environment.R",
        ],
    )
    payload = json.loads([line for line in r_output.splitlines() if line.strip()][-1])
    report = _run(
        root,
        [
            "docker", "run", "--rm", "--entrypoint", "sh", image, "-lc",
            "cat /etc/os-release; printf '%s\\n' --PACKAGES--; "
            "dpkg-query -W -f='${Package}\\t${Version}\\n' cmake libuv1-dev",
        ],
    )
    os_release, system_packages = _parse_system_report(report)
    payload_errors = payload_failures(payload)
    system_errors = system_package_failures(system_packages)
    entrypoint = inspect.get("Config", {}).get("Entrypoint")

    statistical_paths = list(STATISTICAL_SOURCE_HASHES)
    statistical_diff = _run(
        root,
        ["git", "diff", "--name-only", ORIGINAL_EXECUTION_COMMIT, "HEAD", "--", *statistical_paths],
    ).splitlines()
    changed_paths = set(
        _run(root, ["git", "diff", "--name-only", ORIGINAL_EXECUTION_COMMIT, "HEAD"]).splitlines()
    )
    unexpected_paths = sorted(changed_paths - ALLOWED_PACKAGING_PATHS)
    amendment_commit = _run(root, ["git", "rev-parse", "HEAD"]).strip()
    checks = {
        "docker_daemon_healthy": bool(docker_server.strip()),
        "dockerfile_contract": not dockerfile_failures,
        "R_and_package_contract": not payload_errors,
        "system_dependencies_present": not system_errors,
        "entrypoint_exact": entrypoint == EXPECTED_ENTRYPOINT,
        "statistical_source_hashes_exact": all(source_checks.values()),
        "analysis_statistical_logic_diff_empty": not statistical_diff,
        "analysis_packaging_diff_scoped": not unexpected_paths,
        "no_scientific_data_mount": True,
    }
    return {
        "schema_version": 1,
        "status": (
            "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATED"
            if all(checks.values())
            else "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATION_FAILED"
        ),
        "ORIGINAL_REGISTERED_ANALYSIS_ENVIRONMENT": ORIGINAL_REGISTERED_ANALYSIS_ENVIRONMENT,
        "ANALYSIS_PACKAGING_AMENDMENT_COMMIT": amendment_commit,
        "REPAIRED_ANALYSIS_IMAGE_DIGEST": inspect.get("Id"),
        "BASE_IMAGE": BASE_IMAGE,
        "BASE_IMAGE_DIGEST": BASE_IMAGE_DIGEST,
        "OS_RELEASE": os_release,
        "SYSTEM_PACKAGE_VERSIONS": system_packages,
        "R_VERSION": payload.get("R_VERSION"),
        "LME4_VERSION": payload.get("package_versions", {}).get("lme4"),
        "DETECTSEPARATION_VERSION": payload.get("package_versions", {}).get("detectseparation"),
        "JSONLITE_VERSION": payload.get("package_versions", {}).get("jsonlite"),
        "RUN_GLMM_SHA256": payload.get("RUN_GLMM_SHA256"),
        "SOURCE_RUN_GLMM_SHA256": sha256_file(root / "infra/analysis/paddle_wayu_locked_panel/run_glmm.R"),
        "CONTAINER_RUN_GLMM_SHA256": payload.get("RUN_GLMM_SHA256"),
        "checks": checks,
        "dockerfile_contract_failures": dockerfile_failures,
        "payload_failures": payload_errors,
        "system_package_failures": system_errors,
        "statistical_source_checks": source_checks,
        "ANALYSIS_STATISTICAL_LOGIC_DIFF": statistical_diff,
        "ANALYSIS_PACKAGING_DIFF": sorted(changed_paths),
        "unexpected_diff_paths": unexpected_paths,
        "attempt5_scientific_output_accessed": False,
        "write_analysis_inputs_called": False,
        "frozen_analyze_command_run": False,
    }
