"""E2: is a re-read right where the page read misread a mark? (`E2_REREAD_FIXES_MISREADS_DRAFT.md`)."""

from __future__ import annotations

from typing import Sequence

from labbs2026.thai_marks.confidence import _marks
from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from

NOT_FOUND_CER = 0.4


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
    return "right" if read[h] == line[ref_index] and _marks(read, h) == _marks(line, ref_index) else "wrong"
