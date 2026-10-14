"""W4 condition 3, live: does generating with the stop attached give the offline cut? (CPU, calibration only)

Reads a fetched `w4_live_stop` run (checksums verified) and compares every record
with its calibration output in the archive named by the run's manifest:

- **looping** outputs (the offline cut changes them): the stopped output must equal
  `loop_cut.variant_b` of the archived output, character for character;
- **non-looping** outputs: the criterion must not fire, and the stopped output must
  equal the archived output.

Also reported: whether the text generated live is a prefix of the archived output
(greedy decoding reproduced up to the stop), and the tokens saved. Writes one JSON
file with ids and counts, no output text, and refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.loop_cut import variant_b

DATA = Path("docs/stage0/data")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched artifacts/<run_id>")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    result: dict = {
        "kind": "W4 condition 3, live: generation with the decode-time stop attached vs the offline cut",
        "run_id": args.run_dir.name,
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "cells": {},
    }
    archives: dict = {}
    for manifest_path in sorted((args.run_dir / "live_stop").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        role, name = manifest["role"], manifest["calibration_archive"]
        if name not in archives:
            archives[name] = json.loads(gzip.open(DATA / f"{name}.json.gz", "rt", encoding="utf-8").read())["records"]
        archived = {(r["id"], r["prompt_kind"]): r for r in archives[name][role]}
        records = [json.loads(line) for line in
                   (manifest_path.parent / "records.jsonl").read_text(encoding="utf-8").splitlines()]
        for kind in manifest["prompts"]:
            cell = {"model": f"{manifest['model_id']}@{manifest['revision'][:12]}", "archive": name,
                    "dtype": manifest["dtype_used"], "failures": manifest["failures"],
                    "not_run": manifest["not_run"], "wall_seconds": manifest["wall_seconds"],
                    "looping": 0, "looping_equal": 0, "looping_not_equal": [],
                    "non_looping": 0, "non_looping_unchanged": 0, "non_looping_changed": [],
                    "fired_on_non_looping": [], "live_not_prefix_of_archived": [],
                    "tokens_archived_looping": 0, "tokens_live_looping": 0}
            for r in (r for r in records if r["prompt_kind"] == kind):
                old = archived[(r["id"], kind)]
                if not old["raw_output"].startswith(r["live_text"].rstrip("�")):
                    cell["live_not_prefix_of_archived"].append(r["id"])
                if r["looping_offline"]:
                    cell["looping"] += 1
                    cell["tokens_archived_looping"] += old["generated_tokens"]
                    cell["tokens_live_looping"] += r["generated_tokens"]
                    if r["stopped_text"] == variant_b(old):
                        cell["looping_equal"] += 1
                    else:
                        cell["looping_not_equal"].append(
                            {"id": r["id"], "stopped_chars": len(r["stopped_text"]),
                             "offline_chars": len(variant_b(old)), "first_stop": r["first_stop"]})
                else:
                    cell["non_looping"] += 1
                    if r["fired_during_generation"] or r["first_stop"] is not None:
                        cell["fired_on_non_looping"].append(r["id"])
                    if r["stopped_text"] == old["raw_output"]:
                        cell["non_looping_unchanged"] += 1
                    else:
                        cell["non_looping_changed"].append(r["id"])
            result["cells"][f"{role} | {kind}"] = cell
            print(role, kind, {k: (len(v) if isinstance(v, list) else v) for k, v in cell.items()
                               if k not in ("model", "archive")}, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
