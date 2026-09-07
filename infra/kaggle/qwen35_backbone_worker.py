"""Kaggle bootstrap for one immutable Qwen3.5 Stage 0 backbone audit."""

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
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
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
            ["git", "rev-parse", "HEAD"], cwd=source, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("checked-out Git SHA does not match submission")
        expected = {
            spec[key]: spec[key.replace("_path", "_sha256")]
            for key in (
                "audit_config_path", "config_path", "runtime_path", "model_config_path",
                "prompt_config_path", "bundle_path", "rationale_path",
                "override_lock_path", "worker_template_path",
            )
        }
        expected["uv.lock"] = spec["uv_lock_sha256"]
        for relative, expected_hash in expected.items():
            if _sha256(source / relative) != expected_hash:
                raise RuntimeError(f"source hash mismatch: {relative}")
        if subprocess.run(
            ["git", "status", "--porcelain"], cwd=source, check=True,
            capture_output=True, text=True,
        ).stdout.strip():
            raise RuntimeError("checked-out source tree is not clean")
        phase = "environment_sync"
        _run([
            sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
            "--no-input", f"uv=={spec['uv_bootstrap_version']}",
        ], source)
        _run([
            sys.executable, "-m", "uv", "sync", *spec["uv_sync_args"],
            "--python", spec["python_version"],
        ], source)
        venv_python = source / ".venv/bin/python"
        _run([
            sys.executable, "-m", "uv", "pip", "install",
            "--python", str(venv_python), "--require-hashes", "-r",
            str(source / spec["qwen35_override_lock"]),
        ], source)
        phase = "qwen35_backbone_calibration"
        spec_path = Path("/tmp/labbs2026-qwen35-stage0-spec.json")
        _atomic_json(spec_path, spec)
        _run([
            str(venv_python), "-m", "labbs2026.stage0.backbone_calibration",
            "--remote-spec", str(spec_path),
        ], source)
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        if not (artifact_dir / "FAILURE.json").exists():
            _atomic_json(artifact_dir / "FAILURE.json", {
                "schema_version": 1, "run_id": spec["run_id"], "phase": phase,
                "exception_type": type(exc).__name__, "message": message[:2000],
            })
        raise


if __name__ == "__main__":
    main()
