"""Immutable Kaggle bootstrap for the approved Qwen3.5 contract pilot."""

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


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-3000:])


def _json(path: Path, value: dict) -> None:
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    os.replace(temporary, path)


def main() -> None:
    if RUN_SPEC_B64.startswith("__LABBS_"):
        raise RuntimeError("worker has no run spec")
    spec = json.loads(base64.b64decode(RUN_SPEC_B64).decode("utf-8"))
    artifact = Path(spec["output_root"]) / spec["run_id"]
    artifact.mkdir(parents=True, exist_ok=False)
    phase = "source_checkout"
    try:
        source = Path(spec["source_dir"])
        source.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], source)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], source)
        _run(["git", "fetch", "--depth", "1", "origin", spec["remote_ref"]], source)
        _run(["git", "checkout", "--detach", spec["git_sha"]], source)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("Git SHA mismatch")
        for relative, expected in spec["source_hashes"].items():
            if _sha(source / relative) != expected:
                raise RuntimeError(f"source hash mismatch: {relative}")
        phase = "environment_sync"
        _run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", f"uv=={spec['uv_bootstrap_version']}"], source)
        _run([sys.executable, "-m", "uv", "sync", *spec["uv_sync_args"], "--python", spec["python_version"]], source)
        python = source / ".venv/bin/python"
        _run([sys.executable, "-m", "uv", "pip", "install", "--python", str(python), "--require-hashes", "-r", str(source / spec["qwen35_override_lock"])], source)
        phase = "frozen_contract_pilot"
        spec_path = Path("/tmp/labbs-contract-pilot-spec.json")
        _json(spec_path, spec)
        _run([str(python), "-m", "labbs2026.stage0.measurement_contract_pilot_run", "--remote-spec", str(spec_path)], source)
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        if not (artifact / "FAILURE.json").exists():
            _json(artifact / "FAILURE.json", {"schema_version": 1, "run_id": spec["run_id"], "phase": phase, "exception_type": type(exc).__name__, "message": message[:2000]})
        raise


if __name__ == "__main__":
    main()
