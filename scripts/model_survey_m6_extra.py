"""MODEL_SURVEY_M6: registered pairings and the markup audit (offline, CPU only).

For every model and prompt of an M6 run (`m6a.yaml` or `m6b.yaml`), on the same
items:

- paired against Typhoon and the base (T1's archived `BENCHMARK_QUESTION`
  outputs) and against Qwen3-VL-4B (M1's archived `BENCHMARK_QUESTION`
  outputs, `M1_OUTPUTS_3431d9f9dccf.json.gz`). For SEA-LION, the last is
  question (a)'s primary;
- per cell: outputs at the token limit, markdown (bold, headings, tables,
  code fences, blockquotes), HTML tags, `<figure>` blocks and unclosed ones.

As in M5, one diagnostic that is not registered: an upper bound for the outputs
whose text the scoring drops after a never-closed `<figure>`, credited with a
perfect read. Writes JSON without reference or output text, and refuses to
overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

from labbs2026.model_survey.analysis import comparison_records, load_role, references_by_id
from labbs2026.model_survey.exploratory import compare
from labbs2026.thai_marks.extract import extract
from labbs2026.thai_marks.order_free import mark_counts

M1_OUTPUTS = Path("docs/stage0/data/M1_OUTPUTS_3431d9f9dccf.json.gz")
MARKUP = {
    "md_bold": re.compile(r"\*\*"),
    "md_heading": re.compile(r"^\s*#{1,6} ", re.M),
    "md_table": re.compile(r"^\s*\|.*\|", re.M),
    "code_fence": re.compile(r"```"),
    "md_blockquote": re.compile(r"^\s*>", re.M),
    "html_tag": re.compile(r"</?[A-Za-z][A-Za-z0-9]*[\s>/]"),
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="the fetched artifacts/<run_id> directory")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(args.config.read_text("utf-8"))
    for line in (args.run_dir / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_dir / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    order_free = config["scoring"]["order_free"]
    boot = config["scoring"]["bootstrap"]
    comparison = config["comparison"]

    def counts(rows):
        return {r["id"]: mark_counts(r["reference"], r["raw_output"], **order_free) for r in rows}

    result: dict = {
        "kind": "M6 registered pairings and markup audit; one unregistered diagnostic (marked)",
        "claim_level": config["claim_level"], "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "run": args.run_dir.name, "order_free": order_free, "bootstrap": boot,
        "audit": {}, "paired": {}, "diagnostic_unclosed_figure_upper_bound": {},
    }
    for role, model in config["models"].items():
        records, _ = load_role(args.run_dir, role, model["prompts"])
        refs = references_by_id(records)
        others = comparison_records(Path(comparison["outputs"]), comparison["roles"], comparison["prompt"], refs)
        others.update(comparison_records(M1_OUTPUTS, ["qwen3vl4b"], "BENCHMARK_QUESTION", refs))
        for task in config["benchmark"]["tasks"]:
            base = {m: counts([r for r in others[m] if r["task"] == task]) for m in others}
            for prompt in model["prompts"]:
                rows = [r for r in records if r["task"] == task and r["prompt_kind"] == prompt]
                structure = [extract(r["raw_output"])[1] for r in rows]
                unclosed = sorted(r["id"] for r, s in zip(rows, structure) if s["unclosed_figures"])
                at_limit = {r["id"] for r in rows if r["reached_max_new_tokens"]}
                cell = f"{role} | {prompt} | {task}"
                result["audit"][cell] = {
                    "n": len(rows), "reached_max_new_tokens": len(at_limit),
                    **{name: sum(1 for r in rows if pattern.search(r["raw_output"]))
                       for name, pattern in MARKUP.items()},
                    "with_figure": sum(1 for s in structure if s["figures"]),
                    "unclosed_figure": unclosed,
                    "unclosed_figure_reached_limit": sorted(i for i in unclosed if i in at_limit),
                }
                own = counts(rows)
                for other, theirs in base.items():
                    ids = sorted(set(theirs) & set(own))
                    key = f"{role} ({prompt}) - {other} (BENCHMARK_QUESTION) / {task}"
                    result["paired"][key] = compare(theirs, own, ids, **boot)
                dropped = [i for i in unclosed if i not in at_limit]
                if dropped:
                    bound = {i: ({**c, "correct": c["reference_marks"], "output_marks": c["reference_marks"]}
                                 if i in dropped else c) for i, c in own.items()}
                    ids = sorted(set(base["typhoon"]) & set(own))
                    result["diagnostic_unclosed_figure_upper_bound"][cell] = {
                        "items": dropped,
                        "reference_marks": sum(own[i]["reference_marks"] for i in dropped),
                        "vs_typhoon": compare(base["typhoon"], bound, ids, **boot),
                    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
