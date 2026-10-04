"""Remote entry point for one model's FIND_VS_READ_F1 process on Kaggle.

Items: T1's seeded calibration split applied to the Fine-grained task (locked
never touched). Every item runs every arm on the same loaded model, from one
prepared page (`geometry.prepare_page`). Failures are recorded per arm and
item; the run continues so the analysis can report n per arm.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
import traceback
from pathlib import Path

from labbs2026.find_vs_read.geometry import (
    MIN_PIXELS,
    crop_padded,
    crop_rect,
    draw_rect,
    image_sha256,
    parse_box,
    prepare_page,
    rescaled_crop,
)


def question_without_clause(question: str, clause: str) -> str:
    """The item question minus its leading coordinate-system clause (addendum 2)."""
    if not question.startswith(clause):
        raise ValueError("question does not start with the registered clause")
    return question[len(clause):]


def arm_input(arm: str, source, page, question: str, rect, box, *, crop_prompt: str, margin: float,
              clause: str = ""):
    """(image, prompt) for one arm. All but CROP_RESCALED come from the same prepared page."""
    if arm == "WHOLE":
        return page, question
    if arm == "WHOLE_MARKED":
        return draw_rect(page, rect), question
    if arm == "WHOLE_NOCLAUSE":
        return page, question_without_clause(question, clause)
    if arm == "CROP_SAME_SCALE":
        return crop_padded(page, rect), crop_prompt
    if arm == "CROP_RESCALED":
        return rescaled_crop(source, box, margin=margin)[0], crop_prompt
    raise ValueError(f"unknown arm {arm!r}")


def geometry_record(source, page, box, rect, *, margin: float) -> dict:
    """Everything needed to reproduce the inputs, without storing any image."""
    rescaled, native = rescaled_crop(source, box, margin=margin)
    page_scale = page.width / source.width
    native_w = native[2] - native[0]
    return {
        "source_size": list(source.size), "page_size": list(page.size), "box": list(box),
        "page_scale": page_scale,
        "crop_rect_page": list(rect),
        "crop_same_scale_under_floor": (rect[2] - rect[0]) * (rect[3] - rect[1]) < MIN_PIXELS,
        "crop_rect_native": list(native), "crop_rescaled_size": list(rescaled.size),
        "crop_rescaled_scale": rescaled.width / native_w,
        "magnification_rescaled_vs_page": (rescaled.width / native_w) / page_scale,
    }


def generate(model, processor, image, prompt: str, *, generation: dict, max_new_tokens: int,
             device: str) -> dict:
    import torch

    from labbs2026.thai_marks import runtime as t1_runtime

    inputs = t1_runtime.prompt_inputs(processor, image, prompt, device)
    prompt_len = int(inputs["input_ids"].shape[-1])
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode():
        produced = model.generate(**inputs, **generation, max_new_tokens=max_new_tokens)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    new_ids = [int(t) for t in produced[0][prompt_len:].tolist()]
    return {
        "raw_output": processor.decode(new_ids, skip_special_tokens=True),
        "generated_tokens": len(new_ids),
        "reached_max_new_tokens": len(new_ids) >= max_new_tokens,
        "prompt_tokens": prompt_len,
        "visual_tokens": int((inputs["input_ids"] == model.config.image_token_id).sum().item()),
        "image_size": list(image.size),
        "image_sha256": image_sha256(image),
        "seconds_generate": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", choices=("base", "typhoon"), required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))

    import torch
    import transformers

    from labbs2026.thai_marks import runtime as t1_runtime
    from labbs2026.thai_marks.remote import load_items

    import hashlib

    if hashlib.sha256(spec["crop_prompt"].encode("utf-8")).hexdigest() != spec["crop_prompt_sha256"]:
        raise RuntimeError("crop prompt does not match its registered sha256")
    if hashlib.sha256(spec["question_clause"].encode("utf-8")).hexdigest() != spec["question_clause_sha256"]:
        raise RuntimeError("question clause does not match its registered sha256")
    out_dir = Path(spec["artifact_dir"]) / "f1" / args.role
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({"calibration": sorted(calibration), "run_ids": [id_col[i] for i in selected]}, handle,
                  ensure_ascii=False, indent=1)

    model_spec = spec["models"][args.role]
    device = "cuda"
    dtype = spec["dtype_preferred"]
    model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
    first = dataset[selected[0]]
    probe = prepare_page(first["image"])
    if not t1_runtime.logits_are_finite(model, processor, probe, first["question"], device):
        del model
        torch.cuda.empty_cache()
        dtype = spec["dtype_fallback"]
        model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
        if not t1_runtime.logits_are_finite(model, processor, probe, first["question"], device):
            raise RuntimeError("non-finite logits in both fp16 and fp32")

    failures = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for index in selected:
            row = dataset[index]
            source = row["image"].convert("RGB")
            page = prepare_page(source)
            box = parse_box(row["question"])
            margin = float(spec["crop_margin"])
            rect = crop_rect(box, page.size, margin=margin)
            record = {"id": row["Id"], "task": row["Task"], "category": row["category"],
                      "reference": row["answer"], "question": row["question"], "dtype": dtype,
                      "geometry": geometry_record(source, page, box, rect, margin=margin), "arms": {}}
            for arm in spec["arms"]:
                try:
                    image, prompt = arm_input(arm, source, page, row["question"], rect, box,
                                              crop_prompt=spec["crop_prompt"], margin=margin,
                                              clause=spec["question_clause"])
                    record["arms"][arm] = generate(model, processor, image, prompt,
                                                   generation=spec["generation"],
                                                   max_new_tokens=int(spec["max_new_tokens"]), device=device)
                except Exception as exc:  # recorded per arm; never scored as an output
                    failures.append({"id": row["Id"], "arm": arm, "error": f"{type(exc).__name__}: {exc}"[:800],
                                     "trace": traceback.format_exc()[-1500:]})
                    record["arms"][arm] = {"failed": True}
                torch.cuda.empty_cache()
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "f1", "role": args.role, "model_id": model_spec["model_id"],
            "revision": model_spec["revision"], "dtype_used": dtype, "items": len(selected),
            "arms": spec["arms"], "failures": failures, "generation": spec["generation"],
            "max_new_tokens": int(spec["max_new_tokens"]), "crop_margin": spec["crop_margin"],
            "crop_prompt": spec["crop_prompt"], "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/find_vs_read/f1.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
