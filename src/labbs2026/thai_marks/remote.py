"""Remote entry point for one (test, model) process on Kaggle.

The split is recomputed here from the registered seed, and only calibration
items are run. Records are appended line by line so a crash loses at most the
item in flight, and a consistency failure in T2 stops the process instead of
writing scores that cannot be trusted.

`--resume-dir` points at this same (test, role) leg's output directory from an
earlier, interrupted submission (mounted read-only, e.g. as a Kaggle dataset
input). If that leg already finished (its `manifest.json` exists), the whole
leg is copied forward and no model is loaded at all. Otherwise, any items
already present in its `records.jsonl` are carried forward and skipped, so a
resumed run only pays for the items it has not already scored.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import shutil
import time
import traceback
from pathlib import Path

from labbs2026.thai_marks.generation import describe_resolved, generation_kwargs
from labbs2026.thai_marks.normalize import collapse_whitespace
from labbs2026.thai_marks.orthography import find_sites, sample_sites
from labbs2026.thai_marks.split import calibration_ids


class ConsistencyFailure(RuntimeError):
    pass


def completed_keys(records_path: Path, test: str) -> set:
    """Keys already scored in a previous attempt's `records.jsonl`.

    T1 records one row per (id, prompt_kind); T2 records one row per id.
    Missing or empty files mean nothing to resume, not an error.
    """
    if not records_path.is_file():
        return set()
    keys: set = set()
    with io.open(records_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if test == "t1":
                keys.add((record["id"], record["prompt_kind"]))
            else:
                keys.add(record["id"])
    return keys


def shard_items(items: list, shard: int, shards: int) -> list:
    """Every `shards`-th item from `shard`: interleaved, so shards stay balanced."""
    return items[shard::shards]


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
    parser.add_argument("--resume-dir", type=Path, default=None,
                        help="a previous, interrupted attempt's output directory "
                             "for this same (test, role) leg")
    parser.add_argument("--shard", type=int, default=0,
                        help="this process's share of the items: selected[shard::shards]")
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    source = Path(spec["source_dir"])

    out_dir = Path(spec["artifact_dir"]) / args.test / args.role
    if args.shards > 1:
        out_dir = out_dir / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)

    resume_dir = args.resume_dir
    previous_manifest = resume_dir / "manifest.json" if resume_dir else None
    if resume_dir and previous_manifest is not None and previous_manifest.is_file():
        # This leg already finished in a prior attempt: carry it forward
        # verbatim and skip model loading entirely -- no CUDA cost paid twice.
        shutil.copyfile(resume_dir / "records.jsonl", out_dir / "records.jsonl")
        if (resume_dir / "split.json").is_file():
            shutil.copyfile(resume_dir / "split.json", out_dir / "split.json")
        manifest = json.loads(previous_manifest.read_text(encoding="utf-8"))
        manifest["resumed_from"] = str(resume_dir)
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    import torch
    import transformers

    from labbs2026.thai_marks import runtime

    typhoon_prompt = _prompt(spec, source)
    started = time.perf_counter()

    load_started = time.perf_counter()
    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    selected = shard_items(selected, args.shard, args.shards)
    with io.open(out_dir / "split.json", "w", encoding="utf-8") as handle:
        json.dump({
            "calibration": sorted(calibration),
            "locked": sorted(id_col[i] for i in ordered if id_col[i] not in calibration),
            "run_ids": [id_col[i] for i in selected],
        }, handle, ensure_ascii=False, indent=1)

    completed = (completed_keys(resume_dir / "records.jsonl", args.test)
                 if resume_dir is not None else set())
    carried_forward = ""
    if resume_dir is not None and (resume_dir / "records.jsonl").is_file():
        carried_forward = (resume_dir / "records.jsonl").read_text(encoding="utf-8")

    model_spec = spec["models"][args.role]
    device = "cuda"
    # T2 may pin its own precision: its consistency guard compares a cached
    # continuation with an uncached forward, and fp16 kernels disagreed by
    # 0.1358 nats on base (2026-09-27); fp32 keeps the guard strict (0.001).
    dtype = (spec.get("t2_dtype") if args.test == "t2" else None) or spec["dtype_preferred"]
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

    setup_seconds = time.perf_counter() - load_started  # dataset + model load, before any item
    gen_kwargs = generation_record = None
    if args.test == "t1":  # T2 teacher-forces and never generates
        gen_kwargs = generation_kwargs(spec["generation"], int(spec["max_new_tokens"]))
        generation_record = {"requested": gen_kwargs,
                             **describe_resolved(runtime.resolved_generation(model, gen_kwargs))}

    failures = []
    records_path = out_dir / "records.jsonl"
    with io.open(records_path, "w", encoding="utf-8", newline="\n") as handle:
        if carried_forward:
            handle.write(carried_forward)
            handle.flush()
        for index in selected:
            row = dataset[index]
            if args.test == "t2" and row["Id"] in completed:
                continue
            if args.test == "t1" and all((row["Id"], p) in completed for p in spec["t1_prompts"]):
                continue
            original = row["image"].convert("RGB")
            image = runtime.resize_policy(original)
            base = {
                "id": row["Id"], "task": row["Task"], "category": row["category"],
                "reference": row["answer"],
                "source_size": list(original.size), "resized_size": list(image.size),
            }
            if args.test == "t1":
                for prompt_kind in spec["t1_prompts"]:
                    if (row["Id"], prompt_kind) in completed:
                        continue
                    prompt = typhoon_prompt if prompt_kind == "TYPHOON_CARD" else row["question"]
                    try:
                        result = runtime.generate(model, processor, image, prompt,
                                                  generation=gen_kwargs, device=device)
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
                item_started = time.perf_counter()
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
                                         "sites": scored,
                                         "seconds": time.perf_counter() - item_started},
                                        ensure_ascii=False) + "\n")
                handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": args.test, "role": args.role,
            "model_id": model_spec["model_id"], "revision": model_spec["revision"],
            "dtype_used": dtype, "items": len(selected), "failures": failures,
            "setup_seconds": setup_seconds,
            "generation": generation_record,
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda_device": torch.cuda.get_device_name(0), "platform": platform.platform(),
            "git_sha": spec["git_sha"], "run_id": spec["run_id"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
