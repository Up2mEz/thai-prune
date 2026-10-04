"""Edit distance without the full DP table.

`labbs2026.thai_marks.decompose.align` keeps the whole Levenshtein table to
trace an alignment back. On a looped output (~10,000 characters) against a page
reference (~3,000) that is ~30 million Python ints, and the R1 pilot analysis
ran a 16 GB machine out of memory. Distance alone needs no table: this is the
bit-parallel algorithm of Myers (1999) in Hyyrö's (2001) formulation, with the
pattern held in one Python integer, so memory is O(len(reference)) bits and the
work is one big-int step per hypothesis character. It returns exactly the
Levenshtein distance (unit costs), the same number `edit_distance_from(align(...))`
gives; tests check this on random strings.
"""

from __future__ import annotations


def levenshtein(reference: str, hypothesis: str) -> int:
    m = len(reference)
    if m == 0:
        return len(hypothesis)
    peq: dict[str, int] = {}
    for i, char in enumerate(reference):
        peq[char] = peq.get(char, 0) | (1 << i)
    mask = (1 << m) - 1
    high = 1 << (m - 1)
    pv, mv, score = mask, 0, m
    for char in hypothesis:
        eq = peq.get(char, 0)
        xv = eq | mv
        xh = (((eq & pv) + pv) ^ pv) | eq
        ph = mv | (~(xh | pv) & mask)
        mh = pv & xh
        if ph & high:
            score += 1
        elif mh & high:
            score -= 1
        ph = ((ph << 1) | 1) & mask
        mh = (mh << 1) & mask
        pv = mh | (~(xv | ph) & mask)
        mv = ph & xv
    return score
