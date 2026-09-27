"""Remote entry point for one (test, model) process on Kaggle.

The split is recomputed here from the registered seed, and only calibration
items are run. Records are appended line by line so a crash loses at most the
item in flight, and a consistency failure in T2 stops the process instead of
writing scores that cannot be trusted.
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

from labbs2026.thai_marks.normalize import collapse_whitespace
from labbs2026.thai_marks.orthography import find_sites, sample_sites
from labbs2026.thai_marks.split import calibration_ids


class ConsistencyFailure(RuntimeError):
    pass


def _prompt(spec: dict, source: Path) -> str:
    path = source / spec["typhoon_prompt_file"]
    text = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != spec["typhoon_prompt_sha256"]:
        raise RuntimeError(f"Typhoon prompt hash {digest} does not match the registration")
    return text


def load_items(spec: dict):
    """The benchmark, the selected rows' indices in Id order, and the calibration ids.

    Selection reads only the text columns; images are decoded one row at a time
    later, because decoding every image up front exhausts memory.
    """
    from datasets import load_dataset

    dataset = load_dataset(spec["benchmark_repo"], split=spec["benchmark_split"],
                           revision=spec["benchmark_revision"])
    tasks = set(spec["tasks"])
    task_col, id_col, category_col = dataset["Task"], dataset["Id"], dataset["category"]
    indices = [i for i, task in enumerate(task_col) if task in tasks]
    calibration = calibration_ids(
        ((id_col[i], task_col[i], category_col[i]) for i in indices),
        seed=int(spec["split_seed"]), fraction=float(spec["calibration_fraction"]),
    )
    ordered = sorted(indices, key=lambda i: id_col[i])
    return dataset, ordered, calibration, id_col


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--test", choices=("t1", "t2"), required=True)
    parser.add_argument("--role", choices=("base", "typhoon"), required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    source = Path(spec["source_dir"])

    import torch
    import transformers

    from labbs2026.thai_marks import runtime

    out_dir = Path(spec["artifact_dir"]) / args.test / args.role
    out_dir.mkdir(parents=True, exist_ok=False)
    typhoon_prompt = _prompt(spec, source)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({
            "calibration": sorted(calibration),
            "locked": sorted(id_col[i] for i in ordered if id_col[i] not in calibration),
            "run_ids": [id_col[i] for i in selected],
        }, handle, ensure_ascii=False, indent=1)

    model_spec = spec["models"][args.role]
    device = "cuda"
    dtype = spec["dtype_preferred"]
    model, processor = runtime.load(model_spec["model_id"], model_spec["revision"], dtype, device)
    probe = runtime.resize_policy(dataset[selected[0]]["image"].convert("RGB"))
    if not runtime.logits_are_finite(model, processor, probe, typhoon_prompt, device):
        del model
        torch.cuda.empty_cache()
        dtype = spec["dtype_fallback"]
        model, processor = runtime.load(model_spec["model_id"], model_spec["revision"],
                                        dtype, device)
        if not runtime.logits_are_finite(model, processor, probe, typhoon_prompt, device):
            raise RuntimeError("non-finite logits in both fp16 and fp32")

    failures = []
    records_path = out_dir / "records.jsonl"
    with io.open(records_path, "w", encoding="utf-8", newline="\n") as handle:
        for index in selected:
            row = dataset[index]
            original = row["image"].convert("RGB")
            image = runtime.resize_policy(original)
            base = {
                "id": row["Id"], "task": row["Task"], "category": row["category"],
                "reference": row["answer"],
                "source_size": list(original.size), "resized_size": list(image.size),
            }
            if args.test == "t1":
                for prompt_kind in spec["t1_prompts"]:
                    prompt = typhoon_prompt if prompt_kind == "TYPHOON_CARD" else row["question"]
                    try:
                        result = runtime.generate(model, processor, image, prompt,
                                                  max_new_tokens=int(spec["max_new_tokens"]),
                                                  device=device)
                    except Exception as exc:  # recorded, never scored as an output
                        failures.append({"id": row["Id"], "prompt": prompt_kind,
                                         "error": f"{type(exc).__name__}: {exc}"[:800]})
                        torch.cuda.empty_cache()
                        continue
                    handle.write(json.dumps({**base, "prompt_kind": prompt_kind, **result},
                                            ensure_ascii=False) + "\n")
                    handle.flush()
            else:
                reference = collapse_whitespace(row["answer"])
                sites = sample_sites(find_sites(reference), row["Id"])
                if not sites:
                    continue
                try:
                    scored = runtime.score_item(
                        model, processor, image, typhoon_prompt, reference, sites,
                        device=device,
                        tolerance=float(spec["consistency_tolerance"][dtype]),
                        window_after=int(spec["window_after_chars"]),
                    )
                except RuntimeError as exc:
                    if "refusing to record" in str(exc):
                        raise ConsistencyFailure(str(exc)) from exc
                    failures.append({"id": row["Id"], "error": f"{type(exc).__name__}: {exc}"[:800],
                                     "trace": traceback.format_exc()[-1500:]})
                    torch.cuda.empty_cache()
                    continue
                handle.write(json.dumps({**base, "reference_collapsed": reference,
                                         "sites": scored}, ensure_ascii=False) + "\n")
                handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": args.test, "role": args.role,
            "model_id": model_spec["model_id"], "revision": model_spec["revision"],
            "dtype_used": dtype, "items": len(selected), "failures": failures,
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda_device": torch.cuda.get_device_name(0), "platform": platform.platform(),
            "git_sha": spec["git_sha"], "run_id": spec["run_id"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
