"""Pack a fetched W4 run's outputs without reference text or images (the format of `M1_OUTPUTS_*.json.gz`).

Adds `image_sha256` (W4's page-clustering key) to M1's archive fields. Refuses to overwrite.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from labbs2026.model_survey.analysis import load_role

ARCHIVE_FIELDS = ("id", "task", "prompt_kind", "image_sha256", "raw_output", "generated_tokens",
                  "reached_max_new_tokens", "visual_tokens", "prompt_tokens", "seconds_generate",
                  "seconds_per_generated_token", "resized_size")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id>")
    parser.add_argument("--role", action="append", required=True, metavar="ROLE=PROMPT[,PROMPT]",
                        help="a model and every prompt it was run with")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    rows, hashes = {}, {}
    for spec in args.role:
        role, prompts = spec.split("=", 1)
        records, _ = load_role(args.run_dir, role, prompts.split(","))
        rows[role] = [{k: r.get(k) for k in ARCHIVE_FIELDS} for r in records]
    for path in sorted((args.run_dir / "m1").rglob("records.jsonl")):
        hashes[path.relative_to(args.run_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {"provenance": {"run_id": args.run_dir.name, "records_sha256": hashes,
                              "note": "MODEL_SURVEY W4 outputs; no reference text and no image."},
               "records": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), mtime=0))
    print(args.out, {k: len(v) for k, v in rows.items()})


if __name__ == "__main__":
    main()
