"""Markup audit of a fetched run, per model and arm — run before reporting any result.

Works on the record layouts of T1, SPEC_DECODE_S1, REMEDIES_R*, FIND_VS_READ_F1
and INPUT_SIDE_D1: every `records.jsonl` under the run directory; outputs are
taken from `arms.<ARM>.raw_output` / `arms.<ARM>.text` or `raw_output`.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from labbs2026.output_diagnostics.markup import summarize


def outputs_by_cell(run: Path) -> dict[tuple[str, str], list[str]]:
    cells: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for records in sorted(run.rglob("records.jsonl")):
        model = records.parent.name
        for line in records.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "arms" in rec:
                for arm, out in rec["arms"].items():
                    if isinstance(out, dict) and not out.get("failed"):
                        text = out.get("raw_output", out.get("text"))
                        if text is not None:
                            cells[(model, arm)].append(text)
            elif "raw_output" in rec:
                cells[(model, rec.get("prompt_kind", "output"))].append(rec["raw_output"])
    return cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="fetched artifacts/<run_id> directory")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = {f"{m}/{a}": summarize(texts) for (m, a), texts in outputs_by_cell(args.run).items()}
    for key, s in result.items():
        print(f"{key:28} n={s['outputs']:3} tags={s['with_any_tag']:3} {s['top_tags']} figure={s['with_figure']} "
              f"heading={s['with_headings']} list={s['with_list_markers']} bold={s['with_bold']} "
              f"pipe={s['with_pipe_table']} fence={s['with_code_fence']} latex={s['with_latex']} entities={s['with_entities']} "
              f"| Thai lost T1 {s['thai_lost_t1_share']:.1%} structural {s['thai_lost_structural_share']:.1%} "
              f"outputs>10%-lost {s['outputs_losing_over_10pct_thai_t1']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
