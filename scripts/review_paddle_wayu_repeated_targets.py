"""Generate the pre-locked repeated-target review from immutable S0 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.repeated_target_review import build_review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    review = build_review(args.artifact_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
