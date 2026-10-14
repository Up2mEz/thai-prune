"""Remote entry point for W4's live decode-time stop check (calibration items only) on Kaggle.

W4 condition 3 replayed the stop on recorded text (`W4_STOP_CHECK_ed02ad0.json`).
This unit generates again, with `stop.LoopStoppingCriteria` attached to
`generate()`, for one model and prompt at a time:

- every calibration output the offline cut (`loop_cut.variant_b`) changes, and
- a seeded sample of outputs it leaves unchanged,

chosen by `stop.live_items` from the calibration outputs archive in the
repository. Each item is generated as in its calibration run (same model,
revision, prompt, image policy, greedy settings and dtype), except that
generation stops at a loop. The record keeps the generated text and the
stopped output; the comparison with the offline cut is made locally. No
reference text and no image is written. Locked items are never read.

Roles with `runner: m6b` (DeepSeek-OCR-2) are generated as
`model_survey.remote_m6b` generates them, in its venv (bootstrap stage).
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

MODULE = "labbs2026.model_survey.remote_live_stop"


def _items(spec: dict, role: str) -> dict[str, list[dict]]:
    from labbs2026.model_survey.stop import live_items

    live = spec["live_stop"]
    model = spec["models"][role]
    archive = Path(spec["source_dir"]) / "docs/stage0/data" / f"{model['calibration_archive']}.json.gz"
    rows = json.loads(gzip.open(archive, "rt", encoding="utf-8").read())["records"][role]
    return {kind: live_items([r for r in rows if r["prompt_kind"] == kind],
                             int(live["sample_non_looping"]), int(live["sample_seed"]))
            for kind in model["prompts"]}


def bootstrap(args: argparse.Namespace, spec: dict) -> None:
    """A fresh venv with M6b's requirements, then this module's run stage there (as remote_m6b)."""
    from labbs2026.model_survey.remote_m6b import REQUIREMENTS

    source = Path(spec["source_dir"])
    venv = Path(f"/tmp/live-venv-{args.role}-{args.shard}")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv not found; the worker installs it before any unit runs")
    subprocess.run([uv, "venv", "--python", f"{sys.version_info.major}.{sys.version_info.minor}",
                    str(venv)], check=True)
    python = venv / "bin" / "python"
    subprocess.run([uv, "pip", "install", "--python", str(python), "-r", str(source / REQUIREMENTS)],
                   check=True)
    env = dict(os.environ, PYTHONPATH=str(source / "src"))
    subprocess.run([str(python), "-m", MODULE, "--stage", "run", "--remote-spec", str(args.remote_spec),
                    "--role", args.role, "--shard", str(args.shard), "--shards", str(args.shards)],
                   cwd=source, env=env, check=True)


def _prompts(role: dict, spec: dict) -> dict:
    """The registered prompt texts, with the role's own where it has one (DeepSeek's card prompt)."""
    return {**spec["prompts"], **role.get("prompt_overrides", {})}


def _hf(role: dict, spec: dict, torch):
    """Load, encode and probe as `model_survey.remote` does; decode its record text the same way."""
    from labbs2026.model_survey.plan import resolve_prompt
    from labbs2026.model_survey.remote import logits_are_finite
    from labbs2026.thai_marks import runtime

    def load(dtype):
        return (*runtime.load(role["model_id"], role["revision"], dtype, "cuda"), dtype)

    def encode(model, processor, image, kind, question):
        return runtime.prompt_inputs(processor, image, resolve_prompt(kind, question, _prompts(role, spec)), "cuda")

    def probe(model, processor, image, kind, question):
        prompt = resolve_prompt(kind, question, _prompts(role, spec))
        return logits_are_finite(model, processor, image, prompt, "cuda", runtime, torch)

    return load, encode, probe, lambda processor: (
        lambda ids: processor.decode(list(ids), skip_special_tokens=True))


def _m6b(role: dict, spec: dict, torch):
    """Load and encode as `model_survey.remote_m6b` does; decode its record text the same way."""
    from transformers import AutoModel, AutoTokenizer

    from labbs2026.model_survey.remote_m6b import STOP, content_for, prepare_inputs

    def load(dtype_name):
        dtype = {"float16": torch.float16, "float32": torch.float32}[dtype_name]
        tokenizer = AutoTokenizer.from_pretrained(role["model_id"], revision=role["revision"],
                                                  trust_remote_code=True)
        model = AutoModel.from_pretrained(role["model_id"], revision=role["revision"],
                                          trust_remote_code=True, use_safetensors=True,
                                          _attn_implementation="eager")
        return model.eval().cuda().to(dtype), tokenizer, dtype_name

    def encode(model, tokenizer, image, kind, question):
        remote = sys.modules[type(model).__module__]
        dtype = next(model.parameters()).dtype
        inputs = prepare_inputs(remote, tokenizer, image, content_for(kind, question, _prompts(role, spec)),
                                dtype, torch)
        inputs.pop("visual_tokens")
        return inputs

    def probe(model, tokenizer, image, kind, question):
        with torch.inference_mode():
            logits = model(**encode(model, tokenizer, image, kind, question)).logits[:, -1]
        return bool(torch.isfinite(logits).all().item())

    def decoder(tokenizer):
        def decode(ids):
            text = tokenizer.decode(list(ids), skip_special_tokens=False)
            if text.endswith(STOP):
                text = text[:-len(STOP)]
            return text.strip()
        return decode

    return load, encode, probe, decoder


def run(args: argparse.Namespace, spec: dict) -> None:
    import torch
    import transformers
    from transformers import StoppingCriteriaList

    from labbs2026.model_survey.stop import K, K_LONG, LoopStoppingCriteria, stopped_output
    from labbs2026.thai_marks import runtime
    from labbs2026.thai_marks.generation import generation_kwargs
    from labbs2026.thai_marks.remote import load_items, shard_items

    role = spec["models"][args.role]
    m6b = role.get("runner") == "m6b"
    out_dir = Path(spec["artifact_dir"]) / "live_stop" / args.role
    if args.shards > 1:
        out_dir = out_dir / f"shard-{args.shard}-of-{args.shards}"
    out_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()

    dataset, ordered, calibration, id_col = load_items(spec)
    index_of = {id_col[i]: i for i in ordered}
    units = [(kind, item) for kind, items in _items(spec, args.role).items() for item in items]
    if any(u["id"] not in calibration for _, u in units):
        raise RuntimeError("a live-check item is not a calibration item")
    if int(spec.get("limit") or 0):
        units = units[:int(spec["limit"])]
    units = shard_items(units, args.shard, args.shards)

    load, encode, probe, decoder = (_m6b if m6b else _hf)(role, spec, torch)
    first_kind, first_item = units[0]
    first = dataset[index_of[first_item["id"]]]
    probe_image = runtime.resize_policy(first["image"].convert("RGB"))
    dtype_name = spec["dtype_preferred"]
    model, processor, dtype_name = load(dtype_name)
    if not probe(model, processor, probe_image, first_kind, first["question"]):
        del model
        torch.cuda.empty_cache()
        dtype_name = spec["dtype_fallback"]
        model, processor, dtype_name = load(dtype_name)
        if not probe(model, processor, probe_image, first_kind, first["question"]):
            raise RuntimeError("non-finite logits in both fp16 and fp32")
    decode = decoder(processor)
    max_new_tokens = int(spec["max_new_tokens"])
    gen_kwargs = {**generation_kwargs(spec["generation"], max_new_tokens), "use_cache": bool(spec["use_cache"])}
    if m6b:
        gen_kwargs["eos_token_id"] = processor.eos_token_id
    stride = int(spec["live_stop"]["stride"])
    setup_seconds = time.perf_counter() - started

    deadline = float(role["unit_deadline_hours"]) * 3600
    failures: list[dict] = []
    not_run: list[str] = []
    attempted = 0
    with io.open(out_dir / "records.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for position, (kind, item) in enumerate(units):
            if time.perf_counter() - started > deadline:
                not_run = [f"{u['id']}|{k}" for k, u in units[position:]]
                break
            attempted += 1
            row = dataset[index_of[item["id"]]]
            image = runtime.resize_policy(row["image"].convert("RGB"))
            try:
                inputs = encode(model, processor, image, kind, row["question"])
                prompt_length = int(inputs["input_ids"].shape[-1])
                criterion = LoopStoppingCriteria(None, prompt_length, K, K_LONG, stride=stride, decode=decode)
                torch.cuda.synchronize()
                t0 = time.perf_counter()
                with torch.inference_mode():
                    produced = model.generate(**inputs, **gen_kwargs,
                                              stopping_criteria=StoppingCriteriaList([criterion]))
                torch.cuda.synchronize()
                t1 = time.perf_counter()
            except Exception as exc:  # recorded, never compared
                failures.append({"id": item["id"], "prompt": kind, "error": f"{type(exc).__name__}: {exc}"[:800]})
                torch.cuda.empty_cache()
                continue
            new = produced[0][prompt_length:].tolist()
            stopped = stopped_output(new, decode)
            handle.write(json.dumps({
                "id": item["id"], "task": row["Task"], "prompt_kind": kind,
                "looping_offline": item["looping_offline"],
                "generated_tokens": len(new), "reached_max_new_tokens": len(new) >= max_new_tokens,
                "fired_during_generation": criterion.stopped_at is not None,
                "fired_at": criterion.stopped_at, "first_stop": stopped["first_stop"],
                "live_text": decode(new), "stopped_text": stopped["text"],
                "seconds_generate": t1 - t0, "seconds_per_generated_token": (t1 - t0) / max(1, len(new)),
            }, ensure_ascii=False) + "\n")
            handle.flush()

    with io.open(out_dir / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump({
            "test": "w4_live_stop", "runner": "m6b" if m6b else "remote", "role": args.role,
            "shard": args.shard, "shards": args.shards, "model_id": role["model_id"],
            "revision": role["revision"], "prompts": role["prompts"], "dtype_used": dtype_name,
            "calibration_archive": role["calibration_archive"], "live_stop": spec["live_stop"],
            "rule": {"k": K, "k_long": K_LONG}, "items": attempted, "selected_items": len(units),
            "deadline_seconds": deadline, "not_run": not_run, "failures": failures,
            "setup_seconds": setup_seconds, "generation": {"requested": gen_kwargs},
            "wall_seconds": time.perf_counter() - started,
            "torch": torch.__version__, "transformers": transformers.__version__,
            "cuda": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0),
            "platform": platform.platform(), "git_sha": spec["git_sha"], "run_id": spec["run_id"],
            "config_sha256": spec["expected_file_hashes"][spec["config_path"]],
        }, handle, ensure_ascii=False, indent=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--stage", choices=("bootstrap", "run"), default=None)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        raise SystemExit("--shard must be in [0, --shards)")
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))
    m6b = spec["models"][args.role].get("runner") == "m6b"
    stage = args.stage or ("bootstrap" if m6b else "run")
    (bootstrap if stage == "bootstrap" else run)(args, spec)


if __name__ == "__main__":
    main()
