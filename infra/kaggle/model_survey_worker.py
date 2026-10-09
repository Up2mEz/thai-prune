"""Kaggle bootstrap for the MODEL_SURVEY_M1 submission (Track E).

Pins the environment, proves the checkout is the registered commit, downloads
the benchmark and every model snapshot once, then runs the registered GPU
queues: one thread per GPU, each running its units (one model's shard) one
after another as separate processes. A failed unit is recorded and the other
units still run; the run ends with SUCCESS.json only if every unit finished.
All scientific logic lives in `labbs2026.model_survey`. Bootstrap copied from
`infra/kaggle/input_side_worker.py`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
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
    in a command line, a log or an error message.
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


def _run_queue(gpu: int, queue: list, python: str, spec_path: Path, source: Path, env: dict,
               artifact_dir: Path) -> list[dict]:
    """Run one GPU's units in order; a failed unit does not stop the next one."""
    results = []
    for role, shard, shards in queue:
        name = f"m1_{role}_shard-{shard}-of-{shards}"
        unit_env = dict(env)
        unit_env["CUDA_VISIBLE_DEVICES"] = str(gpu)
        command = [python, "-m", "labbs2026.model_survey.remote", "--remote-spec", str(spec_path),
                   "--role", role, "--shard", str(shard), "--shards", str(shards)]
        with (artifact_dir / f"{name}.log").open("w", encoding="utf-8") as log:
            code = subprocess.run(command, cwd=source, env=unit_env, stdout=log,
                                  stderr=subprocess.STDOUT).returncode
        entry = {"unit": name, "gpu": gpu, "returncode": code}
        if code:
            entry["log_tail"] = (artifact_dir / f"{name}.log").read_text(encoding="utf-8")[-1500:]
        results.append(entry)
    return results


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
        # Fetch the registered commit itself, not the branch tip (the branch can
        # move while the submission waits in Kaggle's queue).
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

        phase = "model_download"
        for role in spec["roles"]:
            model = spec["models"][role]
            _run([python, "-c",
                  "from huggingface_hub import snapshot_download;"
                  f"snapshot_download({model['model_id']!r}, revision={model['revision']!r})"],
                 source, env)

        remote_spec = dict(spec)
        remote_spec["artifact_dir"] = str(artifact_dir)
        spec_path = Path("/tmp/labbs2026-model-survey-spec.json")
        _atomic_json(spec_path, remote_spec)

        phase = "m1_inference"
        gpus = _gpu_count()
        queues = [q for q in spec["gpu_queues"] if q]
        if gpus >= 2:
            if len(queues) > gpus:
                raise RuntimeError(f"{len(queues)} queues for {gpus} GPUs")
            with ThreadPoolExecutor(len(queues)) as pool:
                futures = [pool.submit(_run_queue, gpu, q, python, spec_path, source, env, artifact_dir)
                           for gpu, q in enumerate(queues)]
                units = [u for f in futures for u in f.result()]
        else:
            units = [u for q in queues
                     for u in _run_queue(0, q, python, spec_path, source, env, artifact_dir)]

        phase = "checksums"
        lines = [f"{_sha256(p)}  {p.relative_to(artifact_dir).as_posix()}"
                 for p in sorted(p for p in artifact_dir.rglob("*") if p.is_file())]
        (artifact_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        status = {"run_id": spec["run_id"], "git_sha": spec["git_sha"], "gpus": gpus,
                  "github_token_used": github_token_used, "units": units,
                  "checksums_sha256": _sha256(artifact_dir / "checksums.sha256")}
        failed = [u["unit"] for u in units if u["returncode"]]
        if failed:
            _atomic_json(artifact_dir / "PARTIAL.json", status)
            raise RuntimeError(f"units failed: {failed}")
        _atomic_json(artifact_dir / "SUCCESS.json", status)
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
