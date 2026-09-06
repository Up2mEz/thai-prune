"""Kaggle bootstrap for one immutable Stage 0 calibration submission."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUN_SPEC_B64 = "__LABBS_RUN_SPEC_B64__"


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-3000:]
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
        raise RuntimeError("worker was not prepared with a run specification")
    spec = json.loads(base64.b64decode(RUN_SPEC_B64).decode("utf-8"))
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=False)
    phase = "source_checkout"
    try:
        source = Path(spec["source_dir"])
        source.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], source)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], source)
        _run(["git", "fetch", "--depth", "1", "origin", spec["remote_ref"]], source)
        _run(["git", "checkout", "--detach", spec["git_sha"]], source)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
        ).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("checked-out Git SHA does not match submission")
        expected = {
            spec["config_path"]: spec["config_sha256"],
            spec["runtime_path"]: spec["runtime_sha256"],
            spec["model_config_path"]: spec["model_config_sha256"],
            spec["prompt_config_path"]: spec["prompt_config_sha256"],
            spec["human_review_path"]: spec["human_review_sha256"],
            spec["bundle_path"]: spec["bundle_sha256"],
            "uv.lock": spec["uv_lock_sha256"],
            spec["worker_template_path"]: spec["worker_template_sha256"],
        }
        for relative, expected_hash in expected.items():
            if _sha256(source / relative) != expected_hash:
                raise RuntimeError(f"source hash mismatch: {relative}")
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=source, check=True, capture_output=True, text=True
        ).stdout.strip()
        if status:
            raise RuntimeError("checked-out source tree is not clean")
        phase = "environment_sync"
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                f"uv=={spec['uv_bootstrap_version']}",
            ],
            source,
        )
        _run(
            [
                sys.executable,
                "-m",
                "uv",
                "sync",
                *spec["uv_sync_args"],
                "--python",
                spec["python_version"],
            ],
            source,
        )
        for relative, expected_hash in expected.items():
            if _sha256(source / relative) != expected_hash:
                raise RuntimeError(f"source changed after environment sync: {relative}")
        phase = "stage0_calibration"
        spec_path = Path("/tmp/labbs2026-stage0-spec.json")
        _atomic_json(spec_path, spec)
        _run(
            [
                str(source / ".venv/bin/python"),
                "-m",
                "labbs2026.stage0.kaggle_backend",
                "--remote-spec",
                str(spec_path),
            ],
            source,
        )
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        if not (artifact_dir / "FAILURE.json").exists():
            _atomic_json(
                artifact_dir / "FAILURE.json",
                {
                    "schema_version": 1,
                    "run_id": spec["run_id"],
                    "phase": phase,
                    "exception_type": type(exc).__name__,
                    "message": message[:2000],
                },
            )
        raise


if __name__ == "__main__":
    main()
