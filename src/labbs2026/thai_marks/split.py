"""Calibration/locked split, fixed before any output exists.

ThaiOCRBench has no held-out split of its own. Round 3 on TEMS chose its best
budget on the same regions it then scored, which made that improvement
optimistic by selection; every design decision here is therefore taken on a
calibration split, and the locked remainder is opened once.
"""

from __future__ import annotations

import collections
import hashlib
import math
from typing import Iterable

SEED = 20260927
FRACTION = 0.30


def _rank(item_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest()


def calibration_ids(
    items: Iterable[tuple[str, str, str]], *, seed: int = SEED, fraction: float = FRACTION
) -> set[str]:
    """Ids in the calibration split, from (id, task, category) triples.

    Within each (task, category) stratum, items are ordered by
    `sha256(f"{seed}:{id}")` and the first `ceil(fraction * n)` are taken.
    """
    if not 0 < fraction < 1:
        raise ValueError("fraction must lie strictly between 0 and 1")
    strata: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    seen: set[str] = set()
    for item_id, task, category in items:
        if item_id in seen:
            raise ValueError(f"duplicate id {item_id!r}")
        seen.add(item_id)
        strata[(task, category)].append(item_id)
    chosen: set[str] = set()
    for ids in strata.values():
        ordered = sorted(ids, key=lambda i: _rank(i, seed))
        chosen.update(ordered[: math.ceil(fraction * len(ordered))])
    return chosen
