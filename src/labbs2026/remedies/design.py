"""Run design for REMEDIES_R1, fixed by its registration before any output."""

from __future__ import annotations

import collections
import hashlib
from typing import Iterable


def hash_rank(item_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).hexdigest()


def pilot_ids(items: Iterable[tuple[str, str]], *, seed: int, per_task: int) -> list[str]:
    """First `per_task` ids of each task in hash order, from (id, task) pairs.

    Returned task by task (tasks sorted by name), each in hash order.
    """
    if per_task < 1:
        raise ValueError("per_task must be at least 1")
    by_task: dict[str, list[str]] = collections.defaultdict(list)
    seen: set[str] = set()
    for item_id, task in items:
        if item_id in seen:
            raise ValueError(f"duplicate id {item_id!r}")
        seen.add(item_id)
        by_task[task].append(item_id)
    chosen: list[str] = []
    for task in sorted(by_task):
        chosen += sorted(by_task[task], key=lambda i: hash_rank(i, seed))[:per_task]
    return chosen


def noise_seed(item_id: str, seed: int) -> int:
    """Per-item seed for VCD's noise, so every model sees the same noised image."""
    return int(hash_rank(item_id, seed)[:8], 16)


def arm_names(arms: dict, controls: dict | None, smoke: bool) -> list[str]:
    """Arms run for this submission: controls only in a smoke, FULL always first."""
    names = list(arms)
    if smoke and controls:
        names += [c for c in controls if c not in names]
    if "FULL" not in names:
        raise ValueError("FULL must be an arm")
    return ["FULL"] + [n for n in names if n != "FULL"]
