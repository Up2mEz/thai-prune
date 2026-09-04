"""Sequential primary-backbone feasibility audit for Advisor Readiness."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import psutil
import yaml
from PIL import Image, ImageDraw, ImageFont

from labbs2026.adapters.qwen25_vl import Qwen25VLAdapter
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
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def render_smoke_images(config: dict[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    smoke = config["smoke"]
    font_path = Path(smoke["font_path"])
    if not font_path.is_file():
        raise FileNotFoundError(f"smoke font not found: {font_path}")
    font = ImageFont.truetype(str(font_path), size=int(smoke["font_size"]))
    image_dir = run_dir / "images"
    image_dir.mkdir()
    rendered: list[dict[str, Any]] = []
    for sample in smoke["samples"]:
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
        image_path = image_dir / f"{sample['sample_id']}.png"
        image.save(image_path, format="PNG", optimize=False)
        rendered.append(
            {
                **sample,
                "image_path": image_path.relative_to(run_dir).as_posix(),
                "image_sha256": sha256_file(image_path),
                "font_path": font_path.as_posix(),
                "font_sha256": sha256_file(font_path),
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
        state["peak_rss_bytes"] = max(state["peak_rss_bytes"], process.memory_info().rss)


def environment_record() -> dict[str, Any]:
    import torch
    import transformers

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "physical_ram_bytes": psutil.virtual_memory().total,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_available": torch.cuda.is_available(),
        "xpu_available": bool(hasattr(torch, "xpu") and torch.xpu.is_available()),
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


def build_adapter(config: dict[str, Any], root: Path) -> Qwen25VLAdapter:
    model = config["model"]
    generation = config["generation"]
    return Qwen25VLAdapter(
        model_id=model["model_id"],
        revision=model["revision"],
        processor_revision=model["processor_revision"],
        cache_dir=root / model["cache_dir"],
        device=model["device"],
        dtype=model["dtype"],
        attention_implementation=model["attention_implementation"],
        use_fast_processor=bool(model["use_fast_processor"]),
        max_new_tokens=int(generation["max_new_tokens"]),
    )


def run_audit(config_path: Path, *, inference: bool) -> tuple[Path, dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    preflight = inspect_repository(root)
    if not preflight.valid:
        raise RuntimeError(f"repository preflight must pass before a run: {preflight}")
    config = load_config(config_path)
    commit = git_commit(root)
    seed_everything(int(config["seed"]))
    run_dir = create_run_dir(root / config["output"]["root_dir"], commit)
    rendered = render_smoke_images(config, run_dir)
    adapter = build_adapter(config, root)

    started = time.perf_counter()
    predictions: list[dict[str, Any]] = []
    status = "PROCESSOR_AUDIT_ONLY"
    with peak_rss_monitor() as memory:
        architecture = adapter.architecture_record()
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
        "samples": rendered,
    }
    write_json(run_dir / "manifest.json", manifest)
    write_json(run_dir / "predictions.json", predictions)
    return run_dir, manifest
