"""Thin CLI for immutable Checkpoint C evidence generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.checkpoint_c import build_checkpoint_c_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite report: {args.output}")
    report = build_checkpoint_c_evidence(args.artifact_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"report={args.output.resolve()}")
    print(f"output_contract_status={report['output_contract_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
