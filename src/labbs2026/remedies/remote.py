"""Remote entry point for one model's REMEDIES_R1 process on Kaggle.

Items: the registered pilot sub-split of T1's calibration split (locked never
touched). Every item runs every arm on the same loaded model; FULL first. A
failure inside one arm is recorded with the arm and item and the run goes on,
so the analysis can report n per arm instead of silently dropping items.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
import traceback
from pathlib import Path

from labbs2026.remedies.design import arm_names, noise_seed, pilot_ids


def _sync() -> None:
    import torch

    if torch.cuda.is_available():
        torch.cuda.synchronize()


def run_one(model, processor, image, prompt: str, item_id: str, arm: dict, *, seed: int,
            generation: dict, max_new_tokens: int, eos_ids: list[int], device: str) -> dict:
    import torch

    from labbs2026.remedies.contrastive import Weight, contrastive_greedy, mark_protector, noised_image
    from labbs2026.remedies.pai import amplified_image_attention
    from labbs2026.thai_marks import runtime as t1_runtime

    inputs = t1_runtime.prompt_inputs(processor, image, prompt, device)
    prompt_len = int(inputs["input_ids"].shape[-1])
    out: dict = {"prompt_tokens": prompt_len}
    _sync()
    started = time.perf_counter()
    if arm["kind"] in ("generate", "pai"):
        kwargs = {**generation, "max_new_tokens": max_new_tokens}
        with torch.inference_mode():
            if arm["kind"] == "pai":
                n_layers = len(model.model.language_model.layers)
                with amplified_image_attention(model, inputs["input_ids"],
                                               image_token_id=model.config.image_token_id,
                                               layers=range(int(arm["first_layer"]), n_layers),
                                               alpha=float(arm["alpha"])):
                    produced = model.generate(**inputs, **kwargs)
            else:
                produced = model.generate(**inputs, **kwargs)
        new_ids = [int(t) for t in produced[0][prompt_len:].tolist()]
    elif arm["kind"] == "contrastive":
        if arm["contrast"] == "noised_image":
            contrast_image = noised_image(image, step=int(arm["noise_step"]), seed=noise_seed(item_id, seed))
            contrast = t1_runtime.prompt_inputs(processor, contrast_image, prompt, device)
        elif arm["contrast"] == "no_image":
            contrast = t1_runtime.prompt_inputs(processor, None, prompt, device)
        else:
            raise ValueError(f"unknown contrast {arm['contrast']!r}")
        weight = Weight(arm["weight"], alpha=float(arm.get("alpha", 0.0)), lam=float(arm.get("lam", 0.0)),
                        max_weight=float(arm.get("max_weight", 10.0)))
        protect = mark_protector(processor.decode) if arm.get("protect_marks") else None
        result = contrastive_greedy(model, inputs, contrast, weight=weight, beta=float(arm["beta"]),
                                    max_new_tokens=max_new_tokens, eos_token_ids=eos_ids, protect=protect)
        new_ids = result["new_token_ids"]
        out["changed_steps"] = len(result["changed_steps"])
        out["protected_steps"] = len(result["protected_steps"])
        out["first_changed_step"] = result["changed_steps"][0] if result["changed_steps"] else None
    else:
        raise ValueError(f"unknown arm kind {arm['kind']!r}")
    _sync()
    out["seconds_generate"] = time.perf_counter() - started
    out["generated_tokens"] = len(new_ids)
    out["reached_max_new_tokens"] = len(new_ids) >= max_new_tokens
    out["new_token_ids"] = new_ids
    out["raw_output"] = processor.decode(new_ids, skip_special_tokens=True)
    return out


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

    out_dir = Path(spec["artifact_dir"]) / spec["tests"][0] / args.role
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    seed = int(spec["split_seed"])

    dataset, ordered, calibration, id_col = load_items(spec)
    row_of = {id_col[i]: i for i in ordered if id_col[i] in calibration}
    task_col = dataset["Task"]
    ids = pilot_ids(((id_col[i], task_col[i]) for i in row_of.values()), seed=seed,
                    per_task=int(spec["items_per_task"]))
    names = arm_names(spec["arms"], spec.get("smoke_controls"), bool(spec.get("smoke")))
    arms = {**spec["arms"], **(spec.get("smoke_controls") or {})}
    with io.open(out_dir / "schedule.json", "w", encoding="utf-8") as handle:
        json.dump({"items": ids, "arms": names, "arm_specs": {n: arms[n] for n in names}}, handle,
                  ensure_ascii=False, indent=1)

    model_spec = spec["models"][args.role]
    device = "cuda"
    dtype = spec["dtype_preferred"]
    model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
    probe = t1_runtime.resize_policy(dataset[row_of[ids[0]]]["image"].convert("RGB"))
    probe_prompt = dataset[row_of[ids[0]]]["question"]
    if not t1_runtime.logits_are_finite(model, processor, probe, probe_prompt, device):
        del model
        torch.cuda.empty_cache()
        dtype = spec["dtype_fallback"]
        model, processor = t1_runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
        if not t1_runtime.logits_are_finite(model, processor, probe, probe_prompt, device):
            raise RuntimeError("non-finite logits in both fp16 and fp32")
    eos = model.generation_config.eos_token_id
    eos_ids = [int(e) for e in (eos if isinstance(eos, (list, tuple)) else [eos])]

    failures = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for item_id in ids:
            row = dataset[row_of[item_id]]
            original = row["image"].convert("RGB")
            image = t1_runtime.resize_policy(original)
            record = {"id": row["Id"], "task": row["Task"], "category": row["category"],
                      "reference": row["answer"], "prompt": row["question"], "dtype": dtype,
                      "source_size": list(original.size), "resized_size": list(image.size), "arms": {}}
            for name in names:
                try:
                    record["arms"][name] = run_one(
                        model, processor, image, row["question"], item_id, arms[name], seed=seed,
                        generation=spec["generation"], max_new_tokens=int(spec["max_new_tokens"]),
                        eos_ids=eos_ids, device=device)
                except Exception as exc:  # recorded per arm; never scored as an output
                    failures.append({"id": item_id, "arm": name, "error": f"{type(exc).__name__}: {exc}"[:800],
                                     "trace": traceback.format_exc()[-1500:]})
                    record["arms"][name] = {"failed": True}
                torch.cuda.empty_cache()
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": spec["tests"][0], "role": args.role, "smoke": bool(spec.get("smoke")),
            "model_id": model_spec["model_id"], "revision": model_spec["revision"],
            "dtype_used": dtype, "items": len(ids), "arms": names, "failures": failures,
            "eos_token_ids": eos_ids, "generation": spec["generation"],
            "max_new_tokens": int(spec["max_new_tokens"]),
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"][spec["config_path"]],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
