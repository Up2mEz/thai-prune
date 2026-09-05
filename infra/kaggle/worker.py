"""Kaggle bootstrap template; the local prepare step injects one run specification."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

RUN_SPEC_B64 = "__LABBS_RUN_SPEC_B64__"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sanitized_message(exc: BaseException) -> str:
    message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
    message = re.sub(r"https://[^/@\s]+:[^/@\s]+@", "https://<redacted>@", message)
    return message[:1000]


def _run(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(
        command, cwd=cwd, check=False, capture_output=True, text=True
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise RuntimeError(f"command failed ({command[0]}): {detail}")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if RUN_SPEC_B64.startswith("__LABBS_"):
        raise RuntimeError("worker template was not prepared with a run specification")
    spec = json.loads(base64.b64decode(RUN_SPEC_B64).decode("utf-8"))
    run_id = spec["run_id"]
    output_root = Path(spec["output_root"])
    artifact_dir = output_root / run_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    phase = "source_checkout"
    try:
        source_dir = Path(spec["source_dir"])
        source_dir.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], cwd=source_dir)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], cwd=source_dir)
        _run(
            ["git", "fetch", "--depth", "1", "origin", spec["remote_ref"]],
            cwd=source_dir,
        )
        _run(["git", "checkout", "--detach", spec["git_sha"]], cwd=source_dir)

        phase = "source_verification"
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError(
                f"Git SHA mismatch: expected {spec['git_sha']}, observed {head}"
            )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=source_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status:
            raise RuntimeError("checked-out source tree is not clean")
        expected_files = {
            spec["config_path"]: spec["config_sha256"],
            spec["runtime_path"]: spec["runtime_sha256"],
            "uv.lock": spec["uv_lock_sha256"],
            "infra/kaggle/worker.py": spec["worker_template_sha256"],
        }
        for sample_id, fixture_path in spec["fixture_paths"].items():
            expected_files[fixture_path] = spec["fixture_hashes"][sample_id]
        for relative_path, expected_hash in expected_files.items():
            observed_hash = _sha256(source_dir / relative_path)
            if observed_hash != expected_hash:
                raise RuntimeError(f"source hash mismatch: {relative_path}")

        phase = "uv_bootstrap"
        bootstrap_version = spec["uv_bootstrap_version"]
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                f"uv=={bootstrap_version}",
            ],
            cwd=source_dir,
        )

        phase = "environment_sync"
        sync_args = spec["uv_sync_args"]
        _run(
            [
                sys.executable,
                "-m",
                "uv",
                "sync",
                *sync_args,
                "--python",
                spec["python_version"],
            ],
            cwd=source_dir,
        )

        phase = "source_reverification"
        for relative_path, expected_hash in expected_files.items():
            if _sha256(source_dir / relative_path) != expected_hash:
                raise RuntimeError(
                    f"source hash changed after environment sync: {relative_path}"
                )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=source_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status:
            raise RuntimeError("source tree changed during environment setup")

        phase = "cuda_preflight"
        spec_path = Path("/tmp/labbs2026-run-spec.json")
        _atomic_json(spec_path, spec)
        venv_python = source_dir / ".venv/bin/python"
        _run(
            [
                str(venv_python),
                "-m",
                "labbs2026.kaggle",
                "--remote-spec",
                str(spec_path),
            ],
            cwd=source_dir,
        )
    except BaseException as exc:
        failure_path = artifact_dir / "FAILURE.json"
        if not failure_path.exists():
            _atomic_json(
                failure_path,
                {
                    "schema_version": 1,
                    "run_id": run_id,
                    "phase": phase,
                    "exception_type": type(exc).__name__,
                    "message": _sanitized_message(exc),
                    "timestamp_utc": _now(),
                },
            )
        success_path = artifact_dir / "SUCCESS.json"
        if success_path.exists():
            success_path.unlink()
        raise


if __name__ == "__main__":
    main()
