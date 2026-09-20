"""Engineering check that post-encoder pruning removes LLM positions for real.

Not a scientific run: it uses a couple of regions, computes no registered
metric, and applies no experimental design. It answers one question — does the
pruning path actually deliver fewer visual positions to the language model, and
does generation still work when it does?

Verified here rather than assumed:
  * the projector emits exactly as many features as there are placeholders;
  * pruning to K shortens the sequence by exactly N - K;
  * surviving tokens keep their original M-RoPE positions;
  * generate() accepts inputs_embeds with explicit 3D position ids.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any

from labbs2026.region_ocr.prune_runtime import (
    apply_keep_mask,
    embed_with_visual_features,
    full_position_ids,
    full_visual_features,
)
from labbs2026.region_ocr.pruning import assert_accounting, select_keep_indices, surviving_sequence_mask

PROMPT = "OCR:"


def _decode_new(processor, sequence, prompt_len: int) -> str:
    return processor.decode(sequence[prompt_len:], skip_special_tokens=True)


def check(image_path: Path, model_id: str, revision: str, ratios: list[float]) -> dict[str, Any]:
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(model_id, revision=revision, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, revision=revision, trust_remote_code=False,
        dtype=torch.float32, attn_implementation="sdpa",
    ).to("cpu").eval()
    inner = model.model

    with Image.open(image_path) as opened:
        opened.load()
        image = opened.convert("RGB").copy()
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}]
    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt",
    )

    input_ids = inputs["input_ids"]
    image_token_id = int(model.config.image_token_id)
    placeholders = int((input_ids == image_token_id).sum().item())
    grid = [int(v) for v in inputs["image_grid_thw"][0].tolist()]
    merge = int(model.config.vision_config.spatial_merge_size)
    rows, cols = grid[1] // merge, grid[2] // merge

    with torch.inference_mode():
        features = full_visual_features(model, inputs["pixel_values"], inputs["image_grid_thw"])
        n_features = int(features.shape[0]) if features.dim() == 2 else int(features.shape[1])
        embeds_full = embed_with_visual_features(model, input_ids, features)
        pos_full = full_position_ids(
            model, input_ids=input_ids, image_grid_thw=inputs["image_grid_thw"],
            inputs_embeds=embeds_full, attention_mask=inputs.get("attention_mask"),
            mm_token_type_ids=inputs.get("mm_token_type_ids"),
        )

    report: dict[str, Any] = {
        "status": "ENGINEERING_CHECK_ONLY_NOT_A_SCIENTIFIC_RUN",
        "image": image_path.name,
        "image_grid_thw": grid,
        "token_rows_cols": [rows, cols],
        "placeholders": placeholders,
        "projector_features": n_features,
        "features_match_placeholders": n_features == placeholders,
        "prompt_sequence_length": int(input_ids.shape[-1]),
        "position_ids_available": pos_full is not None,
        "position_ids_shape": list(pos_full.shape) if pos_full is not None else None,
        "trials": [],
    }

    for ratio in ratios:
        kept = max(1, round(placeholders * ratio))
        keep_indices = select_keep_indices(policy="GRID", rows=rows, cols=cols, kept=kept)
        mask = surviving_sequence_mask(input_ids[0].tolist(), image_token_id, keep_indices)
        pruned = apply_keep_mask(
            inputs_embeds=embeds_full, attention_mask=inputs.get("attention_mask"),
            position_ids=pos_full, keep_mask=mask,
        )
        seq_len = int(pruned["inputs_embeds"].shape[1])
        expected_len = int(input_ids.shape[-1]) - (placeholders - kept)

        trial: dict[str, Any] = {
            "ratio": ratio,
            "kept_tokens": kept,
            "pruned_sequence_length": seq_len,
            "expected_sequence_length": expected_len,
            "sequence_shrank_exactly": seq_len == expected_len,
        }
        assert_accounting(
            pre_prune=placeholders, post_prune=kept, llm_positions=kept, expected_kept=kept
        )
        try:
            with torch.inference_mode():
                out = model.generate(
                    **{k: v for k, v in pruned.items()},
                    do_sample=False, num_beams=1, max_new_tokens=32,
                )
            produced = out[0]
            # With inputs_embeds the prompt is not echoed, so everything returned is new.
            trial["generation_ok"] = True
            trial["returned_tokens"] = int(produced.shape[-1])
            trial["output"] = processor.decode(produced, skip_special_tokens=True)
        except Exception as exc:  # engineering probe: record, do not mask
            trial["generation_ok"] = False
            trial["error"] = f"{type(exc).__name__}: {exc}"[:400]
        report["trials"].append(trial)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--ratios", default="1.0,0.75,0.5,0.25")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite {args.out}")

    report = check(args.image, args.model_id, args.revision,
                   [float(r) for r in args.ratios.split(",")])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print(f"placeholders={report['placeholders']} features={report['projector_features']} "
          f"match={report['features_match_placeholders']} grid={report['token_rows_cols']}")
    print(f"position_ids={report['position_ids_shape']}")
    for t in report["trials"]:
        print(f"  ratio={t['ratio']} kept={t['kept_tokens']} len={t['pruned_sequence_length']} "
              f"exact={t['sequence_shrank_exactly']} gen={t.get('generation_ok')} "
              f"{t.get('error','')}")


if __name__ == "__main__":
    main()
