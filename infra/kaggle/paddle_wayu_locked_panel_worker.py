"""Immutable Kaggle bootstrap for the authorized one-shot locked panel."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
import unicodedata
import zlib
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath


RUN_SPEC_B64 = "__LABBS_RUN_SPEC_B64__"
FROZEN_DESIGN_B64 = "__LABBS_FROZEN_DESIGN_B64__"
LOCKED_CONTENT_MANIFEST_ZLIB_B64 = "__LABBS_LOCKED_CONTENT_MANIFEST_ZLIB_B64__"
RUNTIME_IMPORT_PREFLIGHT = (
    ("accelerate", "import accelerate"),
    ("huggingface_hub", "import huggingface_hub"),
    ("numpy", "import numpy"),
    ("PIL", "import PIL"),
    ("torch", "import torch"),
    ("torchvision", "import torchvision"),
    ("transformers", "import transformers"),
    ("yaml", "import yaml"),
    ("qwen_vl_utils", "import qwen_vl_utils"),
    (
        "transformers.AutoModelForImageTextToText/AutoProcessor",
        "from transformers import AutoModelForImageTextToText, AutoProcessor",
    ),
    (
        "labbs2026.stage0.paddle_wayu_locked_panel",
        "import labbs2026.stage0.paddle_wayu_locked_panel",
    ),
    (
        "labbs2026.stage0.paddle_wayu_smoke",
        "import labbs2026.stage0.paddle_wayu_smoke",
    ),
    (
        "labbs2026.stage0.resolution_pipeline",
        "import labbs2026.stage0.resolution_pipeline",
    ),
)


class CoreSubprocessFailure(RuntimeError):
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        detail = (stderr or stdout or "no subprocess output")[-16000:]
        super().__init__(f"core subprocess exited {returncode}: {detail}")


class RuntimeImportFailure(RuntimeError):
    def __init__(self, module: str, returncode: int, stdout: str, stderr: str) -> None:
        self.module = module
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        detail = (stderr or stdout or "no subprocess output")[-16000:]
        super().__init__(f"required runtime import failed for {module}: {detail}")


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


def _redact(value: str) -> str:
    return re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", value)


def _write_bootstrap_authorization(artifact: Path, value: dict) -> Path:
    if artifact.is_symlink() or artifact.exists():
        raise FileExistsError(f"bootstrap artifact path already exists: {artifact}")
    artifact.mkdir(parents=True, exist_ok=False)
    engineering = artifact / "engineering"
    engineering.mkdir(exist_ok=False)
    authorization = engineering / "AUTHORIZATION_VALIDATED.json"
    _json(authorization, value)
    return authorization


def _launch_core(
    python: Path, source: Path, spec_path: Path, *, handoff_test_only: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [
        str(python),
        "-m",
        "labbs2026.stage0.paddle_wayu_locked_panel",
        "--remote-spec",
        str(spec_path),
    ]
    if handoff_test_only:
        command.append("--artifact-handoff-test-only")
    return subprocess.run(command, cwd=source, capture_output=True, text=True)


def _runtime_import_preflight(python: Path, source: Path) -> None:
    for module, statement in RUNTIME_IMPORT_PREFLIGHT:
        result = subprocess.run(
            [str(python), "-c", statement],
            cwd=source,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeImportFailure(
                module, result.returncode, result.stdout, result.stderr
            )


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


def _decode_verified_zlib_payload(
    encoded: str, path: Path, expected_sha256: str
) -> dict:
    compressed = base64.b64decode(encoded, validate=True)
    payload = zlib.decompress(compressed)
    observed = hashlib.sha256(payload).hexdigest()
    if observed != expected_sha256:
        raise RuntimeError(f"compressed payload hash mismatch: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "packaged_path": str(path),
        "compressed_size": len(compressed),
        "file_size": len(payload),
        "sha256": observed,
        "expected_sha256": expected_sha256,
        "encoding": "BASE64_ZLIB_LEVEL_9",
    }


def _normalized_relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    pure = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or pure.is_absolute()
        or any(part in ("", ".", "..") for part in pure.parts)
        or unicodedata.normalize("NFC", relative) != relative
        or pure.as_posix() != relative
    ):
        raise RuntimeError(f"invalid expanded source path: {relative!r}")
    return relative


def _locate_and_verify_locked_source(
    dataset_root: Path, content_manifest: dict, spec: dict
) -> dict:
    candidates = sorted(
        path
        for path in dataset_root.rglob(spec["locked_source_expanded_directory"])
        if path.is_dir()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one expanded locked source directory; observed={len(candidates)}"
        )
    source_root = candidates[0]
    if source_root.is_symlink():
        raise RuntimeError("expanded locked source directory is a symlink")
    expected = {row["path"]: row for row in content_manifest["files"]}
    if len(expected) != content_manifest["member_count"]:
        raise RuntimeError("content manifest contains duplicate paths")
    observed = {}
    casefold_paths = set()
    for path in source_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("symlink in expanded locked source")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError("non-regular expanded locked source entry")
        relative = _normalized_relative(path, source_root)
        folded = relative.casefold()
        if relative in observed or folded in casefold_paths:
            raise RuntimeError("duplicate or case-colliding expanded source path")
        observed[relative] = path
        casefold_paths.add(folded)
    if set(observed) != set(expected):
        raise RuntimeError(
            f"expanded locked source path-set mismatch: "
            f"missing={len(set(expected) - set(observed))}, "
            f"unexpected={len(set(observed) - set(expected))}"
        )
    total_bytes = 0
    for relative, record in expected.items():
        path = observed[relative]
        if path.stat().st_size != record["bytes"]:
            raise RuntimeError(f"expanded locked source size mismatch: {relative}")
        if _sha(path) != record["sha256"]:
            raise RuntimeError(f"expanded locked source hash mismatch: {relative}")
        total_bytes += record["bytes"]
    if total_bytes != content_manifest["total_uncompressed_bytes"]:
        raise RuntimeError("expanded locked source total-byte mismatch")
    return {
        "dataset_root": str(dataset_root),
        "expanded_source_directory": str(source_root),
        "member_count": len(observed),
        "total_uncompressed_bytes": total_bytes,
        "content_manifest_sha256": spec["locked_content_manifest_sha256"],
        "original_transport_archive_sha256": spec["original_transport_archive_sha256"],
        "exact_path_set": True,
        "all_sizes_match": True,
        "all_sha256_match": True,
    }


def _validate_scientific_contract(design: dict, spec: dict) -> None:
    models = [(row["role"], row["model_id"], row["revision"]) for row in design["models"]]
    expected_models = [
        ("BASE", "PaddlePaddle/PaddleOCR-VL-1.6", "c5630abae1d940eafe0697512a0325494b02ab42"),
        ("SPECIALIZED", "wayu-ai/wayu-paxa-ocr-zero", "af0204b4f334a6d5068b6bac2b3738932d6e289b"),
    ]
    analysis = design["primary_analysis"]
    checks = {
        "original_scientific_design_commit": spec["ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"] == "871996221a36a56a401fa040c239f55768561210",
        "protocol_amendment_commit": spec["PROTOCOL_AMENDMENT_COMMIT"] == "ee9f8c4f85feea935f8c99d05005deea16c30442",
        "attempt5_execution_identity": spec["attempt"] == 5
        and spec["run_id"] == "kaggle-paddle-wayu-locked-panel-attempt5"
        and spec["authorization_label"] == "ATTEMPT5_FRESH_FULL_LOCKED_PANEL_AUTHORIZED"
        and spec["ATTEMPT5_EXECUTION_COMMIT"] == spec["git_sha"],
        "effective_protocol_identity": spec["effective_scientific_protocol"]
        == "ORIGINAL_SCIENTIFIC_DESIGN_PLUS_U_FFFD_PER_CALL_PROTOCOL_AMENDMENT",
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
        content_manifest_record = _decode_verified_zlib_payload(
            LOCKED_CONTENT_MANIFEST_ZLIB_B64,
            package_root / "locked_content_manifest.json",
            spec["locked_content_manifest_sha256"],
        )
        content_manifest = json.loads(
            (package_root / "locked_content_manifest.json").read_text("utf-8")
        )
        if content_manifest["original_transport_archive_sha256"] != spec["original_transport_archive_sha256"]:
            raise RuntimeError("original transport archive provenance mismatch")
        dataset_root = Path(
            os.environ["LABBS_AUTH_VALIDATION_DATASET_ROOT"]
            if authorization_only
            else "/kaggle/input"
        )
        bundle_record = _locate_and_verify_locked_source(dataset_root, content_manifest, spec)
        design = yaml.safe_load((package_root / "frozen_design.yaml").read_text("utf-8"))
        if not isinstance(design, dict):
            raise RuntimeError("packaged frozen design did not parse as a YAML mapping")
        _validate_scientific_contract(design, spec)
        authorization_record = {
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
            "frozen_design": design_record,
            "locked_content_manifest": content_manifest_record,
            "locked_source_content": bundle_record,
            "scientific_contract_valid": True,
            "authorization_only": authorization_only,
        }
        _write_bootstrap_authorization(artifact, authorization_record)
        if authorization_only:
            return
        spec["staged_frozen_design_path"] = str(package_root / "frozen_design.yaml")
        spec["staged_locked_content_manifest_path"] = str(
            package_root / "locked_content_manifest.json"
        )
        spec["staged_locked_source_dir"] = bundle_record["expanded_source_directory"]
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
        phase = "runtime_import_preflight"
        _runtime_import_preflight(python, source)
        phase = "authorized_locked_panel"
        spec_path = Path("/tmp/labbs-paddle-wayu-locked-panel-spec.json")
        _json(spec_path, spec)
        result = _launch_core(python, source, spec_path)
        if result.returncode:
            raise CoreSubprocessFailure(result.returncode, result.stdout, result.stderr)
    except BaseException as exc:
        failure = {
            "schema_version": 1,
            "run_id": spec["run_id"],
            "attempt": spec.get("attempt"),
            "authorization_label": spec.get("authorization_label"),
            "scientific_completed_call_count": 0,
            "ORIGINAL_SCIENTIFIC_DESIGN_COMMIT": spec.get("ORIGINAL_SCIENTIFIC_DESIGN_COMMIT"),
            "PROTOCOL_AMENDMENT_COMMIT": spec.get("PROTOCOL_AMENDMENT_COMMIT"),
            "ATTEMPT5_EXECUTION_COMMIT": spec.get("ATTEMPT5_EXECUTION_COMMIT"),
            "classification": "LOCKED_PANEL_TECHNICAL_INVALID_SCIENTIFIC_OUTPUTS_REMAIN_SEALED",
            "phase": phase,
            "exception_type": type(exc).__name__,
            "message": _redact(str(exc))[:4000],
            "traceback": _redact(traceback.format_exc())[-16000:],
            "timestamp_utc": datetime.now(UTC).isoformat(),
        }
        specific_failure = artifact / "engineering/FAILURE.json"
        if isinstance(exc, CoreSubprocessFailure) and specific_failure.is_file():
            try:
                specific = json.loads(specific_failure.read_text("utf-8"))
                if isinstance(specific, dict):
                    failure = specific
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
        if isinstance(exc, CoreSubprocessFailure):
            failure["core_subprocess_returncode"] = exc.returncode
            failure["core_subprocess_stdout"] = _redact(exc.stdout)[-16000:]
            failure["core_subprocess_stderr"] = _redact(exc.stderr)[-16000:]
        if isinstance(exc, RuntimeImportFailure):
            failure["failed_import_module"] = exc.module
            failure["import_subprocess_returncode"] = exc.returncode
            failure["import_subprocess_stdout"] = _redact(exc.stdout)[-16000:]
            failure["import_subprocess_stderr"] = _redact(exc.stderr)[-16000:]
            failure["dependency_context"] = {
                "uv_sync_args": spec.get("uv_sync_args"),
                "transformers_override_lock": spec.get("transformers_override_lock"),
                "transformers_override_lock_sha256": spec.get("source_hashes", {}).get(
                    spec.get("transformers_override_lock", "")
                ),
            }
        bootstrap_failure = output_root / "_bootstrap_failures" / f"{spec['run_id']}.json"
        _json(bootstrap_failure, failure)
        try:
            artifact.mkdir(parents=True, exist_ok=True)
            engineering = artifact / "engineering"
            engineering.mkdir(parents=True, exist_ok=True)
            if not specific_failure.exists():
                _json(engineering / "FAILURE.json", failure)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
