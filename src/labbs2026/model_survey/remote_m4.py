"""Remote entry point for one MODEL_SURVEY_M4 unit on Kaggle: teacher-forced scores of M3's outputs, one shard.

For each item, M3's `E` output (from the committed archive) is re-tokenized
and scored in one forward pass over prompt + image + output: per token its
log-probability, the entropy of the distribution, and whether it is the
argmax. No generation. Records hold the reference (for labels offline), the
token offsets and the scores; no image is written.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import platform
import time
from pathlib import Path

from labbs2026.model_survey.plan import resolve_prompt
from labbs2026.model_survey.remote import logits_are_finite


def teacher_forced(model, inputs: dict, ids: list[int], chunk: int, torch) -> dict[str, list]:
    """Per-token log-probability, entropy and argmax agreement for `ids` after the prompt `inputs`."""
    from labbs2026.model_survey.escape import extend_inputs

    with torch.inference_mode():
        logits = model(**extend_inputs(inputs, ids), logits_to_keep=len(ids) + 1).logits[0, :-1, :]
    target = torch.tensor(ids, device=logits.device)
    out: dict[str, list] = {"logprob": [], "entropy": [], "agrees": []}
    for start in range(0, len(ids), chunk):
        part = torch.log_softmax(logits[start:start + chunk].float(), dim=-1)
        rows = torch.arange(part.shape[0], device=part.device)
        out["logprob"] += [round(x, 5) for x in part[rows, target[start:start + chunk]].tolist()]
        out["entropy"] += [round(x, 4) for x in (-(part.exp() * part).sum(-1)).tolist()]
        out["agrees"] += (part.argmax(-1) == target[start:start + chunk]).int().tolist()
        del part
    del logits
    return out


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

    import torch
    import transformers

    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.remote import load_items, shard_items

    archive = json.loads(gzip.open(spec["outputs_archive"], "rt", encoding="utf-8").read())
    outputs = {r["id"]: r for r in archive["records"][spec["outputs_arm"]]}
    out_dir = Path(spec["artifact_dir"]) / "m4" / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    selected = [i for i in ordered if id_col[i] in calibration]
    limit = int(spec.get("limit") or 0)
    if limit:
        selected = selected[:limit]
    selected = shard_items(selected, args.shard, args.shards)

    device = "cuda"
    dtype = spec["dtype_preferred"]
    kind = spec["prompt_kind"]
    failures: list[dict] = []
    setup_seconds = None
    if selected:
        model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
        first = dataset[selected[0]]
        probe = runtime.resize_policy(first["image"].convert("RGB"))
        if not logits_are_finite(model, processor, probe, resolve_prompt(kind, first["question"], spec["prompts"]),
                                 device, runtime, torch):
            del model
            torch.cuda.empty_cache()
            dtype = spec["dtype_fallback"]
            model, processor = runtime.load(role["model_id"], role["revision"], dtype, device)
        setup_seconds = time.perf_counter() - started

    attempted: list[str] = []
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for index in selected:
            row = dataset[index]
            attempted.append(row["Id"])
            output = outputs.get(row["Id"])
            if output is None:
                failures.append({"id": row["Id"], "error": "no M3 output for this item"})
                continue
            text = output["raw_output"]
            t0 = time.perf_counter()
            try:
                encoded = processor.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
                ids = list(encoded["input_ids"])
                scores = {"logprob": [], "entropy": [], "agrees": []}
                if ids:
                    image = runtime.resize_policy(row["image"].convert("RGB"))
                    inputs = runtime.prompt_inputs(processor, image, resolve_prompt(kind, row["question"], spec["prompts"]),
                                                   device)
                    scores = teacher_forced(model, inputs, ids, int(spec["chunk"]), torch)
            except Exception as exc:  # recorded, never scored
                failures.append({"id": row["Id"], "error": f"{type(exc).__name__}: {exc}"[:800]})
                torch.cuda.empty_cache()
                continue
            handle.write(json.dumps({
                "id": row["Id"], "task": row["Task"], "category": row["category"], "reference": row["answer"],
                "n_tokens": len(ids), "roundtrip": processor.tokenizer.decode(ids) == text,
                "offsets": [list(o) for o in encoded["offset_mapping"]], **scores,
                "seconds": time.perf_counter() - t0}, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "m4", "shard": args.shard, "shards": args.shards, "model_id": role["model_id"],
            "revision": role["revision"], "prompt_kind": kind, "dtype_used": dtype, "items": len(attempted),
            "selected_items": len(selected), "failures": failures, "setup_seconds": setup_seconds,
            "outputs_archive": spec["outputs_archive"], "outputs_run_id": archive["provenance"]["run_id"],
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"]["configs/model_survey/m4.yaml"],
        }, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
