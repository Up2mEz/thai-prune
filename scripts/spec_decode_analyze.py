"""Analyse a fetched SPEC_DECODE_S1 run with the registered analysis only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from labbs2026.spec_decode.analysis import item_rows, summarize


def verify(run: Path) -> None:
    if (run / "FAILURE.json").exists():
        raise SystemExit("run has FAILURE.json; refusing to analyse")
    for line in (run / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        if hashlib.sha256((run / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="fetched artifacts/<run_id> directory")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    verify(args.run)
    result = {"run_id": args.run.name}
    for role in ("base", "typhoon"):
        d = args.run / "s1" / role
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        records = [json.loads(l) for l in (d / "records.jsonl").read_text(encoding="utf-8").splitlines()]
        rows = item_rows(records, int(manifest["max_new_tokens"]))
        result[role] = {"manifest": {k: manifest[k] for k in ("dtype_used", "timed_items", "revision", "git_sha")},
                        "summary": summarize(rows)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
