"""Kaggle bootstrap for the Thai-mark T1/T2 submission.

Pins the environment, proves the checkout is the registered commit, downloads
the benchmark once, then runs one process per model — the base on GPU 0 and
Typhoon on GPU 1 when two are present, one after the other otherwise. All
scientific logic lives in `labbs2026.thai_marks`.

When `spec["resume_artifact_dir"]` is set (a previous, interrupted attempt's
fetched artifacts, mounted read-only, e.g. as a Kaggle dataset input), each
(test, role) leg is pointed at its own subdirectory there via `--resume-dir` so
`labbs2026.thai_marks.remote` can skip work it already finished.
"""

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


def _atomic_json(path: Path, value) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def _run(command: list[str], cwd: Path, env=None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-3000:]
        raise RuntimeError(f"command failed ({' '.join(command[:4])}): {detail}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gpu_count() -> int:
    result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True)
    return sum(1 for line in result.stdout.splitlines() if line.startswith("GPU "))


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
        # Fetch the registered commit itself, not the branch tip. A submission can
        # sit in Kaggle's queue while the branch moves on; a shallow fetch of the
        # branch then no longer contains the registered SHA and checkout fails.
        _run(["git", "fetch", "--depth", "1", "origin", spec["git_sha"]], source)
        _run(["git", "checkout", "--detach", spec["git_sha"]], source)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source, check=True,
                              capture_output=True, text=True).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("checked-out Git SHA does not match submission")
        for relative, expected in spec["expected_file_hashes"].items():
            if _sha256(source / relative) != expected:
                raise RuntimeError(f"source hash mismatch: {relative}")

        phase = "environment_sync"
        _run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
              "--no-input", f"uv=={spec['uv_bootstrap_version']}"], source)
        _run([sys.executable, "-m", "uv", "sync", *spec["uv_sync_args"],
              "--python", spec["python_version"]], source)
        python = str(source / ".venv/bin/python")

        env = dict(os.environ)
        env["HF_HOME"] = "/tmp/hf"
        env["TOKENIZERS_PARALLELISM"] = "false"

        phase = "benchmark_download"
        _run([python, "-c",
              "from datasets import load_dataset;"
              f"load_dataset({spec['benchmark_repo']!r}, split={spec['benchmark_split']!r},"
              f" revision={spec['benchmark_revision']!r})"], source, env)

        remote_spec = dict(spec)
        remote_spec["artifact_dir"] = str(artifact_dir)
        spec_path = Path("/tmp/labbs2026-thai-marks-spec.json")
        _atomic_json(spec_path, remote_spec)

        resume_root = spec.get("resume_artifact_dir")

        gpus = _gpu_count()
        for test in spec["tests"]:
            phase = f"{test}_inference"
            commands = []
            for position, role in enumerate(("base", "typhoon")):
                role_env = dict(env)
                role_env["CUDA_VISIBLE_DEVICES"] = str(position if gpus >= 2 else 0)
                command = [python, "-m", "labbs2026.thai_marks.remote",
                          "--remote-spec", str(spec_path), "--test", test, "--role", role]
                if resume_root:
                    leg_resume_dir = Path(resume_root) / test / role
                    if leg_resume_dir.is_dir():
                        command += ["--resume-dir", str(leg_resume_dir)]
                commands.append((command, role_env, role))
            if gpus >= 2:
                # Redirect each subprocess's stdout straight to its own log file
                # instead of subprocess.PIPE. A PIPE has a fixed OS buffer (~64KB
                # on Linux); waiting on process.communicate() one process at a
                # time means the other process's pipe is never drained, so once
                # its output (model-loading progress bars, HF warnings) exceeds
                # that buffer it blocks on write() and stalls -- silently
                # serializing what was meant to run in parallel across the two
                # GPUs. Writing to a file has no such buffer limit, so both
                # processes actually run concurrently.
                processes = []
                for cmd, e, role in commands:
                    log_handle = (artifact_dir / f"{test}_{role}.log").open("w", encoding="utf-8")
                    process = subprocess.Popen(cmd, cwd=source, env=e, stdout=log_handle,
                                               stderr=subprocess.STDOUT)
                    processes.append((process, role, log_handle))
                errors = []
                for process, role, log_handle in processes:
                    process.wait()
                    log_handle.close()
                    if process.returncode:
                        output = (artifact_dir / f"{test}_{role}.log").read_text(encoding="utf-8")
                        errors.append(f"{role}: {output[-1500:]}")
                if errors:
                    raise RuntimeError(" | ".join(errors))
            else:
                for cmd, e, role in commands:
                    _run(cmd, source, e)

        phase = "checksums"
        lines = [f"{_sha256(p)}  {p.relative_to(artifact_dir).as_posix()}"
                 for p in sorted(p for p in artifact_dir.rglob("*") if p.is_file())]
        (artifact_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        _atomic_json(artifact_dir / "SUCCESS.json", {
            "run_id": spec["run_id"], "git_sha": spec["git_sha"], "gpus": gpus,
            "checksums_sha256": _sha256(artifact_dir / "checksums.sha256"),
        })
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        _atomic_json(artifact_dir / "FAILURE.json", {
            "run_id": spec.get("run_id"), "phase": phase,
            "exception_type": type(exc).__name__, "message": message[:4000],
        })
        raise


if __name__ == "__main__":
    main()
