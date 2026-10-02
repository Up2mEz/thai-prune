"""Read-then-point for Text recognition (`docs/stage0/G1_READ_THEN_POINT_DRAFT.md`).

Typhoon reads a crop best under its own prompt (`TYPHOON_CARD`), which
transcribes everything; the benchmark question's answer (`BENCHMARK_QUESTION`)
says which text was asked for. The answer is the stretch of the TC
transcription that best matches the BQ answer. No reference is used.
"""

from __future__ import annotations

from labbs2026.thai_marks.decompose import align, edit_distance_from
from labbs2026.thai_marks.extract import extract_text

MAX_LINES = 5
MIN_SIMILARITY = 0.5


def similarity(a: str, b: str) -> float:
    """1 − Levenshtein(a, b) / max(len); 1.0 for two empty strings."""
    longest = max(len(a), len(b))
    if not longest:
        return 1.0
    return 1 - edit_distance_from(align(a, b), a, b) / longest


def transcription_lines(raw_output: str) -> list[str]:
    return [line for line in (extract_text(part) for part in raw_output.split("\n")) if line]


def point(bq_output: str, tc_output: str, *, max_lines: int = MAX_LINES,
          min_similarity: float = MIN_SIMILARITY) -> dict:
    """The answer and how it was chosen (`fell_back` when the pointer failed)."""
    pointer = extract_text(bq_output)
    lines = transcription_lines(tc_output)
    best = None
    for start in range(len(lines)):
        for count in range(1, max_lines + 1):
            if start + count > len(lines):
                break
            candidate = " ".join(lines[start:start + count])
            key = (similarity(pointer, candidate), -len(candidate), -start)
            if best is None or key > best[0]:
                best = (key, candidate, start, count)
    if best is None or best[0][0] < min_similarity:
        return {"answer": pointer, "fell_back": True,
                "similarity": best[0][0] if best else None}
    return {"answer": best[1], "fell_back": False, "similarity": best[0][0],
            "lines": (best[2], best[2] + best[3])}
