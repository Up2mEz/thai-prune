"""Write local-only validation evidence for the U+FFFD protocol amendment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.paddle_wayu_u_fffd_protocol_amendment import (
    validate_amendment,
    write_validation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s0-artifact-dir", type=Path, required=True)
    parser.add_argument("--unicode-diagnostic", type=Path, required=True)
    parser.add_argument("--attempt4-zip", type=Path, required=True)
    parser.add_argument("--s0-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_amendment(
        s0_artifact_dir=args.s0_artifact_dir,
        unicode_diagnostic_path=args.unicode_diagnostic,
        attempt4_zip_path=args.attempt4_zip,
        s0_config_path=args.s0_config,
    )
    write_validation(result, args.output)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "classification": result["s0_open_replay"]["classification"],
        "cer_semantics": result["cer_semantics_audit"]["classification"],
        "terminal_state": result["terminal_state"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
