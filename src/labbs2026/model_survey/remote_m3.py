"""Remote entry point for one MODEL_SURVEY_M3 unit (Wayu with loop escape, one position shard) on Kaggle.

M1's items, image policy, prompt, decoding and record format, plus the escape
fields of `model_survey.escape.generate_with_escape`. Records hold the
reference and the output; no image is written.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
from pathlib import Path

from labbs2026.model_survey.plan import resolve_prompt
from labbs2026.model_survey.remote import logits_are_finite

RESOLVED_KEYS = ("do_sample", "num_beams", "max_new_tokens", "repetition_penalty", "no_repeat_ngram_size",
                 "temperature", "top_p", "top_k", "use_cache", "eos_token_id", "pad_token_id")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    role = spec["models"][spec["model_role"]]
    settings = spec["escape"]

    import torch
    import transformers

    from labbs2026.model_survey.escape import generate_with_escape
    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.generation import generation_kwargs
    from labbs2026.thai_marks.remote import load_items, shard_items

    out_dir = Path(spec["artifact_dir"]) / "m3" / settings["arm"] / f"shard-{args.shard}-of-{args.shards}"
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
    kind = spec["prompt_kind"]
    failures: list[dict] = []
    setup_seconds = resolved = kwargs = None
    if selected:
        model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
        first = dataset[selected[0]]
        probe = runtime.resize_policy(first["image"].convert("RGB"))
        probe_prompt = resolve_prompt(kind, first["question"], spec["prompts"])
        if not logits_are_finite(model, processor, probe, probe_prompt, device, runtime, torch):
            del model
            torch.cuda.empty_cache()
            dtype = spec["dtype_fallback"]
            model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
            if not logits_are_finite(model, processor, probe, probe_prompt, device, runtime, torch):
                raise RuntimeError("non-finite logits in both fp16 and fp32")
        setup_seconds = time.perf_counter() - started
        kwargs = {**generation_kwargs(spec["generation"], int(spec["max_new_tokens"])),
                  "use_cache": bool(spec["use_cache"])}
        resolved = runtime.resolved_generation(model, kwargs)

    deadline = float(spec["unit_deadline_hours"]) * 3600
    attempted: list[str] = []
    not_run: list[str] = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for position, index in enumerate(selected):
            if time.perf_counter() - started > deadline:   # registered stop: no item starts past it
                not_run = [id_col[i] for i in selected[position:]]
                break
            row = dataset[index]
            attempted.append(row["Id"])
            original = row["image"].convert("RGB")
            image = runtime.resize_policy(original)
            try:
                result = generate_with_escape(
                    model, processor, image, resolve_prompt(kind, row["question"], spec["prompts"]),
                    generation=kwargs, device=device, max_escapes=int(settings["max_escapes"]),
                    every=int(settings["every"]), max_total_steps=int(settings["max_total_steps"]))
            except Exception as exc:  # recorded, never scored as an output
                failures.append({"id": row["Id"], "error": f"{type(exc).__name__}: {exc}"[:800]})
                torch.cuda.empty_cache()
                continue
            handle.write(json.dumps({"id": row["Id"], "task": row["Task"], "category": row["category"],
                                     "reference": row["answer"], "source_size": list(original.size),
                                     "resized_size": list(image.size), "prompt_kind": kind,
                                     "arm": settings["arm"], **result}, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "m3", "arm": settings["arm"], "shard": args.shard, "shards": args.shards,
            "model_id": role["model_id"], "revision": role["revision"], "prompt_kind": kind,
            "dtype_used": dtype, "items": len(attempted), "selected_items": len(selected),
            "deadline_seconds": deadline, "not_run": not_run, "failures": failures,
            "setup_seconds": setup_seconds, "requested": kwargs, "escape": settings,
            "resolved": {k: resolved.get(k) for k in RESOLVED_KEYS} if resolved else None,
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/model_survey/m3.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
