"""MODEL_SURVEY_M1 exploratory readings (not registered; reported apart from §4's outcome).

Two questions the registered numbers cannot separate:

1. **Loops versus reading.** Comparisons restricted to items on which neither
   model reached `max_new_tokens`, so a model is not charged twice for looping.
2. **Answering versus transcribing.** Some ThaiOCRBench "Text recognition"
   items show a whole page and the question asks for one part; `OCR:` carries
   no question, so a recognizer transcribes everything (recall up, precision
   down). Items are split by how much text the model produced relative to the
   reference. The split conditions on the model's own output, so it describes
   these runs and is not a test.
"""

from __future__ import annotations

from typing import Any

from labbs2026.model_survey.analysis import paired_f1_difference
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.order_free import prf

LENGTH_RATIO_SPLIT = 1.5


def length_ratio(record: dict) -> float:
    """Characters of extracted output per character of extracted reference."""
    return len(extract_text(record["raw_output"])) / max(1, len(extract_text(record["reference"])))


def no_loop_ids(a: dict[str, dict], b: dict[str, dict]) -> list[str]:
    """Ids read by both whose outputs both stopped before `max_new_tokens` (`a`, `b`: id -> record)."""
    return sorted(i for i in set(a) & set(b)
                  if not a[i]["reached_max_new_tokens"] and not b[i]["reached_max_new_tokens"])


def compare(counts_a: dict[str, dict], counts_b: dict[str, dict], ids: list[str], *, resamples: int,
            seed: int) -> dict[str, Any]:
    """Micro P/R/F1 of both on `ids`, and paired differences (b − a) for F1, recall and precision."""
    a = {i: counts_a[i] for i in ids}
    b = {i: counts_b[i] for i in ids}
    return {"n": len(ids), "a": prf(list(a.values())), "b": prf(list(b.values())),
            "difference": {key: paired_f1_difference(a, b, resamples=resamples, seed=seed, key=key)
                           for key in ("f1", "recall", "precision")}}


def split_by_length(records: dict[str, dict], ids: list[str],
                    threshold: float = LENGTH_RATIO_SPLIT) -> dict[str, list[str]]:
    """`ids` split by whether the model's output is at most `threshold` × the reference's length."""
    out: dict[str, list[str]] = {"about_reference": [], "much_more": []}
    for i in ids:
        out["about_reference" if length_ratio(records[i]) <= threshold else "much_more"].append(i)
    return out
