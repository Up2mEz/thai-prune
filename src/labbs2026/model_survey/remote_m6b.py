"""Remote entry point for one MODEL_SURVEY M6b (DeepSeek-OCR-2) process on Kaggle.

DeepSeek-OCR-2 runs only with remote code written for transformers 4.46.3
(clearance §4), while the repository pins transformers 5.12. The unit therefore
runs in two stages:

1. **bootstrap** (the repository's environment, as started by the worker):
   create a fresh venv, install `configs/model_survey/m6b_requirements.txt`, and
   re-run this module there with `--stage run`.
2. **run** (the venv): M1's item loop with M1's protocol. DeepSeek's `infer()`
   is not used, because it:
   - reads the image from a file;
   - casts to bf16;
   - bans repeated 20-grams;
   - decodes up to 8192 tokens.

   Instead, `prepare_inputs` rebuilds infer()'s inputs (crop mode, base 1024,
   crops of 768, the `plain` conversation template, the card's settings) from the
   in-memory image. The model then generates with M1's greedy settings in fp16,
   with eager attention (T4 has no flash-attention 2 and no bf16).

Records have M1's format, under `m1/<role>/`, so `model_survey.analysis` reads
them unchanged. No image is written anywhere.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

REQUIREMENTS = "configs/model_survey/m6b_requirements.txt"
BASE_SIZE, CROP_SIZE, PATCH, DOWNSAMPLE = 1024, 768, 16, 4   # the card's infer() call
IMAGE_TOKEN_ID = 128815                                       # as infer()
STOP = "<｜end▁of▁sentence｜>"


def bootstrap(args: argparse.Namespace, spec: dict) -> None:
    source = Path(spec["source_dir"])
    venv = Path(f"/tmp/m6b-venv-{args.role}-{args.shard}")
    # Kaggle's Python has no ensurepip, so `python -m venv` fails; the worker has
    # already installed uv, which builds the venv and installs into it.
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv not found; the worker installs it before any unit runs")
    subprocess.run([uv, "venv", "--python", f"{sys.version_info.major}.{sys.version_info.minor}",
                    str(venv)], check=True)
    python = venv / "bin" / "python"
    subprocess.run([uv, "pip", "install", "--python", str(python), "-r", str(source / REQUIREMENTS)],
                   check=True)
    env = dict(os.environ, PYTHONPATH=str(source / "src"))
    subprocess.run([str(python), "-m", "labbs2026.model_survey.remote_m6b", "--stage", "run",
                    "--remote-spec", str(args.remote_spec), "--role", args.role,
                    "--shard", str(args.shard), "--shards", str(args.shards)],
                   cwd=source, env=env, check=True)


def content_for(kind: str, question: str, prompts: dict) -> str:
    """The user turn: DeepSeek's `<image>` placeholder, then the prompt text."""
    from labbs2026.model_survey.plan import resolve_prompt

    return "<image>\n" + resolve_prompt(kind, question, prompts)


def prepare_inputs(remote, tokenizer, image, content: str, dtype, torch, device: str = "cuda") -> dict:
    """infer()'s inputs for one image in crop mode, built without a file and in `dtype`.

    `remote` is the model's own module (`modeling_deepseekocr2`), whose helpers
    are used as infer() uses them.
    """
    conversation = [{"role": "<|User|>", "content": content, "images": ["<in memory>"]},
                    {"role": "<|Assistant|>", "content": ""}]
    prompt = remote.format_messages(conversations=conversation, sft_format="plain", system_prompt="")
    transform = remote.BasicImageTransform(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5), normalize=True)
    before, after = prompt.split("<image>")

    tokens = remote.text_encode(tokenizer, before, bos=False, eos=False)
    seq_mask = [False] * len(tokens)
    if image.size[0] <= CROP_SIZE and image.size[1] <= CROP_SIZE:
        crops, crop_ratio = [], [1, 1]
    else:
        crops, crop_ratio = remote.dynamic_preprocess(image)
    global_view = remote.ImageOps.pad(image, (BASE_SIZE, BASE_SIZE),
                                      color=tuple(int(x * 255) for x in transform.mean))
    width_crops, height_crops = crop_ratio
    queries = math.ceil((CROP_SIZE // PATCH) / DOWNSAMPLE)
    queries_base = math.ceil((BASE_SIZE // PATCH) / DOWNSAMPLE)
    image_tokens = [IMAGE_TOKEN_ID] * (queries_base * queries_base) + [IMAGE_TOKEN_ID]
    if width_crops > 1 or height_crops > 1:
        image_tokens += [IMAGE_TOKEN_ID] * ((queries * width_crops) * (queries * height_crops))
    else:
        crops = []
    tokens += image_tokens
    seq_mask += [True] * len(image_tokens)
    tail = remote.text_encode(tokenizer, after, bos=False, eos=False)
    tokens = [0] + tokens + tail                                  # BOS id 0, as infer()
    seq_mask = [False] + seq_mask + [False] * len(tail)

    images_ori = torch.stack([transform(global_view)], dim=0).to(dtype)
    images_crop = (torch.stack([transform(c) for c in crops], dim=0) if crops
                   else torch.zeros((1, 3, BASE_SIZE, BASE_SIZE))).to(dtype)
    return {
        "input_ids": torch.LongTensor(tokens).unsqueeze(0).to(device),
        "images": [(images_crop.to(device), images_ori.to(device))],
        "images_seq_mask": torch.tensor(seq_mask, dtype=torch.bool).unsqueeze(0).to(device),
        "images_spatial_crop": torch.tensor([[width_crops, height_crops]], dtype=torch.long),
        "visual_tokens": len(image_tokens),
    }


def run(args: argparse.Namespace, spec: dict) -> None:
    import torch
    import transformers
    from transformers import AutoModel, AutoTokenizer

    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.generation import generation_kwargs
    from labbs2026.thai_marks.remote import load_items, shard_items
    from labbs2026.model_survey.plan import image_sha256, run_items

    role = spec["models"][args.role]
    out_dir = Path(spec["artifact_dir"]) / "m1" / args.role
    if args.shards > 1:
        out_dir = out_dir / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    run_on = spec.get("run_on", "calibration")
    selected = run_items(ordered, calibration, id_col, run_on)
    if int(spec.get("limit") or 0):
        selected = selected[:int(spec["limit"])]
    selected = shard_items(selected, args.shard, args.shards)
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({"run_on": run_on, "calibration": sorted(calibration),
                   "run_ids": [id_col[i] for i in selected]},
                  handle, ensure_ascii=False, indent=1)

    def load(dtype_name: str):
        dtype = {"float16": torch.float16, "float32": torch.float32}[dtype_name]
        tokenizer = AutoTokenizer.from_pretrained(role["model_id"], revision=role["revision"],
                                                  trust_remote_code=True)
        model = AutoModel.from_pretrained(role["model_id"], revision=role["revision"],
                                          trust_remote_code=True, use_safetensors=True,
                                          _attn_implementation="eager")
        return model.eval().cuda().to(dtype), tokenizer, dtype

    def finite(model, tokenizer, dtype, image, content) -> bool:
        inputs = prepare_inputs(sys.modules[type(model).__module__], tokenizer, image, content, dtype, torch)
        inputs.pop("visual_tokens")
        with torch.inference_mode():
            logits = model(**inputs).logits[:, -1]
        return bool(torch.isfinite(logits).all().item())

    first = dataset[selected[0]]
    probe = runtime.resize_policy(first["image"].convert("RGB"))
    probe_content = content_for(role["prompts"][0], first["question"], spec["prompts"])
    dtype_name = spec["dtype_preferred"]
    model, tokenizer, dtype = load(dtype_name)
    if not finite(model, tokenizer, dtype, probe, probe_content):
        del model
        torch.cuda.empty_cache()
        dtype_name = spec["dtype_fallback"]
        model, tokenizer, dtype = load(dtype_name)
        if not finite(model, tokenizer, dtype, probe, probe_content):
            raise RuntimeError("non-finite logits in both fp16 and fp32")
    remote = sys.modules[type(model).__module__]
    setup_seconds = time.perf_counter() - started
    gen_kwargs = {**generation_kwargs(spec["generation"], int(spec["max_new_tokens"])),
                  "use_cache": bool(spec["use_cache"]), "eos_token_id": tokenizer.eos_token_id}
    max_new_tokens = int(spec["max_new_tokens"])

    deadline = float(role["unit_deadline_hours"]) * 3600
    failures: list[dict] = []
    attempted: list[str] = []
    not_run: list[str] = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for position, index in enumerate(selected):
            if time.perf_counter() - started > deadline:
                not_run = [id_col[i] for i in selected[position:]]
                break
            row = dataset[index]
            attempted.append(row["Id"])
            original = row["image"].convert("RGB")
            image = runtime.resize_policy(original)
            base = {"id": row["Id"], "task": row["Task"], "category": row["category"],
                    "reference": row["answer"],
                    "source_size": list(original.size), "resized_size": list(image.size),
                    "image_sha256": image_sha256(original)}
            for kind in role["prompts"]:
                try:
                    torch.cuda.synchronize()
                    t0 = time.perf_counter()
                    inputs = prepare_inputs(remote, tokenizer, image,
                                            content_for(kind, row["question"], spec["prompts"]), dtype, torch)
                    visual = inputs.pop("visual_tokens")
                    t1 = time.perf_counter()
                    torch.cuda.reset_peak_memory_stats()
                    with torch.inference_mode():
                        produced = model.generate(**inputs, **gen_kwargs)
                    torch.cuda.synchronize()
                    t2 = time.perf_counter()
                except Exception as exc:  # recorded, never scored as an output
                    failures.append({"id": row["Id"], "prompt": kind,
                                     "error": f"{type(exc).__name__}: {exc}"[:800]})
                    torch.cuda.empty_cache()
                    continue
                new = produced[0][inputs["input_ids"].shape[-1]:]
                text = tokenizer.decode(new, skip_special_tokens=False)
                if text.endswith(STOP):
                    text = text[:-len(STOP)]
                generated = int(new.shape[-1])
                handle.write(json.dumps({
                    **base, "prompt_kind": kind, "raw_output": text.strip(),
                    "generated_tokens": generated, "reached_max_new_tokens": generated >= max_new_tokens,
                    "visual_tokens": visual, "prompt_tokens": int(inputs["input_ids"].shape[-1]),
                    "seconds_processor": t1 - t0, "seconds_generate": t2 - t1,
                    "seconds_per_generated_token": (t2 - t1) / max(1, generated),
                    "peak_bytes": int(torch.cuda.max_memory_allocated()),
                }, ensure_ascii=False) + "\n")
                handle.flush()

    freeze = subprocess.run([shutil.which("uv") or "uv", "pip", "freeze", "--python", sys.executable],
                            capture_output=True, text=True).stdout
    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "m1", "runner": "model_survey.remote_m6b", "role": args.role,
            "shard": args.shard, "shards": args.shards,
            "model_id": role["model_id"], "revision": role["revision"], "prompts": role["prompts"],
            "dtype_used": dtype_name, "attention": "eager", "items": len(attempted),
            "selected_items": len(selected), "deadline_seconds": deadline, "not_run": not_run,
            "failures": failures, "setup_seconds": setup_seconds,
            "generation": {"requested": gen_kwargs},
            "preprocessing": {"base_size": BASE_SIZE, "crop_size": CROP_SIZE, "crop_mode": True,
                              "template": "plain", "image_token_id": IMAGE_TOKEN_ID},
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "pip_freeze": freeze.splitlines(),
            "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"][spec["config_path"]],
        }, handle, ensure_ascii=False, indent=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--stage", choices=("bootstrap", "run"), default="bootstrap")
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    (bootstrap if args.stage == "bootstrap" else run)(args, spec)


if __name__ == "__main__":
    main()
