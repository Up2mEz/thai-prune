"""Thin CLI for immutable Checkpoint D analysis-only artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.checkpoint_d import write_checkpoint_d_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/stage0/calibration_only_diagnostics.yaml"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    manifest = write_checkpoint_d_artifacts(
        root, args.config.resolve(), args.output_dir.resolve()
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
