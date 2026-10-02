"""Freeze the P-ZOOM probe's page list from Typhoon's T1 records (offline, no model)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks import p_zoom


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-records", type=Path, required=True,
                        help="Typhoon's T1 records.jsonl (read-only)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    def git(*a: str) -> str:
        return subprocess.run(["git", *a], capture_output=True, text=True,
                              check=True).stdout.strip()

    records = [json.loads(line) for line in args.t1_records.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    pages = p_zoom.select_pages(records)
    payload = {
        "provenance": {
            "git_sha": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
            "t1_records_sha256": hashlib.sha256(args.t1_records.read_bytes()).hexdigest(),
            "task": p_zoom.TASK, "prompt_kind": p_zoom.PROMPT_KIND,
            "control_per_page": p_zoom.CONTROL_PER_PAGE, "control_seed": p_zoom.CONTROL_SEED,
            "note": "line numbers index attribution.reference_lines(reference); no reference text is stored",
        },
        "totals": {"pages": len(pages),
                   "absent_lines": sum(len(p["absent_lines"]) for p in pages),
                   "absent_marks": sum(p["absent_marks"] for p in pages),
                   "control_lines": sum(len(p["control_lines"]) for p in pages)},
        "pages": pages,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(payload["totals"]), hashlib.sha256(args.out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
