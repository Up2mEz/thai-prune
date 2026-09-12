"""Processor-only geometry probe; never loads model weights or dataset images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from PIL import Image
from transformers import AutoTokenizer
from transformers.models.paddleocr_vl.image_processing_pil_paddleocr_vl import (
    PaddleOCRVLImageProcessorPil,
)
from transformers.models.paddleocr_vl.processing_paddleocr_vl import PaddleOCRVLProcessor


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage0/overall_model_budget_design.yaml"
CANDIDATES = list(range(448, 223, -28))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    source = Image.new("RGB", (448, 448), "white")
    processors = []
    mappings = []
    for model_spec in config["models"]:
        tokenizer = AutoTokenizer.from_pretrained(
            model_spec["model_id"], revision=model_spec["revision"]
        )
        image_processor = PaddleOCRVLImageProcessorPil.from_pretrained(
            model_spec["model_id"], revision=model_spec["revision"]
        )
        processor = PaddleOCRVLProcessor(image_processor, tokenizer)
        processors.append(
            {
                **model_spec,
                "patch_size": image_processor.patch_size,
                "merge_size": image_processor.merge_size,
                "image_token_id": tokenizer.image_token_id,
            }
        )
        role_rows = []
        for resolution in CANDIDATES:
            encoded = processor(
                images=source,
                text=tokenizer.image_token,
                min_pixels=resolution**2,
                max_pixels=resolution**2,
                return_tensors="np",
            )
            grid = encoded["image_grid_thw"][0].tolist()
            placeholders = sum(
                int(value) == tokenizer.image_token_id
                for value in encoded["input_ids"][0]
            )
            role_rows.append(
                {
                    "input_dimensions": [resolution, resolution],
                    "image_grid_thw": grid,
                    "pre_merge_patch_count": int(grid[0] * grid[1] * grid[2]),
                    "actual_llm_image_placeholders": placeholders,
                }
            )
        mappings.append({"role": model_spec["role"], "rows": role_rows})
    result = {
        "schema_version": 1,
        "status": "PROCESSOR_ONLY_NO_MODEL_INFERENCE",
        "source_image": "synthetic blank RGB 448x448",
        "model_weights_loaded": False,
        "locked_validation_access": False,
        "processors": processors,
        "mappings_by_role": mappings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"output": str(args.output), "roles": len(processors)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
