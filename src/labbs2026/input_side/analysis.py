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
from labbs2026.find_vs_read.scoring import best_window
from labbs2026.thai_marks.decompose import align
from labbs2026.thai_marks.orthography import CONSONANTS

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


def consonant_status(reference: str, cell: dict) -> dict[int, bool] | None:
    """Per reference consonant: read correctly in the arm's best window (None if not found)."""
    if cell.get("failed") or not cell["found"]:
        return None
    _, start, end = best_window(reference, cell["hypothesis"])
    window = cell["hypothesis"][start:end]
    fate = {}
    for r, h in align(reference, window):
        if r is not None:
            fate[r] = h is not None and reference[r] == window[h]
    return {i: fate.get(i, False) for i, c in enumerate(reference) if c in CONSONANTS}


def consonant_flips(rows: Sequence[dict], d: int) -> dict[str, int]:
    """Registration §6: consonants scored in both D0 and Dd whose status differs."""
    flips = scored = 0
    for r in rows:
        a = consonant_status(r["reference"], r["arms"].get(f"D{d}", {"failed": True}))
        b = consonant_status(r["reference"], r["arms"].get("D0", {"failed": True}))
        if a is None or b is None:
            continue
        for i in b:
            scored += 1
            flips += a[i] != b[i]
    return {"flips": flips, "scored_in_both": scored}


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
    out["consonant_flips_vs_D0"] = {f"D{d}": consonant_flips(rows, d) for d in PHASE + (MERGE,) + CONTROLS}
    out["phase_variable_marks"] = phase_variable_marks(rows)
    out["found_per_shift"] = {
        f"D{d}": sum(1 for r in rows if r["arms"].get(f"D{d}", {}).get("found")) for d in (0,) + PHASE + (MERGE,) + CONTROLS}
    return out
