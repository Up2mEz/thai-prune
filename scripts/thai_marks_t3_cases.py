"""Build T3 cases from a fetched T1 run and write them, with provenance."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.line_skip import build_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="fetched t1/typhoon/records.jsonl")
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; cases are never overwritten")

    records = [json.loads(line) for line in args.t1_records.open(encoding="utf-8") if line.strip()]
    cases = build_cases(records)
    counts = collections.Counter((c["prompt_kind"], c["kind"]) for c in cases)
    payload = {
        "schema_version": 1,
        "source_run": args.source_run,
        "source_records_sha256": hashlib.sha256(args.t1_records.read_bytes()).hexdigest(),
        "built_at_git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                           text=True, check=True).stdout.strip(),
        "counts": {f"{p}/{k}": n for (p, k), n in sorted(counts.items())},
        "cases": cases,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload["counts"], indent=1))
    print(f"{len(cases)} cases written to {args.out}")


if __name__ == "__main__":
    main()
