"""MODEL_SURVEY_M2 exploratory readings (not registered; reported apart from §4's outcome).

Three questions the registered numbers leave open:

1. **Does the penalty, or sampling, add anything once loops are stopped?**
   Paired differences between arms other than against `G` (the pairs are
   listed by the script).
2. **What does the stop remove?** For each output it cuts: the marks it removes
   from the output, the reference marks credited inside the removed text, and
   whether the loop's repeated unit occurs in the reference at all. Where it
   does not, the credit is alignment alone: the order-free metric's residual
   global alignment lines a unit of common syllables (say `ที่`) up with the
   same syllables across the reference.
3. **What do the loops repeat?** Among outputs reaching `max_new_tokens`, how
   many repeat a unit carrying Thai marks, and the marks they put in the
   output. A loop of digits costs no mark precision; a loop of Thai words does.

Plus a split of each stopped arm's items by whether its output looped before
the stop, against Typhoon, to locate what the stop cannot return.
"""

from __future__ import annotations

from typing import Any

from labbs2026.thai_marks.attribution import MARKS
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.loop_cut import loop_onset

STOP_K, STOP_K_LONG = 8, 6          # loop_cut.variant_b's


def loop_unit(text: str) -> str | None:
    """The repeated unit at which T5b's variant B stops `text`, or None if it does not."""
    onset = loop_onset(text, STOP_K, STOP_K_LONG)
    return None if onset is None else text[onset[0]:onset[0] + onset[1]]


def stop_effect(record: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """What the stop removed from one output it cut.

    `before` and `after` are the output's `mark_counts` without and with the
    stop. The unit is compared with the reference after `extract_text` on both.
    """
    unit = extract_text(loop_unit(record["raw_output"]) or "")
    return {"output_marks_removed": before["output_marks"] - after["output_marks"],
            "credited_marks_removed": before["correct"] - after["correct"],
            "unit_in_reference": bool(unit) and unit in extract_text(record["reference"]),
            "unit_has_marks": any(c in MARKS for c in unit)}


def summarize_stops(effects: list[dict[str, Any]]) -> dict[str, Any]:
    """Totals over one arm and task's cut outputs, split by whether the unit occurs in the reference."""
    out: dict[str, Any] = {"cut": len(effects)}
    for part, rows in (("all", effects), ("unit_not_in_reference", [e for e in effects if not e["unit_in_reference"]])):
        out[part] = {"n": len(rows),
                     "output_marks_removed": sum(e["output_marks_removed"] for e in rows),
                     "credited_marks_removed": sum(e["credited_marks_removed"] for e in rows)}
    return out


def loop_content(records: list[dict[str, Any]], counts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Outputs reaching `max_new_tokens` in one arm and task: what they repeat and the marks they carry.

    `counts` maps every item id of `records` to its `mark_counts`.
    """
    looping = [r for r in records if r["reached_max_new_tokens"]]
    units = [loop_unit(r["raw_output"]) for r in looping]
    return {"n": len(records), "reached_max": len(looping),
            "exact_repeat": sum(u is not None for u in units),
            "unit_has_marks": sum(u is not None and any(c in MARKS for c in u) for u in units),
            "output_marks_in_looping": sum(counts[r["id"]]["output_marks"] for r in looping),
            "output_marks_all": sum(counts[r["id"]]["output_marks"] for r in records)}


def split_by_loop(records: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Ids split by whether the output, before any stop, reached `max_new_tokens`."""
    return {"looped": sorted(i for i, r in records.items() if r["reached_max_new_tokens"]),
            "did_not_loop": sorted(i for i, r in records.items() if not r["reached_max_new_tokens"])}
