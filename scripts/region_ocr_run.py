"""Driver for a region-OCR run. Used locally for grid smokes and by the Kaggle worker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--ratios", default="0.75,0.5,0.25")
    parser.add_argument("--random-seeds", default="20260920,20260921")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", default="float32", choices=("float32", "float16"))
    parser.add_argument("--limit-regions", type=int, default=0,
                        help="engineering smoke only; 0 runs the full selection")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from labbs2026.region_ocr.run import run

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    regions = selection["regions"]
    if args.limit_regions:
        regions = regions[: args.limit_regions]

    dtype = {"float32": torch.float32, "float16": torch.float16}[args.dtype]
    processor = AutoProcessor.from_pretrained(
        args.model_id, revision=args.revision, trust_remote_code=False
    )
    model = AutoModelForImageTextToText.from_pretrained(
        args.model_id, revision=args.revision, trust_remote_code=False,
        dtype=dtype, attn_implementation="sdpa",
    ).to(args.device).eval()

    manifest = run(
        regions=regions,
        images_dir=args.images,
        model=model,
        processor=processor,
        ratios=[float(r) for r in args.ratios.split(",")],
        random_seeds=[int(s) for s in args.random_seeds.split(",")],
        max_new_tokens=args.max_new_tokens,
        device=args.device,
        artifact_dir=args.artifacts,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
