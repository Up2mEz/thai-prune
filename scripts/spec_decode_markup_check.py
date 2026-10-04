"""Exploratory markup check of a fetched SPEC_DECODE_S1 run (not registered).

Recomputes, on text instead of raw HTML: the headline/degenerate split and its
speedups, loops among outputs at the token budget, and the drift of diverged
outputs. With `--divergence-kinds`, also the Thai-only base rate for the
divergence-kind comparison. See `labbs2026.spec_decode.markup_check`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.spec_decode.analysis import SPEC_ARMS, item_rows, summarize
from labbs2026.spec_decode.identity import compare_outputs, truncate_new_tokens
from labbs2026.spec_decode.markup_check import (
    TEXT_FORMS, divergence_thai_counts, drift, loops_at_budget, median_or_none, quantile_linear,
    thai_only_mark_share, with_population,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="fetched artifacts/<run_id> directory")
    parser.add_argument("--divergence-kinds", type=Path, help="exported divergence-kind shares (JSON)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result: dict = {"run_id": args.run.name}
    for role in ("base", "typhoon"):
        d = args.run / "s1" / role
        mnt = int(json.loads((d / "manifest.json").read_text(encoding="utf-8"))["max_new_tokens"])
        records = [json.loads(l) for l in (d / "records.jsonl").read_text(encoding="utf-8").splitlines()]
        timed = [r for r in records if not r["warmup"]]
        refs = {r["id"]: r["arms"]["REF"] for r in timed}
        rows = item_rows(records, mnt)
        out: dict = {"populations": {}, "loops_at_budget": loops_at_budget(refs.values()), "drift": {}}
        for name, form in TEXT_FORMS.items():
            s = summarize(with_population(rows, refs, form))
            out["populations"][name] = {
                "n": s["populations"],
                **{arm: {"headline": s[arm]["headline"]["geomean_speedup"],
                         "degenerate": (s[arm]["degenerate"] or {}).get("geomean_speedup")} for arm in SPEC_ARMS},
            }
        for arm in SPEC_ARMS:
            raw, text, ids = [], [], []
            for r in timed:
                ref, a = r["arms"]["REF"], r["arms"][arm]
                if compare_outputs(truncate_new_tokens(ref["new_token_ids"], 0, mnt),
                                   truncate_new_tokens(a["new_token_ids"], 0, mnt)).identical:
                    continue
                raw.append(drift(ref["text"], a["text"]))
                text.append(drift(ref["text"], a["text"], TEXT_FORMS["structural_text"]))
                ids.append(r["id"])
            out["drift"][arm] = {
                "n": len(raw), "quantile_rule": "linear",
                "raw": {"median": median_or_none(raw), "p90": quantile_linear(raw, 0.9) if raw else None},
                "structural": {"median": median_or_none(text), "p90": quantile_linear(text, 0.9) if text else None},
                "largest_structural": sorted(zip(text, ids), reverse=True)[:2],
            }
        result[role] = out
    if args.divergence_kinds:
        kinds = json.loads(args.divergence_kinds.read_text(encoding="utf-8"))
        result["divergence_kinds_thai_only"] = {
            role: {"base_rate_thai": thai_only_mark_share(v["ref_token_kinds"]),
                   **{arm: divergence_thai_counts(v[arm]["ref_token_kind"], v[arm]["divergences"]) for arm in SPEC_ARMS}}
            for role, v in kinds.items()
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
