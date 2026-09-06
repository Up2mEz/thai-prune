from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from labbs2026.kaggle import (
    EXPECTED_FIXTURE_HASHES,
    EXPECTED_KERNEL_METADATA,
    EXPECTED_TOKEN_METADATA,
    atomic_write_json,
    atomic_write_text,
    build_submit_command,
    is_t4_class_device,
    load_runtime,
    make_run_spec,
    parse_kaggle_status,
    phase1_preflight,
    prepare_staging,
    render_worker,
    sha256_file,
    verify_artifacts,
    write_failure,
)
from labbs2026.preflight import PreflightResult

ROOT = Path(__file__).resolve().parents[1]


def _submission() -> dict:
    return {
        "run_id": "kaggle-step3-0123456789ab",
        "git_sha": "0123456789abcdef0123456789abcdef01234567",
        "remote_ref": "refs/heads/infra/kaggle-phase1",
        "config_sha256": "c" * 64,
        "runtime_sha256": "r" * 64,
        "uv_lock_sha256": "u" * 64,
        "model_id": "Qwen/Qwen2.5-VL-3B-Instruct",
        "model_revision": "m" * 40,
        "processor_revision": "p" * 40,
        "fixture_hashes": EXPECTED_FIXTURE_HASHES,
        "requested_accelerator": "NvidiaTeslaT4",
        "python_version": "3.12",
        "locked_package_versions": {"torch": "2.14.0", "transformers": "4.57.6"},
        "local_reference_raw_outputs": {
            "smoke_latin_a": "A",
            "smoke_latin_b": "B",
        },
    }


def _prediction(sample_id: str, label: str, raw: str | None = None) -> dict:
    return {
        "sample_id": sample_id,
        "expected_label": label,
        "raw_output": label if raw is None else raw,
        "parsed_output": label,
        "parse_status": "PARSED",
        "metadata": {
            **EXPECTED_TOKEN_METADATA,
            "spatial_merge_size": 2,
        },
    }


def _valid_artifacts(root: Path, *, raw_a: str = "A") -> tuple[Path, dict]:
    submission = _submission()
    artifact_dir = root / "artifacts" / submission["run_id"]
    artifact_dir.mkdir(parents=True)
    result = {
        "schema_version": 1,
        "run_id": submission["run_id"],
        "predictions": [
            _prediction("smoke_latin_a", "A", raw_a),
            _prediction("smoke_latin_b", "B"),
        ],
    }
    manifest = {
        "schema_version": 1,
        "run_id": submission["run_id"],
        "run_status": "VALID_WITH_WARNINGS",
        "git_sha": submission["git_sha"],
        "remote_ref": submission["remote_ref"],
        "config_sha256": submission["config_sha256"],
        "runtime_sha256": submission["runtime_sha256"],
        "uv_lock_sha256": submission["uv_lock_sha256"],
        "model_revision": submission["model_revision"],
        "processor_revision": submission["processor_revision"],
        "model_id": submission["model_id"],
        "fixture_hashes": EXPECTED_FIXTURE_HASHES,
        "scientific_use": "FORBIDDEN_STEP3_SMOKE_ONLY",
    }
    runtime = {
        "schema_version": 1,
        "run_id": submission["run_id"],
        "gpu_preflight": {
            "requested_accelerator": "NvidiaTeslaT4",
            "observed_gpu_name": "Tesla T4",
            "compute_capability": [7, 5],
            "total_device_vram_bytes": 15_000_000_000,
            "torch": "2.7.1+cu126",
            "cuda_runtime": "12.6",
            "cudnn": 90501,
            "cuda_tensor_operation": "PASS",
        },
        "cuda_memory": {
            "allocated_after_model_load_bytes": 6_000_000_000,
            "reserved_after_model_load_bytes": 6_500_000_000,
            "peak_allocated_during_inference_bytes": 7_000_000_000,
            "peak_reserved_during_inference_bytes": 7_500_000_000,
        },
        "environment": {
            "python": "3.12.13",
            "torch": "2.14.0+cu130",
            "transformers": "4.57.6",
        },
    }
    for name, value in (
        ("result.json", result),
        ("manifest.json", manifest),
        ("runtime.json", runtime),
    ):
        atomic_write_json(artifact_dir / name, value)
    checksums = "".join(
        f"{sha256_file(artifact_dir / name)}  {name}\n"
        for name in ("result.json", "manifest.json", "runtime.json")
    )
    atomic_write_text(artifact_dir / "checksums.sha256", checksums)
    atomic_write_json(
        artifact_dir / "SUCCESS.json",
        {
            "schema_version": 1,
            "run_id": submission["run_id"],
            "checksums_sha256": sha256_file(artifact_dir / "checksums.sha256"),
        },
    )
    return artifact_dir, submission


def test_committed_kernel_metadata_is_exact() -> None:
    observed = json.loads(
        (ROOT / "infra/kaggle/kernel-metadata.json").read_text(encoding="utf-8")
    )
    assert observed == EXPECTED_KERNEL_METADATA


def test_frozen_fixture_hashes_match_audited_images() -> None:
    observed = {
        "smoke_latin_a": sha256_file(ROOT / "assets/step3/smoke_latin_a.png"),
        "smoke_latin_b": sha256_file(ROOT / "assets/step3/smoke_latin_b.png"),
    }
    assert observed == EXPECTED_FIXTURE_HASHES


def test_runtime_profile_is_exact_t4_profile() -> None:
    runtime = load_runtime(ROOT / "configs/runtime/kaggle_t4.yaml")
    assert runtime["accelerator"] == "NvidiaTeslaT4"
    assert runtime["python"]["version"] == "3.12"
    assert runtime["uv"]["bootstrap_version"] == "0.11.25"
    assert runtime["uv"]["sync_args"] == ["--frozen", "--extra", "model"]
    assert runtime["model_runtime"] == {
        "device": "cuda",
        "dtype": "float16",
        "attention_implementation": "sdpa",
        "cache_dir": "/tmp/huggingface",
    }


def test_run_spec_contains_remote_ref_full_sha_and_hashes() -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"
    spec = make_run_spec(
        ROOT,
        ROOT / "configs/step3/qwen25_vl_3b.yaml",
        ROOT / "configs/runtime/kaggle_t4.yaml",
        sha,
    )
    assert spec["run_id"] == "kaggle-step3-0123456789ab"
    assert spec["git_sha"] == sha
    assert spec["remote_ref"] == "refs/heads/main"
    assert spec["source_dir"] == "/tmp/labbs2026-source"
    assert spec["output_root"] == "/kaggle/working/artifacts"
    assert spec["locked_package_versions"] == {
        "torch": "2.14.0",
        "transformers": "4.57.6",
    }
    assert spec["fixture_hashes"] == EXPECTED_FIXTURE_HASHES
    assert spec["model_revision"] == spec["processor_revision"]
    for key in ("config_sha256", "runtime_sha256", "uv_lock_sha256"):
        assert len(spec[key]) == 64


def test_phase1_preflight_accepts_matching_remote_and_read_only_auth() -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"

    def fake_run(command: list[str], *, cwd: Path, check: bool = False):
        if command[:2] == ["git", "ls-files"]:
            return subprocess.CompletedProcess(command, 0, "AGENTS.md\n", "")
        if command == ["kaggle", "--version"]:
            return subprocess.CompletedProcess(command, 0, "Kaggle CLI 2.2.4\n", "")
        if command[:3] == ["kaggle", "kernels", "list"]:
            return subprocess.CompletedProcess(command, 0, "ref,title\n", "")
        raise AssertionError(command)

    with (
        patch(
            "labbs2026.kaggle.inspect_repository",
            return_value=PreflightResult(sha, True, ()),
        ),
        patch("labbs2026.kaggle._check_remote_ref", return_value=(sha, None)),
        patch("labbs2026.kaggle._run", side_effect=fake_run),
    ):
        result = phase1_preflight(
            ROOT,
            ROOT / "configs/step3/qwen25_vl_3b.yaml",
            ROOT / "configs/runtime/kaggle_t4.yaml",
        )

    assert result["valid"]
    assert result["checks"]["kaggle_auth_read_only"]["ok"]
    assert result["checks"]["remote_ref"]["remote_sha"] == sha


def test_prepare_staging_generates_worker_metadata_and_receipt(tmp_path: Path) -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"
    for relative_path in (
        "configs/step3/qwen25_vl_3b.yaml",
        "configs/runtime/kaggle_t4.yaml",
        "infra/kaggle/worker.py",
        "infra/kaggle/kernel-metadata.json",
        "assets/step3/smoke_latin_a.png",
        "assets/step3/smoke_latin_b.png",
        "uv.lock",
    ):
        source = ROOT / relative_path
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    preflight = {
        "schema_version": 1,
        "valid": True,
        "checks": {"repository": {"git_commit": sha}},
    }

    with patch("labbs2026.kaggle.phase1_preflight", return_value=preflight):
        result = prepare_staging(
            tmp_path,
            tmp_path / "configs/step3/qwen25_vl_3b.yaml",
            tmp_path / "configs/runtime/kaggle_t4.yaml",
        )

    staging = Path(result["staging_dir"])
    submission = json.loads(
        (Path(result["run_dir"]) / "submission.json").read_text(encoding="utf-8")
    )
    assert (staging / "worker.py").is_file()
    assert (staging / "kernel-metadata.json").is_file()
    assert "__LABBS_RUN_SPEC_B64__" not in (staging / "worker.py").read_text(
        encoding="utf-8"
    )
    assert submission["git_sha"] == sha
    assert submission["remote_ref"] == "refs/heads/main"
    assert submission["generated_worker_sha256"] == sha256_file(staging / "worker.py")
    assert result["submit_command"] == build_submit_command(staging)


def test_worker_render_replaces_exactly_one_placeholder() -> None:
    template = (ROOT / "infra/kaggle/worker.py").read_text(encoding="utf-8")
    rendered = render_worker(template, {"run_id": "example"})
    compile(rendered, "worker.py", "exec")
    assert "__LABBS_RUN_SPEC_B64__" not in rendered


def test_worker_render_rejects_invalid_template() -> None:
    with pytest.raises(ValueError):
        render_worker("print('no placeholder')", {"run_id": "example"})


def test_submit_command_is_argument_safe(tmp_path: Path) -> None:
    staging = tmp_path / "path with spaces" / "staging"
    assert build_submit_command(staging) == [
        "kaggle",
        "kernels",
        "push",
        "-p",
        str(staging.resolve()),
    ]


@pytest.mark.parametrize("name", ["Tesla T4", "NVIDIA Tesla T4", "NVIDIA T4"])
def test_t4_class_name_normalization(name: str) -> None:
    assert is_t4_class_device(name)


@pytest.mark.parametrize("name", ["Tesla P100", "NVIDIA L4", "T400"])
def test_t4_class_rejects_other_devices(name: str) -> None:
    assert not is_t4_class_device(name)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Status: complete", "COMPLETE"),
        ('Kernel has status "running".', "RUNNING"),
        (
            'example/kernel has status "KernelWorkerStatus.RUNNING"',
            "RUNNING",
        ),
        (
            'example/kernel has status "KernelWorkerStatus.ERROR"',
            "ERROR",
        ),
        ("unrecognized", "UNKNOWN"),
    ],
)
def test_kaggle_status_parsing(raw: str, expected: str) -> None:
    assert parse_kaggle_status(raw) == expected


def test_valid_artifacts_pass_hard_verification(tmp_path: Path) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path)
    before = {path.name: sha256_file(path) for path in artifact_dir.iterdir()}

    result = verify_artifacts(artifact_dir, submission, "COMPLETE")

    after = {path.name: sha256_file(path) for path in artifact_dir.iterdir()}
    assert result["verification_status"] == "VERIFIED"
    assert before == after


def test_raw_text_difference_is_informational_when_parser_passes(
    tmp_path: Path,
) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path, raw_a=" a \n")

    result = verify_artifacts(artifact_dir, submission, "COMPLETE")

    assert result["verification_status"] == "VERIFIED"
    comparison = result["informational_comparisons"]["raw_output_cpu_gpu_comparison"]
    assert comparison["status"] == "MISMATCH_REQUIRES_REVIEW"
    assert comparison["hard_requirement"] is False


def test_corrupted_artifact_fails_verification(tmp_path: Path) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path)
    (artifact_dir / "result.json").write_text("{}\n", encoding="utf-8")

    result = verify_artifacts(artifact_dir, submission, "COMPLETE")

    assert result["verification_status"] == "INVALID"
    assert not result["hard_checks"]["artifact_checksums"]["ok"]


def test_failure_marker_fails_verification(tmp_path: Path) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path)
    write_failure(
        artifact_dir, submission["run_id"], "model_load", RuntimeError("boom")
    )

    result = verify_artifacts(artifact_dir, submission, "COMPLETE")

    assert result["verification_status"] == "INVALID"
    assert not result["hard_checks"]["failure_marker_absent"]["ok"]


def test_missing_success_marker_fails_verification(tmp_path: Path) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path)
    (artifact_dir / "SUCCESS.json").unlink()

    result = verify_artifacts(artifact_dir, submission, "COMPLETE")

    assert result["verification_status"] == "INVALID"


def test_wrong_token_count_fails_even_with_updated_checksums(tmp_path: Path) -> None:
    artifact_dir, submission = _valid_artifacts(tmp_path)
    result_path = artifact_dir / "result.json"
    result_json = json.loads(result_path.read_text(encoding="utf-8"))
    result_json["predictions"][0]["metadata"]["llm_visual_token_count"] = 255
    atomic_write_json(result_path, result_json)
    checksums = "".join(
        f"{sha256_file(artifact_dir / name)}  {name}\n"
        for name in ("result.json", "manifest.json", "runtime.json")
    )
    atomic_write_text(artifact_dir / "checksums.sha256", checksums)
    success = json.loads((artifact_dir / "SUCCESS.json").read_text(encoding="utf-8"))
    success["checksums_sha256"] = sha256_file(artifact_dir / "checksums.sha256")
    atomic_write_json(artifact_dir / "SUCCESS.json", success)

    verification = verify_artifacts(artifact_dir, submission, "COMPLETE")

    assert verification["verification_status"] == "INVALID"
    assert not verification["hard_checks"]["smoke_latin_a.llm_visual_token_count"]["ok"]


def test_failure_message_redacts_common_secret_forms(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    write_failure(
        artifact_dir,
        "run-id",
        "source_checkout",
        RuntimeError("token=secret https://user:password@example.test/repo"),
    )
    failure = json.loads((artifact_dir / "FAILURE.json").read_text(encoding="utf-8"))
    assert "secret" not in failure["message"]
    assert "password" not in failure["message"]
