"""Thin CLI for no-data validation of the registered analysis image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.kaggle import atomic_write_json
from labbs2026.stage0.locked_panel_environment import IMAGE, validate_image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=IMAGE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = validate_image(root, args.image)
    if args.output:
        atomic_write_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
