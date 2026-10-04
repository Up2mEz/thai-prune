"""E1-B1: confidence-gated, lexicon-checked token swap (`E1B_LEXICON_GATED_SWAP_DRAFT.md`).

Offline: uses the per-token log-probabilities and top-5 alternatives recorded
by E1 (`runtime.score_own_output`). Only low-confidence tokens are touched,
only to turn a non-word into a word, and only with the model's own
alternatives.
"""

from __future__ import annotations

import math
import re
from typing import Callable, Sequence

THAI = re.compile(r"[฀-๿]")
MAX_DROP = math.log(10)  # an alternative must keep >= 10% of the chosen token's probability
FLAG_SHARE = 0.05


def flag_threshold(logprobs_by_output: Sequence[Sequence[float]],
                   texts_by_output: Sequence[Sequence[str]], share: float = FLAG_SHARE) -> float:
    """Log-probability at or below which a Thai token is in the lowest `share` of a cell."""
    values = sorted(lp for lps, texts in zip(logprobs_by_output, texts_by_output)
                    for lp, t in zip(lps, texts) if THAI.search(t))
    if not values:
        return -math.inf
    return values[max(0, math.ceil(share * len(values)) - 1)]


def _word_at(segment: Callable[[str], list[str]], line: str, pos: int) -> str:
    cursor = 0
    for word in segment(line):
        if cursor <= pos < cursor + len(word):
            return word
        cursor += len(word)
    return ""


def propose(raw: str, offsets: Sequence[tuple[int, int]], logprob: Sequence[float],
            top_ids: Sequence[Sequence[int]], top_logprobs: Sequence[Sequence[float]],
            threshold: float, decode: Callable[[int], str],
            segment: Callable[[str], list[str]], words: frozenset[str]) -> list[dict]:
    """The swaps the rule makes in one output, as (start, end, old, new, ...)."""
    swaps = []
    for k, (start, end) in enumerate(offsets):
        chosen = raw[start:end]
        if end <= start or not THAI.search(chosen) or logprob[k] > threshold:
            continue
        line_start = raw.rfind("\n", 0, start) + 1
        line_end = raw.find("\n", end)
        line_end = len(raw) if line_end == -1 else line_end
        line, pos = raw[line_start:line_end], start - line_start
        w0 = _word_at(segment, line, pos)
        if not w0 or w0 in words:
            continue
        best = None
        for tid, lp in zip(top_ids[k], top_logprobs[k]):
            alt = decode(tid)
            if (alt == chosen or lp < logprob[k] - MAX_DROP or "�" in alt
                    or not THAI.search(alt)):
                continue
            new_line = line[:pos] + alt + line[pos + (end - start):]
            if _word_at(segment, new_line, pos) in words and (best is None or lp > best[1]):
                best = (alt, lp)
        if best:
            swaps.append({"start": start, "end": end, "old": chosen, "new": best[0],
                          "token": k, "logprob": logprob[k], "alt_logprob": best[1], "w0": w0})
    return swaps


def apply(raw: str, swaps: Sequence[dict]) -> str:
    """Apply non-overlapping swaps left to right."""
    out, cursor = [], 0
    for s in sorted(swaps, key=lambda s: s["start"]):
        if s["start"] < cursor:
            continue
        out.append(raw[cursor:s["start"]])
        out.append(s["new"])
        cursor = s["end"]
    out.append(raw[cursor:])
    return "".join(out)
