"""Character Error Rate for free-form region transcription.

The frozen Stage-0 evidence modules already contain this Levenshtein routine,
but importing from them would couple a new branch to frozen evidence code and
drag in PIL/numpy/yaml at runtime. The algorithm is reimplemented here and
pinned to the frozen versions by an equivalence test instead.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

# Thai component classes, keyed by the reference character. Frozen before any
# outcome is observed; see REGION_OCR_TOKEN_PRUNING_PROTOCOL.md section 9.
COMPONENT_CLASSES: dict[str, tuple[str, ...]] = {
    "TONE_MARK": ("่", "้", "๊", "๋"),
    "UPPER_VOWEL": ("ั", "ิ", "ี", "ึ", "ื", "็"),
    "LOWER_VOWEL": ("ุ", "ู", "ฺ"),
    "BASE_CONSONANT": tuple(chr(code) for code in range(0x0E01, 0x0E2F)),
}


def codepoint_edit_distance(left: str, right: str) -> int:
    """Levenshtein distance over Unicode codepoints, no grapheme clustering."""
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def classify_component(character: str) -> str:
    for name, members in COMPONENT_CLASSES.items():
        if character in members:
            return name
    return "OTHER"


def region_cer(reference: str, hypothesis: str, *, clamp: bool = False) -> float:
    """CER for one region.

    Unclamped by default, which is the standard definition: a hypothesis longer
    than the reference can exceed 1.0. That matters here because a degenerate
    repetition loop can produce a very large value that dominates a macro mean,
    so `cer_summary` reports how often it happens instead of hiding it.
    """
    if reference == "":
        raise ValueError("reference must be non-empty; empty ground truth is a dataset defect")
    value = codepoint_edit_distance(reference, hypothesis) / len(reference)
    return min(value, 1.0) if clamp else value


def micro_cer(records: Iterable[tuple[str, str]]) -> float:
    """Corpus CER: total edit distance over total reference length."""
    total_distance = 0
    total_length = 0
    for reference, hypothesis in records:
        if reference == "":
            raise ValueError("reference must be non-empty; empty ground truth is a dataset defect")
        total_distance += codepoint_edit_distance(reference, hypothesis)
        total_length += len(reference)
    if total_length == 0:
        raise ValueError("no records supplied")
    return total_distance / total_length


def macro_cer(records: Iterable[tuple[str, str]], *, clamp: bool = False) -> float:
    """Mean of per-region CER. Diverges from micro_cer when lengths differ."""
    values = [region_cer(reference, hypothesis, clamp=clamp) for reference, hypothesis in records]
    if not values:
        raise ValueError("no records supplied")
    return sum(values) / len(values)


def cer_summary(records: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Both averages plus the degenerate-output counts they can conceal."""
    materialized = list(records)
    raw = [region_cer(reference, hypothesis) for reference, hypothesis in materialized]
    return {
        "region_count": len(materialized),
        "macro_cer": sum(raw) / len(raw),
        "macro_cer_clamped": sum(min(value, 1.0) for value in raw) / len(raw),
        "micro_cer": micro_cer(materialized),
        "regions_over_one": sum(1 for value in raw if value > 1.0),
        "empty_hypotheses": sum(1 for _, hypothesis in materialized if hypothesis == ""),
    }


def oracle_page_text(region_texts: Sequence[str], *, separator: str = "\n") -> str:
    """Concatenate region outputs in ground-truth reading order.

    This yields a page-level score whose only error source is the recognizer,
    because the order is taken from ground truth rather than a layout detector.
    """
    return separator.join(region_texts)


def component_error_counts(reference: str, hypothesis: str) -> dict[str, Any]:
    """Per-component error counts for one region.

    Substitutions and deletions are attributed to the class of the *reference*
    character (what the model failed to produce). Insertions have no reference
    character, so they are attributed to the class of the *hypothesis* character
    instead (what the model produced spuriously) and reported in a separate
    field. "Pruning deletes tone marks" and "pruning invents tone marks" are
    different findings and must not be collapsed.

    Diagnostic only. The attribution follows one fixed backtrace through the
    edit matrix; ties are broken in the order substitution, deletion, insertion,
    so the result is deterministic but is one of several equal-cost alignments.
    """
    rows = len(reference)
    columns = len(hypothesis)
    matrix = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows + 1):
        matrix[i][0] = i
    for j in range(columns + 1):
        matrix[0][j] = j
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            matrix[i][j] = min(
                matrix[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]),
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
            )

    components: dict[str, dict[str, int]] = {
        name: {
            "reference_total": 0,
            "hypothesis_total": 0,
            "substitution": 0,
            "deletion": 0,
            "insertion": 0,
        }
        for name in (*COMPONENT_CLASSES, "OTHER")
    }
    for character in reference:
        components[classify_component(character)]["reference_total"] += 1
    for character in hypothesis:
        components[classify_component(character)]["hypothesis_total"] += 1

    i, j = rows, columns
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            substitution_cost = matrix[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1])
            if matrix[i][j] == substitution_cost:
                if reference[i - 1] != hypothesis[j - 1]:
                    components[classify_component(reference[i - 1])]["substitution"] += 1
                i -= 1
                j -= 1
                continue
        if i > 0 and matrix[i][j] == matrix[i - 1][j] + 1:
            components[classify_component(reference[i - 1])]["deletion"] += 1
            i -= 1
            continue
        components[classify_component(hypothesis[j - 1])]["insertion"] += 1
        j -= 1

    totals = {
        "substitution": sum(entry["substitution"] for entry in components.values()),
        "deletion": sum(entry["deletion"] for entry in components.values()),
        "insertion": sum(entry["insertion"] for entry in components.values()),
    }
    return {"components": components, "totals": totals}
