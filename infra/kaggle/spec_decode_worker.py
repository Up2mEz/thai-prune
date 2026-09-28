"""Kaggle bootstrap for the SPEC_DECODE_S1 submission (Track A).

Pins the environment, proves the checkout is the registered commit, downloads
the benchmark once, then runs one process per model — the base on GPU 0 and
Typhoon on GPU 1 when two are present, one after the other otherwise. All
scientific logic lives in `labbs2026.spec_decode`. Copied from
`infra/kaggle/thai_marks_worker.py`; only the entry module and phase names differ.
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


def _github_env() -> tuple[dict, bool]:
    """Environment for `git fetch` from the private repository.

    The read token comes from the Kaggle Secret `GITHUB_READ_TOKEN` and reaches
    git only through `GIT_CONFIG_*` environment variables, so it never appears
    in a command line, a log or an error message. Without the secret the fetch
    is anonymous, which works only while the repository is public.
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        from kaggle_secrets import UserSecretsClient

        token = UserSecretsClient().get_secret("GITHUB_READ_TOKEN")
    except Exception:
        token = None
    if not token:
        return env, False
    basic = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    return env, True


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
    github_token_used = False
    try:
        source = Path(spec["source_dir"])
        source.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], source)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], source)
        # Fetch the registered commit itself, not the branch tip. A submission can
        # sit in Kaggle's queue while the branch moves on; a shallow fetch of the
        # branch then no longer contains the registered SHA and checkout fails.
        git_env, github_token_used = _github_env()
        _run(["git", "fetch", "--depth", "1", "origin", spec["git_sha"]], source, git_env)
        del git_env
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
        spec_path = Path("/tmp/labbs2026-spec-decode-spec.json")
        _atomic_json(spec_path, remote_spec)

        gpus = _gpu_count()
        for test in spec["tests"]:
            phase = f"{test}_inference"
            commands = []
            for position, role in enumerate(("base", "typhoon")):
                role_env = dict(env)
                role_env["CUDA_VISIBLE_DEVICES"] = str(position if gpus >= 2 else 0)
                commands.append(([python, "-m", "labbs2026.spec_decode.remote",
                                  "--remote-spec", str(spec_path),
                                  "--role", role], role_env, role))
            if gpus >= 2:
                # Each process writes straight to its own log file, not a PIPE: draining
                # pipes one process at a time lets the other's ~64KB buffer fill, block
                # its write() and silently serialize the two GPUs (fixed the same way
                # in infra/kaggle/thai_marks_worker.py, PR #16).
                processes = []
                for cmd, e, role in commands:
                    log_handle = (artifact_dir / f"{test}_{role}.log").open("w", encoding="utf-8")
                    processes.append((subprocess.Popen(cmd, cwd=source, env=e, stdout=log_handle,
                                                       stderr=subprocess.STDOUT), role, log_handle))
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
            "github_token_used": github_token_used,
            "checksums_sha256": _sha256(artifact_dir / "checksums.sha256"),
        })
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        _atomic_json(artifact_dir / "FAILURE.json", {
            "run_id": spec.get("run_id"), "phase": phase,
            "github_token_used": github_token_used,
            "exception_type": type(exc).__name__, "message": message[:4000],
        })
        raise


if __name__ == "__main__":
    main()
