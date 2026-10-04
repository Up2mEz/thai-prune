"""Freeze the P-BAND page list: Full-page OCR calibration items not already in P-ZOOM's 21 pages.

Offline, no model. Ids come from Typhoon's T1 records (which hold every calibration item); only
ids are stored, no reference text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-records", type=Path, required=True)
    parser.add_argument("--pzoom-pages", type=Path, default=Path("configs/thai_marks/p_zoom_pages.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    def git(*a: str) -> str:
        return subprocess.run(["git", *a], capture_output=True, text=True,
                              check=True).stdout.strip()

    records = [json.loads(line) for line in args.t1_records.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    full_page = sorted({r["id"] for r in records
                        if r["task"] == "Full-page OCR" and r["prompt_kind"] == "TYPHOON_CARD"})
    already = {p["id"] for p in json.loads(args.pzoom_pages.read_text(encoding="utf-8"))["pages"]}
    if not already <= set(full_page):
        raise SystemExit("P-ZOOM pages are not all Full-page calibration items")
    new = [i for i in full_page if i not in already]
    payload = {
        "provenance": {
            "git_sha": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
            "t1_records_sha256": hashlib.sha256(args.t1_records.read_bytes()).hexdigest(),
            "pzoom_pages_sha256": hashlib.sha256(args.pzoom_pages.read_bytes()).hexdigest(),
            "rule": "Full-page OCR, TYPHOON_CARD, calibration items minus the P-ZOOM pages; sorted by id",
        },
        "totals": {"full_page_items": len(full_page), "pzoom_pages": len(already), "pages": len(new)},
        "pages": [{"id": i} for i in new],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # bytes, not write_text: LF on Windows, so the sha256 pinned in the config matches the git blob
    args.out.write_bytes((json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(payload["totals"]), hashlib.sha256(args.out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
