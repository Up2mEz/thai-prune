"""Immutable Kaggle bootstrap for the authorized one-shot locked panel."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


RUN_SPEC_B64 = "__LABBS_RUN_SPEC_B64__"
FROZEN_DESIGN_B64 = "__LABBS_FROZEN_DESIGN_B64__"
LOCKED_SOURCE_BUNDLE_B64 = "__LABBS_LOCKED_SOURCE_BUNDLE_B64__"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])


def _json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    os.replace(temporary, path)


def _decode_verified_payload(encoded: str, path: Path, expected_sha256: str) -> dict:
    payload = base64.b64decode(encoded, validate=True)
    observed = hashlib.sha256(payload).hexdigest()
    if observed != expected_sha256:
        raise RuntimeError(f"packaged payload hash mismatch: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "packaged_path": str(path),
        "file_size": len(payload),
        "sha256": observed,
        "expected_sha256": expected_sha256,
    }


def _validate_scientific_contract(design: dict, spec: dict) -> None:
    models = [(row["role"], row["model_id"], row["revision"]) for row in design["models"]]
    expected_models = [
        ("BASE", "PaddlePaddle/PaddleOCR-VL-1.6", "c5630abae1d940eafe0697512a0325494b02ab42"),
        ("SPECIALIZED", "wayu-ai/wayu-paxa-ocr-zero", "af0204b4f334a6d5068b6bac2b3738932d6e289b"),
    ]
    analysis = design["primary_analysis"]
    checks = {
        "scientific_design_commit": spec["SCIENTIFIC_DESIGN_COMMIT"] == "871996221a36a56a401fa040c239f55768561210",
        "models_and_revisions": models == expected_models,
        "prompt": design["prompt"] == "OCR:",
        "parser": design["primary_parser"]["operation"] == "PYTHON_STRIP_LEADING_TRAILING_WHITESPACE_ONLY",
        "budgets": [row["llm_image_placeholders"] for row in design["intervention"]["budgets"]] == [256, 196, 121, 64],
        "bicubic": design["intervention"]["downsampling"]["interpolation"] == "Image.Resampling.BICUBIC",
        "pillow": design["intervention"]["downsampling"]["version"] == "12.3.0",
        "workload": design["execution"]["total_calls"] == 6400,
        "full_formula": analysis["full_formula"] == "exact_correct ~ MODEL * BUDGET + FONT + FONT_SIZE + MEMBER + COMPONENT + (1 | pair_id) + (1 | pair_id:member)",
        "null_formula": analysis["null_formula"] == "exact_correct ~ MODEL + BUDGET + FONT + FONT_SIZE + MEMBER + COMPONENT + (1 | pair_id) + (1 | pair_id:member)",
        "bootstrap": analysis["uncertainty"]["resamples"] == 10000 and analysis["uncertainty"]["seed"] == 20260913,
        "holm": analysis["multiplicity"]["method"] == "HOLM",
        "sesoi": analysis["meaningful_effect"]["sesoi"] == 0.10,
        "locked_pairs": design["dataset"]["pair_count"] == 100,
        "blinding": design["execution"]["intermediate_scientific_outcome_access"] == "FORBIDDEN",
    }
    if not all(checks.values()):
        raise RuntimeError(f"frozen scientific contract mismatch: {checks}")


def main() -> None:
    if RUN_SPEC_B64.startswith("__LABBS_"):
        raise RuntimeError("worker has no run spec")
    spec = json.loads(base64.b64decode(RUN_SPEC_B64).decode("utf-8"))
    authorization_only = os.environ.get("LABBS_AUTHORIZATION_ONLY") == "1"
    output_root = Path(os.environ["LABBS_AUTH_VALIDATION_OUTPUT_ROOT"]) if authorization_only else Path(spec["output_root"])
    artifact = output_root / spec["run_id"]
    phase = "packaged_authorization"
    try:
        import yaml

        package_root = Path("/tmp/labbs-paddle-wayu-locked-package")
        if authorization_only:
            package_root = output_root / ".packaged"
        if package_root.exists():
            raise FileExistsError(f"packaged contract path already exists: {package_root}")
        design_record = _decode_verified_payload(
            FROZEN_DESIGN_B64, package_root / "frozen_design.yaml", spec["frozen_design_sha256"]
        )
        bundle_record = _decode_verified_payload(
            LOCKED_SOURCE_BUNDLE_B64, package_root / "locked_source_bundle.zip",
            spec["locked_source_bundle_sha256"],
        )
        design = yaml.safe_load((package_root / "frozen_design.yaml").read_text("utf-8"))
        if not isinstance(design, dict):
            raise RuntimeError("packaged frozen design did not parse as a YAML mapping")
        _validate_scientific_contract(design, spec)
        authorization_record = {
            "schema_version": 1,
            "status": "AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION",
            "SCIENTIFIC_DESIGN_COMMIT": spec["SCIENTIFIC_DESIGN_COMMIT"],
            "EXECUTION_REPAIR_COMMIT": spec["EXECUTION_REPAIR_COMMIT"],
            "frozen_design": design_record,
            "locked_source_bundle": bundle_record,
            "scientific_contract_valid": True,
            "authorization_only": authorization_only,
        }
        _json(artifact / "engineering/AUTHORIZATION_VALIDATED.json", authorization_record)
        if authorization_only:
            return
        spec["staged_frozen_design_path"] = str(package_root / "frozen_design.yaml")
        spec["staged_locked_bundle_path"] = str(package_root / "locked_source_bundle.zip")
        phase = "source_checkout"
        source = Path(spec["source_dir"])
        source.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], source)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], source)
        _run(["git", "fetch", "--depth", "1", "origin", spec["remote_ref"]], source)
        _run(["git", "checkout", "--detach", spec["git_sha"]], source)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("Git SHA mismatch")
        for relative, expected in spec["source_hashes"].items():
            if _sha(source / relative) != expected:
                raise RuntimeError(f"source hash mismatch: {relative}")
        phase = "environment_sync"
        _run([
            sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
            "--no-input", f"uv=={spec['uv_bootstrap_version']}",
        ], source)
        _run([
            sys.executable, "-m", "uv", "sync", *spec["uv_sync_args"],
            "--python", spec["python_version"],
        ], source)
        python = source / ".venv/bin/python"
        _run([
            sys.executable, "-m", "uv", "pip", "install", "--python", str(python),
            "--require-hashes", "-r", str(source / spec["transformers_override_lock"]),
        ], source)
        phase = "authorized_locked_panel"
        spec_path = Path("/tmp/labbs-paddle-wayu-locked-panel-spec.json")
        _json(spec_path, spec)
        result = subprocess.run(
            [str(python), "-m", "labbs2026.stage0.paddle_wayu_locked_panel",
             "--remote-spec", str(spec_path)],
            cwd=source,
        )
        if result.returncode:
            raise RuntimeError("locked panel execution returned a nonzero status")
    except BaseException as exc:
        artifact.mkdir(parents=True, exist_ok=True)
        engineering = artifact / "engineering"
        engineering.mkdir(parents=True, exist_ok=True)
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        if not (engineering / "FAILURE.json").exists():
            _json(engineering / "FAILURE.json", {
                "schema_version": 1,
                "run_id": spec["run_id"],
                "classification": "LOCKED_PANEL_TECHNICAL_INVALID_SCIENTIFIC_OUTPUTS_REMAIN_SEALED",
                "phase": phase,
                "exception_type": type(exc).__name__,
                "message": message[:4000],
            })
        raise


if __name__ == "__main__":
    main()
