"""MODEL_SURVEY_M5: secondary comparisons and the markup audit (offline, CPU only).

Registered secondaries not in `model_survey_analyze.py`'s output:

- the secondary prompt (`BENCHMARK_QUESTION`) paired against Typhoon and the base on
  the same prompt;
- per-cell counts of JSON-wrapped outputs, outputs at the token limit, `<figure>`
  blocks and unclosed `<figure>` blocks (Addendum 1 asks for the wrapped counts).

One diagnostic, not registered: an upper bound for the pages whose text the
scoring drops after a malformed, never-closed `<figure>` tag, by crediting those
outputs with a perfect read. Writes JSON with no reference text and no output
text, and refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.model_survey.analysis import comparison_records, load_role, references_by_id
from labbs2026.model_survey.exploratory import compare
from labbs2026.model_survey.m5 import is_wrapped
from labbs2026.thai_marks.extract import extract
from labbs2026.thai_marks.order_free import mark_counts


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="the fetched artifacts/<run_id> directory")
    parser.add_argument("--config", type=Path, default=Path("configs/model_survey/m5.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    (role, model), = config["models"].items()
    records, _ = load_role(args.run_dir, role, model["prompts"])
    comparison = config["comparison"]
    others = comparison_records(Path(comparison["outputs"]), comparison["roles"], comparison["prompt"],
                                references_by_id(records))
    order_free = config["scoring"]["order_free"]
    boot = config["scoring"]["bootstrap"]

    def counts(rows):
        return {r["id"]: mark_counts(r["reference"], r["raw_output"], **order_free) for r in rows}

    result: dict = {
        "kind": "M5 registered secondaries and markup audit; one unregistered diagnostic (marked)",
        "claim_level": config["claim_level"], "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "run": args.run_dir.name, "order_free": order_free, "bootstrap": boot,
        "audit": {}, "paired": {}, "diagnostic_unclosed_figure_upper_bound": {},
    }
    for task in config["benchmark"]["tasks"]:
        base = {m: counts([r for r in others[m] if r["task"] == task]) for m in others}
        ids = sorted(base["typhoon"])
        for prompt in model["prompts"]:
            rows = [r for r in records if r["task"] == task and r["prompt_kind"] == prompt]
            structure = [extract(r["raw_output"])[1] for r in rows]
            unclosed = sorted(r["id"] for r, s in zip(rows, structure) if s["unclosed_figures"])
            result["audit"][f"{prompt} | {task}"] = {
                "n": len(rows),
                "json_wrapped": sorted(r["id"] for r in rows if is_wrapped(r["raw_output"])),
                "reached_max_new_tokens": sum(r["reached_max_new_tokens"] for r in rows),
                "with_figure": sum(1 for s in structure if s["figures"]),
                "unclosed_figure": unclosed,
                "unclosed_figure_reached_limit": sorted(r["id"] for r in rows
                                                        if r["id"] in unclosed and r["reached_max_new_tokens"]),
            }
            own = counts(rows)
            for other in comparison["roles"]:
                key = f"{role} ({prompt}) - {other} ({comparison['prompt']}) / {task}"
                result["paired"][key] = compare(base[other], own, ids, **boot)
            # Diagnostic (not registered): the outputs that ended on their own but lose
            # text after an unclosed <figure>, credited with a perfect read.
            dropped = [i for i in unclosed if i not in result["audit"][f"{prompt} | {task}"]["unclosed_figure_reached_limit"]]
            if dropped:
                bound = {i: ({**c, "correct": c["reference_marks"], "output_marks": c["reference_marks"]}
                             if i in dropped else c) for i, c in own.items()}
                result["diagnostic_unclosed_figure_upper_bound"][f"{prompt} | {task}"] = {
                    "items": dropped,
                    "reference_marks": sum(own[i]["reference_marks"] for i in dropped),
                    "vs_typhoon": compare(base["typhoon"], bound, ids, **boot),
                }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
