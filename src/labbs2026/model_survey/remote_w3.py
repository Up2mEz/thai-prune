"""Remote entry point for one W3 (T2 on another model) process on Kaggle.

T2's item loop (`thai_marks.remote`, `--test t2`) for a model that is not one
of T1's two roles: the same split, sites, prompt, fp32 scoring and consistency
guard, imported read-only from `thai_marks`. Two differences, both outside the
scoring:

- the role is any model in the W3 config, not only `base` / `typhoon`;
- a role with `device_map: two_gpus` is loaded over both T4s
  (`device_map="auto"`), because Qwen3-VL-4B in fp32 does not fit one.

A unit stops starting items after its registered deadline and lists the items
it did not run. A consistency failure stops the process, as in T2.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import time
import traceback
from pathlib import Path

from labbs2026.thai_marks.normalize import collapse_whitespace
from labbs2026.thai_marks.orthography import find_sites, sample_sites
from labbs2026.thai_marks.remote import ConsistencyFailure, _prompt, load_items, shard_items

TWO_GPU_MEMORY = {0: "12GiB", 1: "14GiB"}  # GPU 0 also holds the activations and the inputs


def load(model_spec: dict, dtype_name: str, device: str, runtime):
    """`runtime.load`, or the same model spread over both GPUs."""
    if model_spec.get("device_map") != "two_gpus":
        return runtime.load(model_spec["model_id"], model_spec["revision"], dtype_name, device)
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    dtype = {"float16": torch.float16, "float32": torch.float32}[dtype_name]
    processor = AutoProcessor.from_pretrained(model_spec["model_id"], revision=model_spec["revision"])
    model = AutoModelForImageTextToText.from_pretrained(
        model_spec["model_id"], revision=model_spec["revision"], dtype=dtype,
        attn_implementation="sdpa", device_map="auto", max_memory=TWO_GPU_MEMORY,
    ).eval()
    return model, processor


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
    model_spec = spec["models"][args.role]
    source = Path(spec["source_dir"])

    out_dir = Path(spec["artifact_dir"]) / "t2" / args.role
    if args.shards > 1:
        out_dir = out_dir / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)

    import torch
    import transformers

    from labbs2026.thai_marks import runtime

    typhoon_prompt = _prompt(spec, source)
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
    dtype = spec["t2_dtype"]
    model, processor = load(model_spec, dtype, device, runtime)
    probe = runtime.resize_policy(dataset[selected[0]]["image"].convert("RGB"))
    if not runtime.logits_are_finite(model, processor, probe, typhoon_prompt, device):
        raise RuntimeError(f"non-finite logits in {dtype}")
    setup_seconds = time.perf_counter() - started
    placement = sorted({str(d) for d in getattr(model, "hf_device_map", {}).values()}) or [device]

    deadline = float(model_spec["unit_deadline_hours"]) * 3600
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
                    "source_size": list(original.size), "resized_size": list(image.size)}
            reference = collapse_whitespace(row["answer"])
            sites = sample_sites(find_sites(reference), row["Id"])
            if not sites:
                continue
            item_started = time.perf_counter()
            try:
                scored = runtime.score_item(
                    model, processor, image, typhoon_prompt, reference, sites, device=device,
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
            handle.write(json.dumps({**base, "reference_collapsed": reference, "sites": scored,
                                     "seconds": time.perf_counter() - item_started},
                                    ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "t2", "role": args.role, "shard": args.shard, "shards": args.shards,
            "model_id": model_spec["model_id"], "revision": model_spec["revision"],
            "dtype_used": dtype, "placement": placement, "items": len(attempted),
            "selected_items": len(selected), "deadline_seconds": deadline, "not_run": not_run,
            "failures": failures, "setup_seconds": setup_seconds,
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda_device": torch.cuda.get_device_name(0), "platform": platform.platform(),
            "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"][spec["config_path"]],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
