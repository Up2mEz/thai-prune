"""Run design for SPEC_DECODE_S1, fixed by the registration before any output.

Item order, warm-up, arm rotation and the budget rule live here so that they are
unit-tested and identical on every machine; `remote.py` only applies them.
"""

from __future__ import annotations

import hashlib
from typing import Sequence


def hash_order(ids: Sequence[str], seed: int) -> list[str]:
    """Ids ordered by `sha256(f"{seed}:{id}")`, the registration's "hash order"."""
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate ids")
    return sorted(ids, key=lambda i: hashlib.sha256(f"{seed}:{i}".encode("utf-8")).hexdigest())


def schedule(
    ids: Sequence[str], seed: int, rotation: Sequence[Sequence[str]], warmup_items: int, limit: int = 0
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """(warm-up ids, [(timed id, arm order)]).

    The first `warmup_items` in hash order are warm-up only. Timed item k gets
    `rotation[k % len(rotation)]`. `limit` (engineering smoke only) keeps the
    first `limit` timed items.
    """
    if not rotation or warmup_items < 0 or limit < 0:
        raise ValueError("bad schedule parameters")
    arms = set(rotation[0])
    if any(set(order) != arms or len(order) != len(arms) for order in rotation):
        raise ValueError("every rotation entry must be a permutation of the same arms")
    ordered = hash_order(ids, seed)
    warmup, timed = ordered[:warmup_items], ordered[warmup_items:]
    if limit:
        timed = timed[:limit]
    return warmup, [(item, list(rotation[k % len(rotation)])) for k, item in enumerate(timed)]


def drop_arm(rotation: Sequence[Sequence[str]], arm: str) -> list[list[str]]:
    """The rotation with `arm` removed, order of the others kept."""
    return [[a for a in order if a != arm] for order in rotation]


def estimated_t4_hours(items: int, seconds_per_item: float, arms: int, parallel_models: int = 2) -> float:
    """Registration §7: items × T1 seconds/item (slower model) × arms ÷ models in parallel."""
    if items < 0 or seconds_per_item < 0 or arms < 1 or parallel_models < 1:
        raise ValueError("bad budget inputs")
    return items * seconds_per_item * arms / parallel_models / 3600.0


def top2_margin(logits_row) -> float:
    """Top-1 minus top-2 logit of a 1-D logits vector."""
    import torch

    values = torch.topk(logits_row.float(), 2).values
    return float((values[0] - values[1]).item())
