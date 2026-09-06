"""Minimal, Step-3-specific Kaggle execution proof and artifact verifier."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from labbs2026.adapters.qwen25_vl import parse_ab, visual_counts_from_grid
from labbs2026.preflight import inspect_repository
from labbs2026.step3 import load_config, run_audit

WORKER_PLACEHOLDER = "__LABBS_RUN_SPEC_B64__"
EXPECTED_FIXTURE_HASHES = {
    "smoke_latin_a": "1f08ffd67df13b4279442ed4f23713fea9f481a7d0dfcf27cd2586a897ad1d93",
    "smoke_latin_b": "777095ec5b2215748b7d695af02b7e918307b93d7d32d5847f7ad5a7305c3716",
}
EXPECTED_KERNEL_METADATA = {
    "id": "thanakritsamoena/labbs2026-step3-kaggle-proof",
    "title": "LabBS2026 Step 3 Kaggle Proof",
    "code_file": "worker.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "machine_shape": "NvidiaTeslaT4",
    "dataset_sources": [],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}
EXPECTED_TOKEN_METADATA = {
    "image_grid_thw": [1, 32, 32],
    "premerge_patch_count": 1024,
    "llm_visual_token_count": 256,
    "input_image_token_count": 256,
    "runtime_vision_output_count": 256,
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(value) + b"\n")
    temporary.replace(path)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def load_runtime(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("runtime profile must be a mapping")
    if value.get("schema_version") != 1 or value.get("backend") != "kaggle":
        raise ValueError("runtime profile must be a Kaggle schema_version 1 profile")
    if value.get("accelerator") != "NvidiaTeslaT4":
        raise ValueError("Phase 1 requires NvidiaTeslaT4")
    model_runtime = value.get("model_runtime", {})
    if model_runtime.get("device") != "cuda" or model_runtime.get("dtype") != "float16":
        raise ValueError("Phase 1 T4 profile requires cuda/float16")
    return value


def locked_package_versions(path: Path) -> dict[str, str]:
    with path.open("rb") as handle:
        lock = tomllib.load(handle)
    packages = {
        package["name"]: package["version"]
        for package in lock.get("package", [])
        if isinstance(package, dict)
        and isinstance(package.get("name"), str)
        and isinstance(package.get("version"), str)
    }
    required = ("torch", "transformers")
    missing = [name for name in required if name not in packages]
    if missing:
        raise ValueError(f"uv.lock is missing required packages: {missing}")
    return {name: packages[name] for name in required}


def _run(
    command: list[str], *, cwd: Path, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def _check_remote_ref(
    root: Path, url: str, remote_ref: str
) -> tuple[str | None, str | None]:
    result = _run(["git", "ls-remote", url, remote_ref], cwd=root)
    if result.returncode != 0:
        return None, result.stderr.strip() or "git ls-remote failed"
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        return None, f"expected one remote ref match, observed {len(lines)}"
    sha, observed_ref = lines[0].split(maxsplit=1)
    if observed_ref != remote_ref:
        return None, f"remote returned unexpected ref: {observed_ref}"
    return sha, None


def phase1_preflight(
    root: Path, config_path: Path, runtime_path: Path
) -> dict[str, Any]:
    root = root.resolve()
    config_path = config_path.resolve()
    runtime_path = runtime_path.resolve()
    checks: dict[str, dict[str, Any]] = {}

    repository = inspect_repository(root)
    checks["repository"] = {
        "ok": repository.valid,
        "git_commit": repository.git_commit,
        "git_clean": repository.git_clean,
        "missing_paths": list(repository.missing_paths),
    }

    try:
        config = load_config(config_path)
        checks["experiment_config"] = {"ok": True, "sha256": sha256_file(config_path)}
    except (
        AttributeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        yaml.YAMLError,
    ) as exc:
        config = {}
        checks["experiment_config"] = {"ok": False, "error": str(exc)}

    try:
        runtime = load_runtime(runtime_path)
        checks["runtime_profile"] = {"ok": True, "sha256": sha256_file(runtime_path)}
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        runtime = {}
        checks["runtime_profile"] = {"ok": False, "error": str(exc)}

    revision_pattern = re.compile(r"[0-9a-f]{40}")
    model = config.get("model", {})
    revisions_ok = bool(
        revision_pattern.fullmatch(str(model.get("revision", "")))
        and revision_pattern.fullmatch(str(model.get("processor_revision", "")))
    )
    checks["model_revisions"] = {
        "ok": revisions_ok,
        "model_revision": model.get("revision"),
        "processor_revision": model.get("processor_revision"),
    }

    fixture_observed: dict[str, str | None] = {}
    fixture_ok = True
    for sample in config.get("smoke", {}).get("samples", []):
        sample_id = sample.get("sample_id")
        fixture = root / str(sample.get("fixture_path", ""))
        observed = sha256_file(fixture) if fixture.is_file() else None
        fixture_observed[str(sample_id)] = observed
        if observed != EXPECTED_FIXTURE_HASHES.get(str(sample_id)):
            fixture_ok = False
    if set(fixture_observed) != set(EXPECTED_FIXTURE_HASHES):
        fixture_ok = False
    checks["fixtures"] = {"ok": fixture_ok, "observed": fixture_observed}

    uv_lock = root / "uv.lock"
    checks["uv_lock"] = {
        "ok": uv_lock.is_file(),
        "sha256": sha256_file(uv_lock) if uv_lock.is_file() else None,
    }

    metadata_path = root / "infra/kaggle/kernel-metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata_ok = metadata == EXPECTED_KERNEL_METADATA
    except (json.JSONDecodeError, OSError) as exc:
        metadata = {"error": str(exc)}
        metadata_ok = False
    checks["kernel_metadata"] = {"ok": metadata_ok, "observed": metadata}

    tracked = _run(["git", "ls-files"], cwd=root)
    forbidden_names = {"kaggle.json", "access_token"}
    tracked_credentials = [
        line
        for line in tracked.stdout.splitlines()
        if Path(line).name.lower() in forbidden_names
        or Path(line).name.lower().startswith(".env")
    ]
    checks["credentials_not_tracked"] = {
        "ok": tracked.returncode == 0 and not tracked_credentials,
        "tracked_forbidden_paths": tracked_credentials,
    }

    kaggle_version = _run(["kaggle", "--version"], cwd=root)
    checks["kaggle_cli"] = {
        "ok": kaggle_version.returncode == 0,
        "version": kaggle_version.stdout.strip(),
    }
    kaggle_auth = _run(
        ["kaggle", "kernels", "list", "--mine", "--page-size", "1", "-v"],
        cwd=root,
    )
    checks["kaggle_auth_read_only"] = {
        "ok": kaggle_auth.returncode == 0,
        "command": "kaggle kernels list --mine --page-size 1 -v",
    }

    source = runtime.get("source", {})
    remote_sha, remote_error = (
        _check_remote_ref(
            root,
            str(source.get("repository_url", "")),
            str(source.get("remote_ref", "")),
        )
        if source
        else (None, "runtime source configuration unavailable")
    )
    expected_sha = repository.git_commit
    checks["remote_ref"] = {
        "ok": remote_sha is not None and remote_sha == expected_sha,
        "remote_ref": source.get("remote_ref"),
        "local_sha": expected_sha,
        "remote_sha": remote_sha,
        "error": remote_error,
    }

    valid = all(check["ok"] for check in checks.values())
    return {"schema_version": 1, "valid": valid, "checks": checks}


def make_run_spec(
    root: Path, config_path: Path, runtime_path: Path, git_sha: str
) -> dict[str, Any]:
    root = root.resolve()
    config = load_config(config_path)
    runtime = load_runtime(runtime_path)
    run_id = f"kaggle-step3-{git_sha[:12]}"
    fixture_hashes = {
        sample["sample_id"]: sha256_file(root / sample["fixture_path"])
        for sample in config["smoke"]["samples"]
    }
    fixture_paths = {
        sample["sample_id"]: sample["fixture_path"]
        for sample in config["smoke"]["samples"]
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "repository_url": runtime["source"]["repository_url"],
        "remote_ref": runtime["source"]["remote_ref"],
        "git_sha": git_sha,
        "config_path": config_path.resolve().relative_to(root).as_posix(),
        "config_sha256": sha256_file(config_path),
        "runtime_path": runtime_path.resolve().relative_to(root).as_posix(),
        "runtime_sha256": sha256_file(runtime_path),
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "locked_package_versions": locked_package_versions(root / "uv.lock"),
        "fixture_hashes": fixture_hashes,
        "fixture_paths": fixture_paths,
        "model_id": config["model"]["model_id"],
        "model_revision": config["model"]["revision"],
        "processor_revision": config["model"]["processor_revision"],
        "requested_accelerator": runtime["accelerator"],
        "source_dir": runtime["paths"]["source_dir"],
        "output_root": runtime["paths"]["output_root"],
        "python_version": runtime["python"]["version"],
        "uv_bootstrap_version": runtime["uv"]["bootstrap_version"],
        "uv_sync_args": runtime["uv"]["sync_args"],
        "local_reference_raw_outputs": {"smoke_latin_a": "A", "smoke_latin_b": "B"},
        "kernel_id": EXPECTED_KERNEL_METADATA["id"],
        "created_at_utc": utc_now(),
    }


def render_worker(template: str, run_spec: dict[str, Any]) -> str:
    if template.count(WORKER_PLACEHOLDER) != 1:
        raise ValueError(
            "worker template must contain exactly one run-spec placeholder"
        )
    encoded = base64.b64encode(canonical_json_bytes(run_spec)).decode("ascii")
    rendered = template.replace(WORKER_PLACEHOLDER, encoded)
    if WORKER_PLACEHOLDER in rendered:
        raise RuntimeError("worker run-spec placeholder was not replaced")
    return rendered


def build_submit_command(staging_dir: Path) -> list[str]:
    return ["kaggle", "kernels", "push", "-p", str(staging_dir.resolve())]


def prepare_staging(
    root: Path, config_path: Path, runtime_path: Path
) -> dict[str, Any]:
    preflight = phase1_preflight(root, config_path, runtime_path)
    if not preflight["valid"]:
        raise RuntimeError(
            "Phase 1 preflight failed; remote ref must resolve to local HEAD"
        )
    git_sha = preflight["checks"]["repository"]["git_commit"]
    run_spec = make_run_spec(root, config_path, runtime_path, git_sha)
    run_dir = root / "runs" / "kaggle" / run_spec["run_id"]
    staging_dir = run_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=False)
    template_path = root / "infra/kaggle/worker.py"
    run_spec["worker_template_sha256"] = sha256_file(template_path)
    worker = render_worker(template_path.read_text(encoding="utf-8"), run_spec)
    atomic_write_text(staging_dir / "worker.py", worker)
    shutil.copyfile(
        root / "infra/kaggle/kernel-metadata.json",
        staging_dir / "kernel-metadata.json",
    )
    run_spec["generated_worker_sha256"] = sha256_file(staging_dir / "worker.py")
    atomic_write_json(run_dir / "submission.json", run_spec)
    return {
        "run_id": run_spec["run_id"],
        "run_dir": str(run_dir.resolve()),
        "staging_dir": str(staging_dir.resolve()),
        "submit_command": build_submit_command(staging_dir),
        "submission": run_spec,
    }


def is_t4_class_device(name: str) -> bool:
    return bool(re.search(r"(?:^|[^A-Z0-9])T4(?:[^A-Z0-9]|$)", name.upper()))


def cuda_preflight(requested_accelerator: str) -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("torch.cuda.is_available() is false")
    device_index = torch.cuda.current_device()
    properties = torch.cuda.get_device_properties(device_index)
    observed_name = torch.cuda.get_device_name(device_index)
    if requested_accelerator == "NvidiaTeslaT4" and not is_t4_class_device(
        observed_name
    ):
        raise RuntimeError(
            f"requested T4-class accelerator but observed {observed_name!r}"
        )
    left = torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cuda")
    right = torch.tensor([[2.0], [1.0]], device="cuda")
    product = left @ right
    torch.cuda.synchronize()
    if product.cpu().tolist() != [[4.0], [10.0]]:
        raise RuntimeError("CUDA tensor-operation result was incorrect")
    nvidia_smi = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=driver_version,name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "requested_accelerator": requested_accelerator,
        "observed_gpu_name": observed_name,
        "t4_class_verified": is_t4_class_device(observed_name),
        "compute_capability": [int(properties.major), int(properties.minor)],
        "total_device_vram_bytes": int(properties.total_memory),
        "device_count": int(torch.cuda.device_count()),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "cuda_tensor_operation": "PASS",
        "nvidia_smi": {
            "available": nvidia_smi.returncode == 0,
            "query_output": nvidia_smi.stdout.strip()
            if nvidia_smi.returncode == 0
            else None,
        },
    }


def _validate_remote_result(predictions: list[dict[str, Any]]) -> None:
    expected_labels = {"smoke_latin_a": "A", "smoke_latin_b": "B"}
    if {item.get("sample_id") for item in predictions} != set(expected_labels):
        raise RuntimeError("Step 3 result does not contain the two expected controls")
    for prediction in predictions:
        sample_id = prediction["sample_id"]
        if prediction.get("parsed_output") != expected_labels[sample_id]:
            raise RuntimeError(f"parsed control mismatch for {sample_id}")
        parsed, parse_status = parse_ab(str(prediction.get("raw_output", "")))
        if parsed != expected_labels[sample_id] or parse_status != "PARSED":
            raise RuntimeError(f"raw control output is not parseable for {sample_id}")
        metadata = prediction.get("metadata", {})
        for key, expected in EXPECTED_TOKEN_METADATA.items():
            if metadata.get(key) != expected:
                raise RuntimeError(f"token metadata mismatch for {sample_id}: {key}")
        premerge, llm_count = visual_counts_from_grid(
            tuple(metadata["image_grid_thw"]), int(metadata["spatial_merge_size"])
        )
        if premerge != 1024 or llm_count != 256:
            raise RuntimeError(f"recomputed token metadata mismatch for {sample_id}")


def _checksums_text(artifact_dir: Path) -> str:
    names = ("result.json", "manifest.json", "runtime.json")
    return "".join(f"{sha256_file(artifact_dir / name)}  {name}\n" for name in names)


def write_failure(
    artifact_dir: Path, run_id: str, phase: str, exc: BaseException
) -> None:
    message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
    message = re.sub(r"https://[^/@\s]+:[^/@\s]+@", "https://<redacted>@", message)
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "phase": phase,
        "exception_type": type(exc).__name__,
        "message": message[:1000],
        "timestamp_utc": utc_now(),
    }
    atomic_write_json(artifact_dir / "FAILURE.json", payload)


def execute_remote_step3(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    run_id = spec["run_id"]
    source_dir = Path.cwd()
    runtime_path = source_dir / spec["runtime_path"]
    runtime_profile = load_runtime(runtime_path)
    artifact_dir = Path(runtime_profile["paths"]["output_root"]) / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    phase = "cuda_preflight"
    try:
        gpu = cuda_preflight(spec["requested_accelerator"])
        phase = "step3_execution"

        def note_phase(value: str) -> None:
            nonlocal phase
            phase = value

        with tempfile.TemporaryDirectory(prefix="labbs-step3-") as temporary:
            run_dir, source_manifest = run_audit(
                source_dir / spec["config_path"],
                inference=True,
                runtime=runtime_profile,
                output_dir=Path(temporary) / "run",
                expected_git_sha=spec["git_sha"],
                phase_callback=note_phase,
            )
            predictions = json.loads(
                (run_dir / "predictions.json").read_text(encoding="utf-8")
            )

        phase = "step3_validation"
        _validate_remote_result(predictions)
        observed_fixture_hashes = {
            sample["sample_id"]: sample["image_sha256"]
            for sample in source_manifest["samples"]
        }
        if observed_fixture_hashes != spec["fixture_hashes"]:
            raise RuntimeError(
                "runtime fixture hashes do not match submitted fixture hashes"
            )
        architecture = source_manifest["architecture"]
        if architecture["model_id"] != spec["model_id"]:
            raise RuntimeError("model_id does not match submitted model")
        for key in ("model_revision", "processor_revision"):
            if architecture[key] != spec[key]:
                raise RuntimeError(f"{key} does not match submitted revision")

        phase = "artifact_finalization"
        result = {
            "schema_version": 1,
            "run_id": run_id,
            "predictions": predictions,
        }
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "run_status": "VALID_WITH_WARNINGS",
            "scientific_use": "FORBIDDEN_STEP3_SMOKE_ONLY",
            "review_status": "PENDING_HUMAN_REVIEW",
            "git_sha": spec["git_sha"],
            "remote_ref": spec["remote_ref"],
            "config_path": spec["config_path"],
            "config_sha256": spec["config_sha256"],
            "runtime_path": spec["runtime_path"],
            "runtime_sha256": spec["runtime_sha256"],
            "uv_lock_sha256": spec["uv_lock_sha256"],
            "fixture_hashes": observed_fixture_hashes,
            "model_id": architecture["model_id"],
            "model_revision": architecture["model_revision"],
            "processor_revision": architecture["processor_revision"],
            "created_at_utc": source_manifest["created_at_utc"],
        }
        runtime = {
            "schema_version": 1,
            "run_id": run_id,
            "gpu_preflight": gpu,
            "environment": source_manifest["environment"],
            "model_load_seconds": source_manifest["model_load_seconds"],
            "total_seconds": source_manifest["total_seconds"],
            "peak_rss_bytes": source_manifest["peak_rss_bytes"],
            "cuda_memory": source_manifest["cuda_memory"],
        }
        atomic_write_json(artifact_dir / "result.json", result)
        atomic_write_json(artifact_dir / "manifest.json", manifest)
        atomic_write_json(artifact_dir / "runtime.json", runtime)
        checksums = _checksums_text(artifact_dir)
        atomic_write_text(artifact_dir / "checksums.sha256", checksums)
        success = {
            "schema_version": 1,
            "run_id": run_id,
            "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
            "timestamp_utc": utc_now(),
        }
        atomic_write_json(artifact_dir / "SUCCESS.json", success)
    except BaseException as exc:
        success_path = artifact_dir / "SUCCESS.json"
        if success_path.exists():
            success_path.unlink()
        write_failure(artifact_dir, run_id, phase, exc)
        raise


def parse_kaggle_status(output: str) -> str:
    match = re.search(r"(?im)^\s*status\s*:\s*([A-Za-z_ -]+)\s*$", output)
    if not match:
        match = re.search(
            r"(?i)KernelWorkerStatus\.([A-Za-z_]+)",
            output,
        )
    if not match:
        match = re.search(
            r"(?i)kernel\s+has\s+status\s+['\"]?([A-Za-z0-9_. -]+?)['\"]?(?:\.|$)",
            output,
        )
    if not match:
        return "UNKNOWN"
    value = match.group(1).strip().split(".")[-1]
    return value.upper().replace(" ", "_")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path.name}")
    return value


def _version_without_local_suffix(value: Any) -> str:
    return str(value).split("+", maxsplit=1)[0]


def verify_artifacts(
    artifact_dir: Path, submission: dict[str, Any], kaggle_status: str
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    checks: dict[str, dict[str, Any]] = {}

    def record(name: str, ok: bool, observed: Any = None, expected: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "observed": observed, "expected": expected}

    record("kaggle_status", kaggle_status == "COMPLETE", kaggle_status, "COMPLETE")
    success_path = artifact_dir / "SUCCESS.json"
    failure_path = artifact_dir / "FAILURE.json"
    record("success_marker", success_path.is_file(), success_path.is_file(), True)
    record(
        "failure_marker_absent", not failure_path.exists(), failure_path.exists(), False
    )

    required = ["result.json", "manifest.json", "runtime.json", "checksums.sha256"]
    record(
        "required_artifacts", all((artifact_dir / name).is_file() for name in required)
    )
    try:
        result = _load_json(artifact_dir / "result.json")
        manifest = _load_json(artifact_dir / "manifest.json")
        runtime = _load_json(artifact_dir / "runtime.json")
        success = _load_json(success_path)
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        record("json_schema", False, type(exc).__name__, "readable JSON objects")
        return {
            "schema_version": 1,
            "verification_status": "INVALID",
            "hard_checks": checks,
            "informational_comparisons": {},
        }
    record("json_schema", True)

    for name, document in (
        ("result", result),
        ("manifest", manifest),
        ("runtime", runtime),
        ("success", success),
    ):
        record(f"{name}.schema_version", document.get("schema_version") == 1)
        record(
            f"{name}.run_id",
            document.get("run_id") == submission.get("run_id"),
            document.get("run_id"),
            submission.get("run_id"),
        )

    declared: dict[str, str] = {}
    expected_names = {"result.json", "manifest.json", "runtime.json"}
    try:
        checksum_lines = (
            (artifact_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines()
        )
        for line in checksum_lines:
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                declared[parts[1].strip()] = parts[0]
        checksum_ok = set(declared) == expected_names and all(
            sha256_file(artifact_dir / name) == digest
            for name, digest in declared.items()
        )
        observed_checksum_hash = sha256_file(artifact_dir / "checksums.sha256")
    except OSError:
        checksum_ok = False
        observed_checksum_hash = None
    record("artifact_checksums", checksum_ok)
    record(
        "success_checksum_reference",
        observed_checksum_hash is not None
        and success.get("checksums_sha256") == observed_checksum_hash,
        success.get("checksums_sha256"),
        observed_checksum_hash,
    )

    identity_fields = (
        "run_id",
        "git_sha",
        "remote_ref",
        "config_sha256",
        "runtime_sha256",
        "uv_lock_sha256",
        "model_id",
        "model_revision",
        "processor_revision",
    )
    for field in identity_fields:
        observed = success.get(field) if field == "run_id" else manifest.get(field)
        record(
            field, observed == submission.get(field), observed, submission.get(field)
        )
    record(
        "fixture_hashes",
        manifest.get("fixture_hashes")
        == submission.get("fixture_hashes")
        == EXPECTED_FIXTURE_HASHES,
        manifest.get("fixture_hashes"),
        EXPECTED_FIXTURE_HASHES,
    )
    record(
        "scientific_use",
        manifest.get("scientific_use") == "FORBIDDEN_STEP3_SMOKE_ONLY",
        manifest.get("scientific_use"),
        "FORBIDDEN_STEP3_SMOKE_ONLY",
    )
    record(
        "run_status",
        manifest.get("run_status") == "VALID_WITH_WARNINGS",
        manifest.get("run_status"),
        "VALID_WITH_WARNINGS",
    )

    predictions_value = result.get("predictions", [])
    predictions = predictions_value if isinstance(predictions_value, list) else []
    record("predictions_schema", isinstance(predictions_value, list))
    by_id = {
        item.get("sample_id"): item for item in predictions if isinstance(item, dict)
    }
    expected_labels = {"smoke_latin_a": "A", "smoke_latin_b": "B"}
    record(
        "control_set",
        set(by_id) == set(expected_labels),
        sorted(by_id),
        sorted(expected_labels),
    )
    for sample_id, label in expected_labels.items():
        prediction = by_id.get(sample_id, {})
        parsed, parse_status = parse_ab(str(prediction.get("raw_output", "")))
        record(
            f"{sample_id}.parsed_output",
            prediction.get("parsed_output") == label,
            prediction.get("parsed_output"),
            label,
        )
        record(
            f"{sample_id}.parser_recompute",
            parsed == label and parse_status == "PARSED",
            {"parsed": parsed, "status": parse_status},
            {"parsed": label, "status": "PARSED"},
        )
        metadata_value = prediction.get("metadata", {})
        metadata = metadata_value if isinstance(metadata_value, dict) else {}
        record(f"{sample_id}.metadata_schema", isinstance(metadata_value, dict))
        for key, expected in EXPECTED_TOKEN_METADATA.items():
            record(
                f"{sample_id}.{key}",
                metadata.get(key) == expected,
                metadata.get(key),
                expected,
            )
        try:
            premerge, llm_count = visual_counts_from_grid(
                tuple(metadata["image_grid_thw"]), int(metadata["spatial_merge_size"])
            )
            formula_ok = premerge == 1024 and llm_count == 256
        except (KeyError, TypeError, ValueError):
            formula_ok = False
        record(f"{sample_id}.token_formula", formula_ok)

    gpu_value = runtime.get("gpu_preflight", {})
    gpu = gpu_value if isinstance(gpu_value, dict) else {}
    record("gpu_preflight_schema", isinstance(gpu_value, dict))
    record(
        "cuda_tensor_operation",
        gpu.get("cuda_tensor_operation") == "PASS",
        gpu.get("cuda_tensor_operation"),
        "PASS",
    )
    record(
        "requested_accelerator",
        gpu.get("requested_accelerator") == submission.get("requested_accelerator"),
        gpu.get("requested_accelerator"),
        submission.get("requested_accelerator"),
    )
    observed_gpu = str(gpu.get("observed_gpu_name", ""))
    record(
        "t4_class_device", is_t4_class_device(observed_gpu), observed_gpu, "T4-class"
    )
    capability = gpu.get("compute_capability")
    record(
        "compute_capability_recorded",
        isinstance(capability, list)
        and len(capability) == 2
        and all(isinstance(value, int) for value in capability),
    )
    total_vram = gpu.get("total_device_vram_bytes")
    record("total_vram_recorded", isinstance(total_vram, int) and total_vram > 0)
    record("torch_version_recorded", bool(gpu.get("torch")))
    record("cuda_runtime_recorded", bool(gpu.get("cuda_runtime")))
    record("cudnn_field_recorded", "cudnn" in gpu)

    environment = runtime.get("environment", {})
    if not isinstance(environment, dict):
        environment = {}
    expected_python = str(submission.get("python_version", ""))
    observed_python = str(environment.get("python", ""))
    record(
        "python_version",
        observed_python == expected_python
        or observed_python.startswith(f"{expected_python}."),
        observed_python,
        expected_python,
    )
    locked_versions = submission.get("locked_package_versions", {})
    for package in ("torch", "transformers"):
        observed_version = environment.get(package)
        expected_version = locked_versions.get(package)
        record(
            f"locked_{package}_version",
            bool(expected_version)
            and _version_without_local_suffix(observed_version) == expected_version,
            observed_version,
            expected_version,
        )

    cuda_memory_value = runtime.get("cuda_memory", {})
    cuda_memory = cuda_memory_value if isinstance(cuda_memory_value, dict) else {}
    record("cuda_memory_schema", isinstance(cuda_memory_value, dict))
    for key in (
        "allocated_after_model_load_bytes",
        "reserved_after_model_load_bytes",
        "peak_allocated_during_inference_bytes",
        "peak_reserved_during_inference_bytes",
    ):
        value = cuda_memory.get(key)
        record(
            f"cuda_memory.{key}",
            isinstance(value, int) and value >= 0,
            value,
            "non-negative integer",
        )

    raw_observed = {
        sample_id: by_id.get(sample_id, {}).get("raw_output")
        for sample_id in expected_labels
    }
    raw_expected = submission.get("local_reference_raw_outputs", {})
    informational = {
        "raw_output_cpu_gpu_comparison": {
            "status": "MATCH"
            if raw_observed == raw_expected
            else "MISMATCH_REQUIRES_REVIEW",
            "local_reference": raw_expected,
            "kaggle_observed": raw_observed,
            "hard_requirement": False,
        }
    }
    valid = all(item["ok"] for item in checks.values())
    return {
        "schema_version": 1,
        "verification_status": "VERIFIED" if valid else "INVALID",
        "hard_checks": checks,
        "informational_comparisons": informational,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    execute_remote_step3(args.remote_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
