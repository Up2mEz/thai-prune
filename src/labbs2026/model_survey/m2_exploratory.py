"""MODEL_SURVEY_M2 exploratory readings (not registered; reported apart from §4's outcome).

Three questions the registered numbers leave open:

1. **Does the penalty, or sampling, add anything once loops are stopped?**
   Paired differences between arms other than against `G` (the pairs are
   listed by the script).
2. **What does the stop remove?** For each output it cuts: whether the output
   had reached `max_new_tokens` and whether the run is a runaway to the end
   (a cut of an output that ended normally, or of a run followed by more
   text, can drop real reading: registration Addendum 1); the marks it removes
   from the output; the reference marks credited inside the removed text; and
   whether the loop's repeated unit occurs in the reference at all. Where it
   does not, the credit is alignment alone: the order-free metric's residual
   global alignment lines a unit of common syllables (say `ที่`) up with the
   same syllables across the reference. Also the tokens a decode-time stop
   would have generated, to the first copy (what the `+B` cost reports) and to
   the point of detection.
3. **What do the loops repeat?** Among outputs reaching `max_new_tokens`, how
   many repeat a unit carrying Thai marks, and the marks they put in the
   output. A loop of digits costs no mark precision; a loop of Thai words does.

Plus a split of each stopped arm's items by whether its output looped before
the stop, against Typhoon, to locate what the stop cannot return; and, on
Text recognition, the symmetric subset the review asked for (both models
well-behaved), next to M1's one-sided split.
"""

from __future__ import annotations

from typing import Any

from labbs2026.model_survey.exploratory import LENGTH_RATIO_SPLIT, length_ratio
from labbs2026.thai_marks.attribution import MARKS
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.loop_cut import LONG_UNIT, loop_onset

STOP_K, STOP_K_LONG = 8, 6          # loop_cut.variant_b's


def loop_unit(text: str) -> str | None:
    """The repeated unit at which T5b's variant B stops `text`, or None if it does not."""
    onset = loop_onset(text, STOP_K, STOP_K_LONG)
    return None if onset is None else text[onset[0]:onset[0] + onset[1]]


def stop_point(text: str) -> dict[str, int] | None:
    """Where variant B acts on `text`, in characters, or None if it does not.

    `onset` and `unit_chars` locate the first copy (what the cut keeps);
    `fires_at` is where the 8th copy (6th for long units) completes, the
    earliest point a decode-time stop could detect the run; `chars_after_run`
    is the text after the run's last whole copy. A run that ends in less than
    one unit of text is a runaway to the end of the output: the cut drops
    repeats only.
    """
    onset = loop_onset(text, STOP_K, STOP_K_LONG)
    if onset is None:
        return None
    start, unit = onset
    copies = 1
    while text.startswith(text[start:start + unit], start + copies * unit):
        copies += 1
    return {"onset": start, "unit_chars": unit, "copies": copies,
            "fires_at": start + (STOP_K if unit < LONG_UNIT else STOP_K_LONG) * unit,
            "chars_after_run": len(text) - (start + copies * unit)}


def stop_effect(record: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """What the stop removed from one output it cut, and what stopping at detection would have cost.

    `record` is the output before the stop; `before` and `after` are its
    `mark_counts` without and with the stop. The unit is compared with the
    reference after `extract_text` on both. Tokens are scaled by characters
    (as `m2.stop_at_loop` does): to the first copy (what the `+B` arms'
    cost reports, a lower bound on tokens, so an upper bound on the saving)
    and to the point of detection.
    """
    text = record["raw_output"]
    point = stop_point(text)
    unit = extract_text(text[point["onset"]:point["onset"] + point["unit_chars"]])
    per_char = record["generated_tokens"] / max(1, len(text))
    return {"id": record["id"], "reached_max_new_tokens": bool(record["reached_max_new_tokens"]),
            **point, "runaway_to_end": point["chars_after_run"] < point["unit_chars"],
            "output_marks_removed": before["output_marks"] - after["output_marks"],
            "credited_marks_removed": before["correct"] - after["correct"],
            "unit_in_reference": bool(unit) and unit in extract_text(record["reference"]),
            "unit_has_marks": any(c in MARKS for c in unit),
            "generated_tokens": record["generated_tokens"],
            "tokens_to_first_copy": round(per_char * (point["onset"] + point["unit_chars"])),
            "tokens_to_detection": round(per_char * min(len(text), point["fires_at"]))}


def summarize_stops(effects: list[dict[str, Any]]) -> dict[str, Any]:
    """Totals over one arm and task's cut outputs, split as the review asked (Addendum 1).

    Parts: all cuts; cuts on outputs that had ended normally (the ones that can
    cost recall); cuts whose run is not a runaway to the end; cuts whose unit
    never occurs in the reference.
    """
    parts = {"all": effects,
             "ended_normally": [e for e in effects if not e["reached_max_new_tokens"]],
             "not_runaway_to_end": [e for e in effects if not e["runaway_to_end"]],
             "unit_not_in_reference": [e for e in effects if not e["unit_in_reference"]]}
    out: dict[str, Any] = {"cut": len(effects)}
    for part, rows in parts.items():
        out[part] = {"n": len(rows), **{key: sum(e[key] for e in rows) for key in (
            "output_marks_removed", "credited_marks_removed", "generated_tokens",
            "tokens_to_first_copy", "tokens_to_detection")}}
    return out


def symmetric_ids(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]],
                  threshold: float = LENGTH_RATIO_SPLIT) -> list[str]:
    """Ids on which both outputs are well-behaved: neither reached `max_new_tokens`, both at most
    `threshold` × the reference's length. Selects on both models, unlike M1's split on one."""
    return sorted(i for i in set(a) & set(b)
                  if not a[i]["reached_max_new_tokens"] and not b[i]["reached_max_new_tokens"]
                  and length_ratio(a[i]) <= threshold and length_ratio(b[i]) <= threshold)


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
