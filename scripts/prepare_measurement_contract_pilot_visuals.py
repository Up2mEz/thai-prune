"""Thin CLI for the non-model measurement-contract pilot visual review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.measurement_contract_pilot import build_visual_review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/stage0/qwen35_measurement_contract_pilot.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_visual_review(
        root=root, config_path=args.config, output_dir=args.output
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
