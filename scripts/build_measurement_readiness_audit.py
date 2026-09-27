"""Build the S0-only measurement-readiness design-analysis artifact."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from labbs2026.stage0.measurement_readiness import write_audit

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = write_audit(args.artifact_dir.resolve(), args.output.resolve())
    print(json.dumps({"output": str(args.output.resolve()), "source_run_id": result["source_run_id"]}, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
