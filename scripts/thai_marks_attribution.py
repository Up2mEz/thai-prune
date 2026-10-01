"""Attribute every wrong reference mark to a cause, per (model, task, prompt) cell."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from labbs2026.thai_marks.attribution import CAUSES, CAUSES_APPROX, attribute_marks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-dir", type=Path, required=True,
                        help="fetched artifacts t1/ directory (holds <role>/records.jsonl)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")

    cells: dict[str, dict] = {}
    for records_path in sorted(args.t1_dir.glob("*/records.jsonl")):
        role = records_path.parent.name
        records = [json.loads(line) for line in records_path.open(encoding="utf-8") if line.strip()]
        for approx, causes in ((False, CAUSES), (True, CAUSES_APPROX)):
            totals: dict[tuple, collections.Counter] = collections.defaultdict(collections.Counter)
            for r in records:
                totals[(r["task"], r["prompt_kind"])] += attribute_marks(
                    r["reference"], r["raw_output"], approximate_reorder=approx)
            for (task, prompt), counts in sorted(totals.items()):
                marks = sum(counts.values())
                wrong = marks - counts["correct"]
                cell = cells.setdefault(f"{role} | {task} | {prompt}", {})
                cell["approximate_reorder" if approx else "verbatim_reorder"] = {
                    "marks": marks, "wrong": wrong,
                    "wrong_share": wrong / marks if marks else None,
                    "counts": {c: counts[c] for c in causes},
                    "share_of_wrong": {c: counts[c] / wrong if wrong else None for c in causes},
                }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cells, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, cell in cells.items():
        v, a = cell["verbatim_reorder"], cell["approximate_reorder"]
        print(name, f"wrong {v['wrong_share']:.1%}",
              {c: f"{a['share_of_wrong'][c]:.0%}" for c in CAUSES_APPROX if a["share_of_wrong"][c]})


if __name__ == "__main__":
    main()
