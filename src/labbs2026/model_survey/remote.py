"""Remote entry point for one MODEL_SURVEY_M1 unit (one model, one shard) on Kaggle.

T1's inference with another model: the calibration items of T1's seeded split
(`thai_marks.remote.load_items`), Typhoon's card image policy, T1's pinned
greedy decoding and T1's record format, so `thai_marks.analysis` scores these
records exactly as it scores T1's. Only the model and its registered prompts
differ. Records hold the reference and the output; no image is written.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
from pathlib import Path

from labbs2026.model_survey.plan import resolve_prompt


def logits_are_finite(model, processor, image, prompt: str, device: str, runtime, torch) -> bool:
    """T1's finite-logits probe, also for a forward that has no `logits_to_keep`."""
    inputs = runtime.prompt_inputs(processor, image, prompt, device)
    with torch.inference_mode():
        try:
            logits = model(**inputs, logits_to_keep=1).logits
        except TypeError:
            logits = model(**inputs).logits[:, -1:]
    return bool(torch.isfinite(logits).all().item())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    role = spec["models"][args.role]

    import torch
    import transformers

    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.generation import describe_resolved, generation_kwargs
    from labbs2026.thai_marks.remote import load_items, shard_items

    out_dir = Path(spec["artifact_dir"]) / "m1" / args.role
    if args.shards > 1:
        out_dir = out_dir / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    selected = shard_items(selected, args.shard, args.shards)
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({"calibration": sorted(calibration), "run_ids": [id_col[i] for i in selected]},
                  handle, ensure_ascii=False, indent=1)

    device = "cuda"
    dtype = spec["dtype_preferred"]
    failures: list[dict] = []
    setup_seconds = generation_record = None
    if selected:
        model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
        first = dataset[selected[0]]
        probe = runtime.resize_policy(first["image"].convert("RGB"))
        probe_prompt = resolve_prompt(role["prompts"][0], first["question"], spec["prompts"])
        if not logits_are_finite(model, processor, probe, probe_prompt, device, runtime, torch):
            del model
            torch.cuda.empty_cache()
            dtype = spec["dtype_fallback"]
            model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
            if not logits_are_finite(model, processor, probe, probe_prompt, device, runtime, torch):
                raise RuntimeError("non-finite logits in both fp16 and fp32")
        setup_seconds = time.perf_counter() - started
        gen_kwargs = {**generation_kwargs(spec["generation"], int(spec["max_new_tokens"])),
                      "use_cache": bool(spec["use_cache"])}
        resolved = runtime.resolved_generation(model, gen_kwargs)
        generation_record = {"requested": gen_kwargs, "use_cache": resolved.get("use_cache"),
                             **describe_resolved(resolved)}

    deadline = float(role["unit_deadline_hours"]) * 3600 if role.get("unit_deadline_hours") else None
    attempted: list[str] = []
    not_run: list[str] = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for position, index in enumerate(selected):
            if deadline is not None and time.perf_counter() - started > deadline:
                # registered stop (Addendum 1): no item is started past the unit's deadline
                not_run = [id_col[i] for i in selected[position:]]
                break
            row = dataset[index]
            attempted.append(row["Id"])
            original = row["image"].convert("RGB")
            image = runtime.resize_policy(original)
            base = {"id": row["Id"], "task": row["Task"], "category": row["category"],
                    "reference": row["answer"],
                    "source_size": list(original.size), "resized_size": list(image.size)}
            for kind in role["prompts"]:
                prompt = resolve_prompt(kind, row["question"], spec["prompts"])
                try:
                    result = runtime.generate(model, processor, image, prompt,
                                              generation=gen_kwargs, device=device)
                except Exception as exc:  # recorded, never scored as an output
                    failures.append({"id": row["Id"], "prompt": kind,
                                     "error": f"{type(exc).__name__}: {exc}"[:800]})
                    torch.cuda.empty_cache()
                    continue
                handle.write(json.dumps({**base, "prompt_kind": kind, **result},
                                        ensure_ascii=False) + "\n")
                handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "m1", "role": args.role, "shard": args.shard, "shards": args.shards,
            "model_id": role["model_id"], "revision": role["revision"],
            "prompts": role["prompts"], "dtype_used": dtype, "items": len(attempted),
            "selected_items": len(selected), "deadline_seconds": deadline, "not_run": not_run,
            "failures": failures, "setup_seconds": setup_seconds,
            "generation": generation_record, "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/model_survey/m1.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
