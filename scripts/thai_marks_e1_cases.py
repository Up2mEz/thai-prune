"""Build E1 cases (Typhoon's own greedy outputs) from a fetched T5 run, with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.confidence import build_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t5-run-dir", type=Path, required=True,
                        help="fetched T5 artifacts/<run_id> directory")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; cases are never overwritten")
    paths = sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
    records = [json.loads(line) for p in paths for line in p.open(encoding="utf-8") if line.strip()]
    cases = build_cases(records)
    payload = {
        "schema_version": 1,
        "source_run": args.t5_run_dir.name,
        "source_records_sha256": {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in paths},
        "built_at_git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                           text=True, check=True).stdout.strip(),
        "cases": cases,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cases)} cases written to {args.out}")


if __name__ == "__main__":
    main()
