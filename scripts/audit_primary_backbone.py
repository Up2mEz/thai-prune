"""Thin CLI for the Step 3 Qwen2.5-VL feasibility audit."""

from __future__ import annotations

import argparse
from pathlib import Path

from labbs2026.step3 import run_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/step3/qwen25_vl_3b.yaml"),
    )
    parser.add_argument(
        "--inference",
        action="store_true",
        help="Download/load the pinned model and run deterministic generation.",
    )
    args = parser.parse_args()
    run_dir, manifest = run_audit(args.config.resolve(), inference=args.inference)
    print(f"run_dir={run_dir}")
    print(f"run_status={manifest['run_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
