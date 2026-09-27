"""Sequential primary-backbone feasibility audit for Advisor Readiness."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import yaml
from PIL import Image, ImageDraw, ImageFont

from labbs2026.adapters.factory import build_adapter
from labbs2026.preflight import inspect_repository


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage") != "step3_backbone_feasibility":
        raise ValueError("config is not a Step 3 feasibility configuration")
    return config


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def render_smoke_images(
    config: dict[str, Any], run_dir: Path, root: Path
) -> list[dict[str, Any]]:
    smoke = config["smoke"]
    image_dir = run_dir / "images"
    image_dir.mkdir()
    rendered: list[dict[str, Any]] = []
    for sample in smoke["samples"]:
        image_path = image_dir / f"{sample['sample_id']}.png"
        fixture = sample.get("fixture_path")
        if fixture:
            fixture_path = (root / fixture).resolve()
            if not fixture_path.is_relative_to(root.resolve()):
                raise ValueError(f"smoke fixture escapes repository root: {fixture}")
            if not fixture_path.is_file():
                raise FileNotFoundError(f"smoke fixture not found: {fixture_path}")
            shutil.copyfile(fixture_path, image_path)
            with Image.open(image_path) as image:
                image.verify()
            fixture_metadata = {
                "fixture_path": Path(fixture).as_posix(),
                "fixture_sha256": sha256_file(fixture_path),
            }
        else:
            font_path = Path(smoke["font_path"])
            if not font_path.is_file():
                raise FileNotFoundError(f"smoke font not found: {font_path}")
            font = ImageFont.truetype(str(font_path), size=int(smoke["font_size"]))
            image = Image.new(
                "RGB",
                (int(smoke["canvas_width"]), int(smoke["canvas_height"])),
                "white",
            )
            draw = ImageDraw.Draw(image)
            bbox = draw.textbbox((0, 0), sample["display_text"], font=font)
            x = (image.width - (bbox[2] - bbox[0])) / 2 - bbox[0]
            y = (image.height - (bbox[3] - bbox[1])) / 2 - bbox[1]
            draw.text((x, y), sample["display_text"], fill="black", font=font)
            image.save(image_path, format="PNG", optimize=False)
            fixture_metadata = {
                "font_path": font_path.as_posix(),
                "font_sha256": sha256_file(font_path),
            }
        rendered.append(
            {
                **sample,
                "image_path": image_path.relative_to(run_dir).as_posix(),
                "image_sha256": sha256_file(image_path),
                **fixture_metadata,
                "review_status": "PENDING_HUMAN_REVIEW",
                "scientific_use": "FORBIDDEN_STEP3_SMOKE_ONLY",
            }
        )
    return rendered


@contextmanager
def peak_rss_monitor(interval_seconds: float = 0.05) -> Iterator[dict[str, int]]:
    process = psutil.Process(os.getpid())
    state = {"peak_rss_bytes": process.memory_info().rss}
    stop = threading.Event()

    def sample() -> None:
        while not stop.wait(interval_seconds):
            state["peak_rss_bytes"] = max(
                state["peak_rss_bytes"], process.memory_info().rss
            )

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        stop.set()
        thread.join()
        state["peak_rss_bytes"] = max(
            state["peak_rss_bytes"], process.memory_info().rss
        )


def environment_record() -> dict[str, Any]:
    import torch
    import transformers

    cuda_available = torch.cuda.is_available()
    gpu: dict[str, Any] | None = None
    if cuda_available:
        index = torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(index)
        driver = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=driver_version,name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        gpu = {
            "device_index": int(index),
            "model": torch.cuda.get_device_name(index),
            "compute_capability": [int(properties.major), int(properties.minor)],
            "total_memory_bytes": int(properties.total_memory),
            "nvidia_smi_query": driver.stdout.strip() if driver.returncode == 0 else None,
        }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "physical_ram_bytes": psutil.virtual_memory().total,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": cuda_available,
        "torch_cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
        "xpu_available": bool(hasattr(torch, "xpu") and torch.xpu.is_available()),
        "gpu": gpu,
    }


def create_run_dir(root: Path, commit: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / f"{timestamp}_{commit[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_audit(
    config_path: Path,
    *,
    inference: bool,
    runtime: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    expected_git_sha: str | None = None,
    phase_callback: Callable[[str], None] | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    preflight = inspect_repository(root)
    if not preflight.valid:
        raise RuntimeError(f"repository preflight must pass before a run: {preflight}")
    config = load_config(config_path)
    commit = git_commit(root)
    if expected_git_sha is not None and commit != expected_git_sha:
        raise RuntimeError(
            f"Git SHA mismatch: expected {expected_git_sha}, observed {commit}"
        )
    seed_everything(int(config["seed"]))
    if output_dir is None:
        run_dir = create_run_dir(root / config["output"]["root_dir"], commit)
    else:
        run_dir = output_dir.resolve()
        run_dir.mkdir(parents=True, exist_ok=False)
    rendered = render_smoke_images(config, run_dir, root)
    adapter = build_adapter(config, root, runtime)

    started = time.perf_counter()
    predictions: list[dict[str, Any]] = []
    status = "PROCESSOR_AUDIT_ONLY"
    cuda_memory: dict[str, int | None] = {
        "allocated_after_model_load_bytes": None,
        "reserved_after_model_load_bytes": None,
        "peak_allocated_during_inference_bytes": None,
        "peak_reserved_during_inference_bytes": None,
    }
    with peak_rss_monitor() as memory:
        if inference and phase_callback:
            phase_callback("model_load")
        architecture = adapter.architecture_record()
        if inference:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            _ = adapter.model
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                cuda_memory["allocated_after_model_load_bytes"] = int(
                    torch.cuda.memory_allocated()
                )
                cuda_memory["reserved_after_model_load_bytes"] = int(
                    torch.cuda.memory_reserved()
                )
                torch.cuda.reset_peak_memory_stats()
            if phase_callback:
                phase_callback("step3_execution")
        for sample in rendered:
            image_path = run_dir / sample["image_path"]
            if inference:
                result = adapter.predict(image_path, config["smoke"]["prompt"])
                predictions.append(
                    {
                        "sample_id": sample["sample_id"],
                        "expected_label": sample["expected_label"],
                        **asdict(result),
                    }
                )
            else:
                metadata = adapter.get_visual_stage_metadata(
                    image_path, config["smoke"]["prompt"]
                )
                predictions.append(
                    {
                        "sample_id": sample["sample_id"],
                        "expected_label": sample["expected_label"],
                        "raw_output": None,
                        "parsed_output": None,
                        "parse_status": "NOT_RUN",
                        "metadata": asdict(metadata),
                    }
                )
        if inference:
            status = "VALID_WITH_PENDING_HUMAN_REVIEW"
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                cuda_memory["peak_allocated_during_inference_bytes"] = int(
                    torch.cuda.max_memory_allocated()
                )
                cuda_memory["peak_reserved_during_inference_bytes"] = int(
                    torch.cuda.max_memory_reserved()
                )

    manifest = {
        "schema_version": 1,
        "run_status": status,
        "stage": config["stage"],
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": sha256_file(config_path),
        "seed": int(config["seed"]),
        "inference_requested": inference,
        "environment": environment_record(),
        "architecture": architecture,
        "model_load_seconds": adapter.model_load_seconds,
        "total_seconds": time.perf_counter() - started,
        "peak_rss_bytes": memory["peak_rss_bytes"],
        "cuda_memory": cuda_memory,
        "samples": rendered,
    }
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "predictions.json", predictions)
    return run_dir, manifest
