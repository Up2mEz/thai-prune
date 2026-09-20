"""Remote entry point invoked by the Kaggle worker.

Reads the frozen run spec, reselects the regions deterministically from the
mounted corpus, loads the pinned model, and runs the registered condition grid.
Selection is recomputed here from the recorded seed rather than shipped as a
list, so the run provably uses the registered rule and cannot be handed a
hand-edited sample.
"""

from __future__ import annotations

import argparse
import io
import json
import platform
from pathlib import Path

from labbs2026.region_ocr.dataset import (
    assert_split_disjoint_by_photo,
    load_tems_metadata,
    select_smoke_sample,
    selection_manifest,
)
from labbs2026.region_ocr.run import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-spec", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.remote_spec.read_text(encoding="utf-8"))

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    artifact_dir = Path(spec["artifact_dir"])
    rows = load_tems_metadata(Path(spec["resolved_metadata_csv"]))
    assert_split_disjoint_by_photo(rows)

    selection = select_smoke_sample(
        rows,
        seed=int(spec["selection_seed"]),
        photos=int(spec["selection_photos"]),
        crops_per_photo=int(spec["selection_crops_per_photo"]),
        splits=tuple(spec["selection_splits"]),
    )
    manifest = selection_manifest(
        selection, seed=int(spec["selection_seed"]), splits=tuple(spec["selection_splits"])
    )
    with io.open(artifact_dir / "selection.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)

    dtype = {"float16": torch.float16, "float32": torch.float32}[spec["model_dtype"]]
    processor = AutoProcessor.from_pretrained(
        spec["model_id"], revision=spec["model_revision"], trust_remote_code=False
    )
    model = AutoModelForImageTextToText.from_pretrained(
        spec["model_id"], revision=spec["model_revision"], trust_remote_code=False,
        dtype=dtype, attn_implementation=spec["attention_implementation"],
    ).to(spec["device"]).eval()

    result = run(
        regions=selection,
        images_dir=Path(spec["resolved_images_dir"]),
        model=model,
        processor=processor,
        ratios=[float(r) for r in spec["ratios"]],
        random_seeds=[int(s) for s in spec["random_seeds"]],
        max_new_tokens=int(spec["max_new_tokens"]),
        device=spec["device"],
        artifact_dir=artifact_dir,
    )
    result["run_id"] = spec["run_id"]
    result["git_sha"] = spec["git_sha"]
    result["torch"] = torch.__version__
    result["cuda_device"] = (
        torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    )
    result["peak_cuda_allocated_bytes"] = (
        int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
    )
    result["platform"] = platform.platform()
    with io.open(artifact_dir / "run_manifest.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: v for k, v in result.items() if k != "workload"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
