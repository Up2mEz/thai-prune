"""Phase-1 FULL-only capability smoke for the region-OCR branch.

Engineering evidence only. It answers one question before any pruning machinery
is built: can the pinned models read Thai text regions at all, and is the visual
token accounting observable, self-consistent, and reproducible?

No compression of any kind is applied. Nothing here may be used as a scientific
criterion — not the CER, not the transcriptions — per
docs/stage0/REGION_OCR_TOKEN_PRUNING_PROTOCOL.md. The run fails closed on any
integrity violation rather than recording a warning and continuing.
"""

from __future__ import annotations

import argparse
import io
import json
import time
import unicodedata
from pathlib import Path
from typing import Any

from labbs2026.region_ocr.text_metrics import cer_summary, region_cer

PROMPT = "OCR:"
REPLACEMENT_CHAR = "�"


def _load_model(model_id: str, revision: str, device: str, dtype_name: str):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    # trust_remote_code=False on purpose, matching paddle_wayu_locked_panel.py.
    # `paddleocr_vl` is native from transformers 5.x and the native implementation is
    # what the recorded experiments ran against. The remote code shipped in the HF repo
    # targets a different transformers generation and fails on both 4.57 and 5.x, so
    # enabling it would silently diverge from the project's own evidence.
    dtype = {"float32": torch.float32, "float16": torch.float16}[dtype_name]
    processor = AutoProcessor.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        revision=revision,
        trust_remote_code=False,
        dtype=dtype,
        attn_implementation="sdpa",
    )
    return processor, model.to(device).eval()


def _accounting(inputs: Any, model: Any, expected: int) -> dict[str, Any]:
    """Visual-token accounting, cross-checked three ways and against the frozen manifest.

    Fails closed: a placeholder count that disagrees with the frozen selection means
    the stimulus the model saw is not the stimulus that was registered.
    """
    grid = [int(v) for v in inputs["image_grid_thw"][0].tolist()]
    merge = int(model.config.vision_config.spatial_merge_size)
    pre_merge = grid[0] * grid[1] * grid[2]
    from_grid = grid[0] * (grid[1] // merge) * (grid[2] // merge)
    placeholders = int((inputs["input_ids"] == int(model.config.image_token_id)).sum().item())
    if from_grid != placeholders:
        raise RuntimeError(
            f"visual-token accounting mismatch: grid={from_grid} placeholders={placeholders}"
        )
    if placeholders != expected:
        raise RuntimeError(
            f"placeholders {placeholders} disagree with frozen manifest {expected}"
        )
    return {
        "image_grid_thw": grid,
        "spatial_merge_size": merge,
        "pre_merge": pre_merge,
        "llm_placeholders": placeholders,
    }


def _generate(model, processor, inputs, prompt_ids, max_new_tokens: int) -> dict[str, Any]:
    """One deterministic pass, with the prompt boundary verified rather than assumed."""
    import torch

    prompt_len = int(prompt_ids.shape[-1])
    start = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            **inputs, do_sample=False, num_beams=1, max_new_tokens=max_new_tokens
        )
    latency = time.perf_counter() - start

    sequence = generated[0]
    prefix = sequence[:prompt_len].detach().cpu()
    if not torch.equal(prefix, prompt_ids[0].detach().cpu()):
        raise RuntimeError("generated prefix does not match the prompt; output slicing is unsafe")

    new_tokens = sequence[prompt_len:]
    raw = processor.decode(new_tokens, skip_special_tokens=True)
    return {
        "raw_output": raw,
        "token_ids": [int(t) for t in new_tokens.detach().cpu().tolist()],
        "generated_tokens": int(new_tokens.shape[-1]),
        "latency_seconds": latency,
    }


def run(
    selection_path: Path,
    images_dir: Path,
    model_id: str,
    revision: str,
    *,
    device: str,
    dtype_name: str,
    max_new_tokens: int,
) -> dict[str, Any]:
    from PIL import Image

    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    entries = selection["regions"]
    ids = [e["image_id"] for e in entries]
    if len(set(ids)) != len(ids):
        raise RuntimeError("frozen selection contains duplicate image_id values")

    load_start = time.perf_counter()
    processor, model = _load_model(model_id, revision, device, dtype_name)
    load_seconds = time.perf_counter() - load_start

    records: list[dict[str, Any]] = []
    violations: list[str] = []

    for entry in entries:
        path = images_dir / f"{entry['image_id']}.jpg"
        with Image.open(path) as opened:
            opened.load()
            image = opened.convert("RGB").copy()
        if image.size != (entry["image_width"], entry["image_height"]):
            raise RuntimeError(f"{entry['image_id']}: image geometry disagrees with manifest")

        messages = [
            {
                "role": "user",
                "content": [{"type": "image", "image": image}, {"type": "text", "text": PROMPT}],
            }
        ]
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        accounting = _accounting(inputs, model, int(entry["placeholders"]))
        prompt_ids = inputs["input_ids"]
        moved = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in inputs.items()}

        first = _generate(model, processor, moved, prompt_ids, max_new_tokens)
        second = _generate(model, processor, moved, prompt_ids, max_new_tokens)
        repeat_agrees = (
            first["token_ids"] == second["token_ids"]
            and first["raw_output"] == second["raw_output"]
        )
        if not repeat_agrees:
            violations.append(f"{entry['image_id']}: deterministic rerun disagreed")

        raw = first["raw_output"]
        parsed = raw.strip()
        if REPLACEMENT_CHAR in raw:
            violations.append(f"{entry['image_id']}: U+FFFD in decoded output")

        reference = entry["label"]
        reached_cap = first["generated_tokens"] >= max_new_tokens

        records.append(
            {
                "image_id": entry["image_id"],
                "source_photo_id": entry["source_photo_id"],
                "reference": reference,
                "raw_output": raw,
                "parsed_output": parsed,
                "cer": region_cer(reference, parsed),
                "generated_tokens": first["generated_tokens"],
                "reached_max_new_tokens": reached_cap,
                "termination_reason": "MAX_NEW_TOKENS" if reached_cap else "STOPPED",
                "repeat_agreement": repeat_agrees,
                "u_fffd_present": REPLACEMENT_CHAR in raw,
                "nfc_changes_output": unicodedata.normalize("NFC", parsed) != parsed,
                "nfc_changes_reference": unicodedata.normalize("NFC", reference) != reference,
                "latency_seconds": first["latency_seconds"],
                **accounting,
                "expected_placeholders": int(entry["placeholders"]),
            }
        )

    if len(records) != len(entries):
        raise RuntimeError(f"expected {len(entries)} records, produced {len(records)}")
    if {r["image_id"] for r in records} != set(ids):
        raise RuntimeError("record image_id set does not match the frozen selection")
    if violations:
        raise RuntimeError("smoke integrity violations: " + "; ".join(violations))

    pairs = [(r["reference"], r["parsed_output"]) for r in records]
    placeholders = [r["llm_placeholders"] for r in records]
    latencies = sorted(r["latency_seconds"] for r in records)
    return {
        "status": "ENGINEERING_SMOKE_ONLY_EXCLUDED_FROM_SCIENTIFIC_SUMMARIES",
        "scientific_use": "FORBIDDEN_CER_AND_TRANSCRIPTIONS_ARE_NOT_A_DECISION_CRITERION",
        "compression_applied": "NONE_FULL_INFORMATION_ONLY",
        "model_id": model_id,
        "revision": revision,
        "device": device,
        "dtype": dtype_name,
        "model_class": type(model).__name__,
        "loading_path": "AutoModelForImageTextToText native, trust_remote_code=False",
        "transformers_version": __import__("transformers").__version__,
        "environment_note": (
            "Run in an ephemeral environment with transformers 5.12.0; the repository's "
            "pinned environment was not modified for this smoke."
        ),
        "prompt": PROMPT,
        "max_new_tokens": max_new_tokens,
        "model_load_seconds": load_seconds,
        "region_count": len(records),
        "photo_count": len({r["source_photo_id"] for r in records}),
        "integrity": {
            "records_complete": True,
            "duplicate_image_ids": False,
            "prompt_boundary_verified": True,
            "placeholders_match_frozen_manifest": True,
            "repeat_agreement": True,
            "u_fffd_present": False,
        },
        "cer": cer_summary(pairs),
        "placeholders": {
            "min": min(placeholders),
            "median": sorted(placeholders)[len(placeholders) // 2],
            "max": max(placeholders),
        },
        "latency_seconds": {
            "min": latencies[0],
            "median": latencies[len(latencies) // 2],
            "max": latencies[-1],
            "total": sum(latencies),
        },
        "truncation": {
            "reached_max_new_tokens": sum(1 for r in records if r["reached_max_new_tokens"]),
            "empty_output": sum(1 for r in records if not r["parsed_output"]),
        },
        "nfc_sensitivity": {
            "outputs_changed_by_nfc": sum(1 for r in records if r["nfc_changes_output"]),
            "references_changed_by_nfc": sum(1 for r in records if r["nfc_changes_reference"]),
        },
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", default="float32", choices=("float32", "float16"))
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite {args.out}")

    report = run(
        args.selection,
        args.images,
        args.model_id,
        args.revision,
        device=args.device,
        dtype_name=args.dtype,
        max_new_tokens=args.max_new_tokens,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)

    cer = report["cer"]
    print(f"regions={report['region_count']} photos={report['photo_count']}")
    print(f"integrity: {report['integrity']}")
    print(f"macro CER={cer['macro_cer']:.4f}  micro CER={cer['micro_cer']:.4f}  (engineering only)")
    print(f"empty={report['truncation']['empty_output']} truncated={report['truncation']['reached_max_new_tokens']}")
    print(f"placeholders min/median/max={report['placeholders']}")
    print(f"median latency={report['latency_seconds']['median']:.2f}s")


if __name__ == "__main__":
    main()
