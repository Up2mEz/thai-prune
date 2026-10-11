"""MODEL_SURVEY W3: score T2 on Pathumma and Qwen3-VL-4B as T2 was scored (offline, CPU only).

For each role: the T2 records of its W3 run (all shards finished, checksums
verified), and its archived greedy `BENCHMARK_QUESTION` outputs from the run
named in `configs/model_survey/w3_t2.yaml` (M5 for Pathumma, M1 for
Qwen3-VL-4B). These are scored with `thai_marks.analysis` read-only, exactly as
`scripts/thai_marks_score_v2.py` scores T2:

- `summarize_t2_v2`: oracle, prior, contrastive and greedy per task and mark;
- greedy correctness with scoring v2's chance-located rule;
- `oracle_by_convention`.

Writes one JSON file without reference or output text, and refuses to
overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.model_survey.analysis import load_role
from labbs2026.thai_marks.analysis import analyze_t1_v2, oracle_by_convention, summarize_t2_v2


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def _verified(run_dir: Path) -> Path:
    for line in (run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {run_dir / relative}")
    return run_dir


def _t2_records(run_dir: Path, role: str) -> tuple[list[dict], list[dict]]:
    root = run_dir / "t2" / role
    files = sorted(root.rglob("records.jsonl"))
    if not files or any(not (f.parent / "manifest.json").exists() for f in files):
        raise SystemExit(f"{root}: missing or unfinished shards")
    records = [json.loads(line) for f in files for line in f.open(encoding="utf-8") if line.strip()]
    if len({r["id"] for r in records}) != len(records):
        raise SystemExit(f"{root}: an item appears twice")
    manifests = [json.loads((f.parent / "manifest.json").read_text("utf-8")) for f in files]
    return records, manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/model_survey/w3_t2.yaml"))
    parser.add_argument("--w3", action="append", required=True, metavar="ROLE=ARTIFACT_DIR",
                        help="a role and its fetched W3 artifacts/<run_id> directory")
    parser.add_argument("--greedy-root", type=Path, default=Path("runs/kaggle"),
                        help="where the greedy runs' fetched artifacts live")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    seed = int(config["scoring"]["null_seed"])

    result: dict = {
        "kind": "MODEL_SURVEY W3: T2 on other models (registered, MODEL_SURVEY_W3_REGISTRATION.md)",
        "claim_level": config["claim_level"], "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "roles": {},
    }
    for entry in args.w3:
        role, _, path = entry.partition("=")
        run_dir = _verified(Path(path))
        records, manifests = _t2_records(run_dir, role)
        source = config["greedy"][role]
        greedy_dir = _verified(args.greedy_root / source["run"] / "fetched" / "artifacts" / source["run"])
        leg_prompts = json.loads(next((greedy_dir / "m1" / role).rglob("manifest.json")).read_text("utf-8"))["prompts"]
        rows, _ = load_role(greedy_dir, role, leg_prompts)
        rows = [r for r in rows if r["prompt_kind"] == source["prompt"]]
        t1 = analyze_t1_v2(rows, seed=seed)
        thresholds = {key.split(" / ")[0]: cell["chance"]["threshold"] for key, cell in t1.items()}
        greedy = {r["id"]: r["raw_output"] for r in rows}
        result["roles"][role] = {
            "w3_run": run_dir.name, "greedy_run": source["run"], "greedy_prompt": source["prompt"],
            "items_scored": len(records),
            "manifests": [{k: m.get(k) for k in ("shard", "dtype_used", "placement", "items",
                                                 "selected_items", "not_run", "failures",
                                                 "wall_seconds", "transformers")} for m in manifests],
            "chance_thresholds": thresholds,
            "t2": summarize_t2_v2(records, greedy=greedy, located_below=thresholds),
            "conventions": {task: oracle_by_convention([r for r in records if r["task"] == task])
                            for task in sorted({r["task"] for r in records})},
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
