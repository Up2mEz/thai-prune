"""Remote entry point for one model's INPUT_SIDE_D1 process on Kaggle.

Items: the same 69 Fine-grained calibration items as FIND_VS_READ_F1, prepared
the same way. For every item, one arm per shift `d` (`phase.SHIFTS`), each the
grid-aligned crop moved by `d` with the F1 crop prompt. Generation, recording
and the no-image rule are F1's (`find_vs_read.remote.generate`).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import time
import traceback
from pathlib import Path

from labbs2026.find_vs_read.geometry import crop_rect, parse_box, prepare_page
from labbs2026.input_side.phase import shifted_crop


def arm_name(d: int) -> str:
    return f"D{d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", choices=("base", "typhoon"), required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    if hashlib.sha256(spec["crop_prompt"].encode("utf-8")).hexdigest() != spec["crop_prompt_sha256"]:
        raise RuntimeError("crop prompt does not match its registered sha256")

    import torch
    import transformers

    from labbs2026.find_vs_read.remote import generate
    from labbs2026.thai_marks import runtime as t1_runtime
    from labbs2026.thai_marks.remote import load_items

    out_dir = Path(spec["artifact_dir"]) / "d1" / args.role
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
    if not t1_runtime.logits_are_finite(model, processor, probe, spec["crop_prompt"], device):
        del model
        torch.cuda.empty_cache()
        dtype = spec["dtype_fallback"]
        model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
        if not t1_runtime.logits_are_finite(model, processor, probe, spec["crop_prompt"], device):
            raise RuntimeError("non-finite logits in both fp16 and fp32")

    failures = []
    shifts = [int(d) for d in spec["shifts"]]
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for index in selected:
            row = dataset[index]
            page = prepare_page(row["image"].convert("RGB"))
            box = parse_box(row["question"])
            rect = crop_rect(box, page.size, margin=float(spec["crop_margin"]))
            record = {"id": row["Id"], "task": row["Task"], "category": row["category"],
                      "reference": row["answer"], "dtype": dtype,
                      "geometry": {"source_size": list(row["image"].size), "page_size": list(page.size),
                                   "box": list(box), "crop_rect_page": list(rect)},
                      "arms": {}}
            for d in shifts:
                name = arm_name(d)
                try:
                    image = shifted_crop(page, rect, d)
                    record["arms"][name] = generate(model, processor, image, spec["crop_prompt"],
                                                    generation=spec["generation"],
                                                    max_new_tokens=int(spec["max_new_tokens"]), device=device)
                except Exception as exc:  # recorded per arm; never scored as an output
                    failures.append({"id": row["Id"], "arm": name, "error": f"{type(exc).__name__}: {exc}"[:800],
                                     "trace": traceback.format_exc()[-1500:]})
                    record["arms"][name] = {"failed": True}
                torch.cuda.empty_cache()
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "d1", "role": args.role, "model_id": model_spec["model_id"],
            "revision": model_spec["revision"], "dtype_used": dtype, "items": len(selected),
            "shifts": shifts, "failures": failures, "generation": spec["generation"],
            "max_new_tokens": int(spec["max_new_tokens"]), "crop_margin": spec["crop_margin"],
            "crop_prompt": spec["crop_prompt"], "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/input_side/d1.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
