"""Remote entry point for one model's SPEC_DECODE_S1 process on Kaggle.

The calibration split and the benchmark loading are T1's, reused unchanged.
Every item runs every arm on the same loaded model, in the registered rotation.
Records are appended line by line. Unlike T1, any exception inside `generate`
stops the run (registration §7) instead of being recorded and skipped: a
speed comparison with silently missing arm-items would be biased.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
from pathlib import Path

from labbs2026.spec_decode.design import schedule
from labbs2026.spec_decode.identity import compare_outputs, truncate_new_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", choices=("base", "typhoon"), required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    source = Path(spec["source_dir"])

    import torch
    import transformers

    from labbs2026.spec_decode import runtime
    from labbs2026.thai_marks import runtime as t1_runtime
    from labbs2026.thai_marks.remote import _prompt, load_items

    out_dir = Path(spec["artifact_dir"]) / "s1" / args.role
    out_dir.mkdir(parents=True, exist_ok=False)
    prompt = _prompt(spec, source)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    row_of = {id_col[i]: i for i in ordered if id_col[i] in calibration}
    warmup, timed = schedule(sorted(row_of), int(spec["split_seed"]), spec["arm_rotation"],
                             int(spec["warmup_items"]), int(spec.get("limit") or 0))
    arms = spec["arms"]
    max_new = int(spec["max_new_tokens"])
    with io.open(out_dir / "schedule.json", "w", encoding="utf-8") as handle:
        json.dump({"warmup": warmup, "timed": timed, "arms": arms}, handle,
                  ensure_ascii=False, indent=1)

    model_spec = spec["models"][args.role]
    device = "cuda"
    dtype = spec["dtype_preferred"]
    model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
    probe = t1_runtime.resize_policy(dataset[row_of[(warmup or [timed[0][0]])[0]]]["image"].convert("RGB"))
    if not t1_runtime.logits_are_finite(model, processor, probe, prompt, device):
        del model
        torch.cuda.empty_cache()
        dtype = spec["dtype_fallback"]
        model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
        if not t1_runtime.logits_are_finite(model, processor, probe, prompt, device):
            raise RuntimeError("non-finite logits in both fp16 and fp32")

    plan = [(item, sorted(arms), True) for item in warmup] + [(item, order, False) for item, order in timed]
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for item_id, order, is_warmup in plan:
            row = dataset[row_of[item_id]]
            original = row["image"].convert("RGB")
            image = t1_runtime.resize_policy(original)
            inputs = t1_runtime.prompt_inputs(processor, image, prompt, device)
            base = {
                "id": row["Id"], "task": row["Task"], "category": row["category"],
                "warmup": is_warmup, "arm_order": order,
                "source_size": list(original.size), "resized_size": list(image.size),
                "visual_tokens": int((inputs["input_ids"] == model.config.image_token_id).sum().item()),
                "dtype": dtype,
            }
            outputs = {}
            for arm in order:
                result = runtime.run_arm(model, inputs, arms[arm], max_new_tokens=max_new, device=device)
                result["text"] = processor.decode(
                    truncate_new_tokens(result["new_token_ids"], 0, max_new), skip_special_tokens=True)
                outputs[arm] = result
            ref = truncate_new_tokens(outputs["REF"]["new_token_ids"], 0, max_new)
            extra = {"seconds_to_first_token": runtime.seconds_to_first_token(model, inputs, device=device)}
            identity = {}
            for arm in order:
                if arm == "REF":
                    continue
                cmp = compare_outputs(ref, truncate_new_tokens(outputs[arm]["new_token_ids"], 0, max_new))
                entry = {"identical": cmp.identical, "first_divergence": cmp.first_divergence,
                         "reference_length": cmp.reference_length,
                         "candidate_length": cmp.candidate_length}
                if not cmp.identical and cmp.first_divergence < len(ref):
                    entry["ref_margin"] = runtime.ref_margin_at(model, inputs, ref, cmp.first_divergence)
                    cand = truncate_new_tokens(outputs[arm]["new_token_ids"], 0, max_new)
                    entry["candidate_token"] = (cand[cmp.first_divergence]
                                                if cmp.first_divergence < len(cand) else None)
                identity[arm] = entry
            handle.write(json.dumps({**base, "reference": row["answer"], "arms": outputs,
                                     "ref_extra": extra, "identity": identity},
                                    ensure_ascii=False) + "\n")
            handle.flush()
            del inputs
            torch.cuda.empty_cache()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "s1", "role": args.role,
            "model_id": model_spec["model_id"], "revision": model_spec["revision"],
            "dtype_used": dtype, "warmup_items": len(warmup), "timed_items": len(timed),
            "arms": sorted(arms), "max_new_tokens": max_new,
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(),
            "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/spec_decode/s1.yaml"],
            "uv_lock_sha256": spec["expected_file_hashes"]["uv.lock"],
            "budget": spec["budget"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
