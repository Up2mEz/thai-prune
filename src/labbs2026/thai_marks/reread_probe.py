"""E2: is a re-read right where the page read misread a mark? (`E2_REREAD_FIXES_MISREADS_DRAFT.md`)."""

from __future__ import annotations

from typing import Sequence

from labbs2026.thai_marks.confidence import _marks
from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from

NOT_FOUND_CER = 0.4


def _base_of(text: str, h: int) -> int:
    """Step back from a combining mark to the character it sits on.

    The anchored alignment may start its window on a mark (a tie between a
    substitution and an insertion), putting a reference consonant against the
    read's mark; the cluster to compare is the one the mark belongs to.
    """
    from labbs2026.thai_marks.orthography import COMBINING

    while h > 0 and text[h] in COMBINING:
        h -= 1
    return h


def view_status(line: str, ref_index: int, reads: Sequence[str]) -> str:
    """`right`, `wrong` or `not_found` for one reference cluster in one view.

    The line is aligned (reference-anchored) to each read of the view; the
    read with the lowest CER is used. Right means the base consonant and its
    marks at the aligned position equal the reference's.
    """
    best = None
    for read in reads:
        if not read:
            continue
        pairs, _, _ = align_anchored(line, read)
        cer = edit_distance_from(pairs, line, read) / len(line)
        if best is None or cer < best[0]:
            best = (cer, pairs, read)
    if best is None or best[0] >= NOT_FOUND_CER:
        return "not_found"
    _, pairs, read = best
    hyp = {r: h for r, h in pairs if r is not None and h is not None}
    h = hyp.get(ref_index)
    if h is None:
        return "wrong"
    h = _base_of(read, h)
    return "right" if read[h] == line[ref_index] and _marks(read, h) == _marks(line, ref_index) else "wrong"


# --- E2b: majority vote at flagged places (`E2B_FLAGGED_VOTE_DRAFT.md`) ------

def _cluster_at(text: str, i: int) -> str:
    from labbs2026.thai_marks.orthography import COMBINING

    j = i + 1
    while j < len(text) and text[j] in COMBINING:
        j += 1
    return text[i:j]


def view_vote(line: str, index: int, reads: Sequence[str]) -> str | None:
    """The cluster a view reads at `line[index]`, or None if the view abstains."""
    best = None
    for read in reads:
        if not read:
            continue
        pairs, _, _ = align_anchored(line, read)
        cer = edit_distance_from(pairs, line, read) / len(line)
        if best is None or cer < best[0]:
            best = (cer, pairs, read)
    if best is None or best[0] >= NOT_FOUND_CER:
        return None
    _, pairs, read = best
    h = {r: h for r, h in pairs if r is not None and h is not None}.get(index)
    return None if h is None else _cluster_at(read, _base_of(read, h))


def majority(own: str, votes: Sequence[str | None]) -> str:
    """The strict-majority cluster among `own` and the non-abstaining votes, else `own`."""
    cast = [own] + [v for v in votes if v is not None]
    best = max(set(cast), key=cast.count)
    return best if cast.count(best) * 2 > len(cast) else own


def flagged_edits(raw: str, clusters: Sequence[tuple[int, int, float]],
                  views: dict[str, Sequence[str]], threshold: float,
                  min_line: int = 8) -> list[tuple[int, int, str]]:
    """(start, end, replacement) for flagged consonant-led clusters whose vote changes them.

    `clusters` are (start, end, s_min) over the raw page read.
    """
    from labbs2026.thai_marks.confidence import CONSONANT_SET

    edits = []
    for start, end, s in clusters:
        if s < threshold or raw[start] not in CONSONANT_SET:
            continue
        line_start = raw.rfind("\n", 0, start) + 1
        line_end = raw.find("\n", end)
        line_end = len(raw) if line_end == -1 else line_end
        line = raw[line_start:line_end]
        if len(line) < min_line:
            continue
        own = raw[start:end]
        votes = [view_vote(line, start - line_start, reads) for reads in views.values()]
        chosen = majority(own, votes)
        if chosen != own:
            edits.append((start, end, chosen))
    return edits


def apply_edits(raw: str, edits: Sequence[tuple[int, int, str]]) -> str:
    out, cursor = [], 0
    for start, end, new in sorted(edits):
        if start < cursor:
            continue
        out += [raw[cursor:start], new]
        cursor = end
    return "".join(out) + raw[cursor:]
