"""Thin CLI for an explicitly human-frozen Stage 0 calibration run."""

from __future__ import annotations

import argparse
from pathlib import Path

from labbs2026.stage0.run import run_calibration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-review-dir", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/stage0/calibration_design.yaml")
    )
    parser.add_argument(
        "--model-config", type=Path, default=Path("configs/step3/qwen25_vl_3b.yaml")
    )
    args = parser.parse_args()
    run_dir = run_calibration(
        args.config.resolve(),
        args.dataset_review_dir.resolve(),
        args.model_config.resolve(),
    )
    print(f"run_dir={run_dir}")
    print("run_status=VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
