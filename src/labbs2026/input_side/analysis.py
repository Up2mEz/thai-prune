"""Offline analysis of INPUT_SIDE_D1, as registered.

Scoring is F1's (best window, mark fates, a mark scored only where the base is
read correctly and the answer is found — F1 addendum 1). Primary outcome, per
model (Typhoon first) and mark class, exact counts:

- **flips(d)**: marks scored in both `D0` and `Dd` whose status differs
  (correct<->wrong), for d in 4, 8, 12 (patch phase) and 16 (merge pairing);
- **flips(32)**, **flips(64)**: the same between `D0` and `D32` / `D64` — the
  phase-neutral controls;
- the full paired table for each shift, and the marks whose status is not
  constant across D0, D4, D8, D12 among marks scored in all four.

No interval and no decision rule on one (about 105 tone marks in total).
"""

from __future__ import annotations

from typing import Any, Sequence

from labbs2026.find_vs_read.analysis import NORMALIZERS, item_rows, paired_fates  # noqa: F401  (re-exported)

KINDS = ("TONE", "UPPER", "LOWER")
PHASE = (4, 8, 12)
MERGE = 16
CONTROLS = (32, 64)


def _flips(table: dict) -> int:
    return table.get("correct->wrong", 0) + table.get("wrong->correct", 0)


def phase_variable_marks(rows: Sequence[dict], shifts=(0,) + PHASE) -> dict[str, dict[str, int]]:
    """Per class: marks scored (found and base-correct) in every listed shift, and how
    many of them do not have the same status in all of them."""
    out = {k: {"scored_in_all": 0, "not_constant": 0} for k in KINDS}
    for r in rows:
        cells = [r["arms"].get(f"D{d}") for d in shifts]
        if any(c is None or c.get("failed") or not c["found"] for c in cells):
            continue
        by_index = [{m["index"]: m for m in c["mark_fates"]} for c in cells]
        for index, mark in by_index[0].items():
            marks = [b[index] for b in by_index]
            if not all(m["base_correct"] for m in marks):
                continue
            out[mark["kind"]]["scored_in_all"] += 1
            if len({m["fate"] == "correct" for m in marks}) > 1:
                out[mark["kind"]]["not_constant"] += 1
    return out


def summarize(rows: Sequence[dict]) -> dict[str, Any]:
    rows = [r for r in rows if r["reference"]]
    out: dict[str, Any] = {"items": len(rows), "per_shift": {}, "flips_vs_D0": {}}
    for d in PHASE + (MERGE,) + CONTROLS:
        table = paired_fates(rows, f"D{d}", "D0")
        out["per_shift"][f"D{d}"] = table
        out["flips_vs_D0"][f"D{d}"] = {
            k: {"flips": _flips(table["fates"][k]),
                "scored_in_both": sum(v for key, v in table["fates"][k].items() if "->" in key)}
            for k in KINDS}
    out["phase_variable_marks"] = phase_variable_marks(rows)
    out["found_per_shift"] = {
        f"D{d}": sum(1 for r in rows if r["arms"].get(f"D{d}", {}).get("found")) for d in (0,) + PHASE + (MERGE,) + CONTROLS}
    return out
