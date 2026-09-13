"""CLI for fail-closed Kaggle SaveKernel request diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.kaggle_savekernel_diagnostic import (
    capture_request,
    submit_once_with_failure_capture,
    write_json_exclusive,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--submit-once",
        action="store_true",
        help="Perform one authorized SaveKernel call and capture any HTTP error.",
    )
    args = parser.parse_args()
    if args.submit_once:
        if len(args.folders) != 1:
            parser.error("--submit-once requires exactly one folder")
        submit_once_with_failure_capture(args.folders[0], args.output)
        return 0
    payload = {
        "schema_version": 1,
        "diagnostic_scope": "LOCAL_SAVEKERNEL_REQUEST_CONSTRUCTION_NO_NETWORK",
        "requests": [capture_request(folder) for folder in args.folders],
    }
    write_json_exclusive(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
