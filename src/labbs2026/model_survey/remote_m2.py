"""Remote entry point for one MODEL_SURVEY_M2 unit (Wayu, one decoding arm) on Kaggle.

M1's items, image policy, prompt and record format; only decoding differs
(`model_survey.m2.arm_kwargs`). A sampling arm seeds torch before every item
with `model_survey.m2.item_seed`. Records hold the reference and the output;
no image is written.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
from pathlib import Path

from labbs2026.model_survey.m2 import arm_kwargs, item_seed
from labbs2026.model_survey.plan import resolve_prompt
from labbs2026.model_survey.remote import logits_are_finite

RESOLVED_KEYS = ("do_sample", "num_beams", "max_new_tokens", "repetition_penalty", "no_repeat_ngram_size",
                 "temperature", "top_p", "top_k", "use_cache", "eos_token_id", "pad_token_id")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    role = spec["models"][spec["model_role"]]
    arm = spec["arms"][args.arm]

    import torch
    import transformers

    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.remote import load_items

    out_dir = Path(spec["artifact_dir"]) / "m2" / args.arm
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({"calibration": sorted(calibration), "run_ids": [id_col[i] for i in selected]},
                  handle, ensure_ascii=False, indent=1)

    device = "cuda"
    dtype = spec["dtype_preferred"]
    kind = spec["prompt_kind"]
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
    kwargs = {**arm_kwargs(spec["generation"], arm, int(spec["max_new_tokens"])),
              "use_cache": bool(spec["use_cache"])}
    resolved = runtime.resolved_generation(model, kwargs)

    deadline = float(spec["unit_deadline_hours"]) * 3600
    failures: list[dict] = []
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
            seed = item_seed(int(spec["seed"]), row["Id"]) if kwargs["do_sample"] else None
            if seed is not None:
                torch.manual_seed(seed)
            try:
                result = runtime.generate(model, processor, image, resolve_prompt(kind, row["question"], spec["prompts"]),
                                          generation=kwargs, device=device)
            except Exception as exc:  # recorded, never scored as an output
                failures.append({"id": row["Id"], "error": f"{type(exc).__name__}: {exc}"[:800]})
                torch.cuda.empty_cache()
                continue
            handle.write(json.dumps({"id": row["Id"], "task": row["Task"], "category": row["category"],
                                     "reference": row["answer"], "source_size": list(original.size),
                                     "resized_size": list(image.size), "prompt_kind": kind, "arm": args.arm,
                                     "seed": seed, **result}, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "m2", "arm": args.arm, "model_id": role["model_id"], "revision": role["revision"],
            "prompt_kind": kind, "dtype_used": dtype, "items": len(attempted), "selected_items": len(selected),
            "deadline_seconds": deadline, "not_run": not_run, "failures": failures,
            "setup_seconds": setup_seconds, "requested": kwargs,
            "resolved": {k: resolved.get(k) for k in RESOLVED_KEYS},
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/model_survey/m2.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
