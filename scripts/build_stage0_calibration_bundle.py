"""Thin CLI for the frozen, calibration-only Stage 0 input bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.bundle import build_calibration_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/stage0/calibration_design.yaml")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("assets/stage0/calibration_input.zip")
    )
    args = parser.parse_args()
    result = build_calibration_bundle(
        args.review_dir.resolve(), args.config.resolve(), args.output.resolve()
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
