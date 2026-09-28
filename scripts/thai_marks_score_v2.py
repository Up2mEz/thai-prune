"""Score fetched T1/T2 artifacts with scoring version 2 (offline, CPU only).

Writes one JSON file and refuses to overwrite an existing one. Version 1
(as registered) is computed alongside for continuity.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.thai_marks.analysis import (
    analyze_t1_v2,
    score_t1_record,
    summarize_t1,
    summarize_t2_v2,
)


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def _t2_leg(root: Path) -> tuple[list[dict], list[str]]:
    """All records of one role's T2 leg, one directory or several shards.

    Every directory holding records must hold a manifest.json, i.e. have
    finished; unfinished ones are returned by name and nothing is merged.
    """
    record_files = sorted(root.rglob("records.jsonl"))
    missing = [str(f.parent) for f in record_files if not (f.parent / "manifest.json").exists()]
    if not record_files:
        missing = [str(root)]
    records = [] if missing else [r for f in record_files for r in _load(f)]
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{root}: an item appears in more than one shard")
    return records, missing


def _pct(value) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True,
                        help="fetched artifacts/<run_id> directory")
    parser.add_argument("--config", type=Path, default=Path("configs/thai_marks/t1_t2.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--t2-dir", action="append", default=[], metavar="ROLE=PATH",
                        help="read this role's T2 from another run's artifacts/<run_id> "
                             "(e.g. a later rerun); may be sharded")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    config = yaml.safe_load(args.config.read_text("utf-8"))
    t2_roots = {}
    for entry in args.t2_dir:
        role, _, path = entry.partition("=")
        t2_roots[role] = Path(path)
    scoring = config["scoring"]
    seed = int(scoring["null_seed"])
    result: dict = {
        "claim_level": config["claim_level"],
        "scoring": scoring,
        "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                  text=True, check=True).stdout.strip(),
        "git_dirty": bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                         text=True, check=True).stdout.strip()),
        "t1": {}, "t1_v1_as_registered": {}, "t2": {}, "t2_source": {}, "excluded": {},
    }

    for role in ("base", "typhoon"):
        t1_path = args.artifact_dir / "t1" / role / "records.jsonl"
        if not t1_path.exists():
            result["excluded"][f"t1/{role}"] = "no records"
            continue
        records = _load(t1_path)
        manifest_path = args.artifact_dir / "t1" / role / "manifest.json"
        if not manifest_path.exists():
            result["excluded"][f"t1/{role}"] = "leg did not finish (no manifest.json)"
            continue
        manifest = json.loads(manifest_path.read_text("utf-8"))
        expected = manifest["items"] * len(config["t1"]["prompts"]) - len(manifest["failures"])
        if len(records) != expected:
            raise SystemExit(f"t1/{role}: {len(records)} records, manifest implies {expected}")
        result["t1"][role] = analyze_t1_v2(records, seed=seed)
        result["t1_v1_as_registered"][role] = {
            prompt: summarize_t1([score_t1_record(r) for r in records if r["prompt_kind"] == prompt])
            for prompt in sorted({r["prompt_kind"] for r in records})
        }
        t2_root = t2_roots.get(role, args.artifact_dir) / "t2" / role
        t2_records, missing = _t2_leg(t2_root)
        if missing:
            result["excluded"][f"t2/{role}"] = f"unfinished (no manifest.json): {missing}"
            continue
        result["t2_source"][role] = str(t2_root)
        greedy = {r["id"]: r["raw_output"] for r in records
                  if r["prompt_kind"] == config["t2"]["prompt"]}
        thresholds = {task: cell["chance"]["threshold"]
                      for key, cell in result["t1"][role].items()
                      for task, prompt in [key.split(" / ")]
                      if prompt == config["t2"]["prompt"]}
        result["t2"][role] = summarize_t2_v2(t2_records, greedy=greedy,
                                             located_below=thresholds)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    primary = scoring["primary_prompt"]
    for role, cells in result["t1"].items():
        for key, s in cells.items():
            task, prompt = key.split(" / ")
            tag = "PRIMARY" if primary.get(task) == prompt else "secondary"
            marks = "  ".join(f"{k} {_pct(s[k]['mark_specific_error']['estimate'])}"
                              for k in ("TONE", "UPPER", "LOWER"))
            print(f"{role:8s} {task:17s} {prompt:18s} {tag:9s} "
                  f"located {_pct(s['located_rate'])}  median CER {_pct(s['median_cer'])}  "
                  f"micro CER {_pct(s['micro_cer']['estimate'])}  | mark-specific {marks}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
