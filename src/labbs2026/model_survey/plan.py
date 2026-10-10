"""MODEL_SURVEY_M1 configuration rules: which prompts a model reads, and which GPU runs which unit.

A unit is one model's share of the items, `(role, shard, shards)`. The config
lists the units of each GPU queue; every unit must appear exactly once.
"""

from __future__ import annotations

import re
from typing import Any

PROMPT_KINDS = ("OCR_NATIVE", "BENCHMARK_QUESTION")
_COMMIT = re.compile(r"[0-9a-f]{40}")


def resolve_prompt(kind: str, question: str, prompts: dict[str, str]) -> str:
    """The text a prompt kind sends for one item."""
    if kind not in PROMPT_KINDS or kind not in prompts:
        raise ValueError(f"unregistered prompt kind {kind!r}")
    if kind == "BENCHMARK_QUESTION":
        if prompts[kind] != "item.question":
            raise ValueError("BENCHMARK_QUESTION must be the item's own question")
        return question
    return prompts[kind]


def _unit(text: str) -> tuple[str, int]:
    role, sep, shard = text.partition("/")
    if not sep or not shard.isdigit():
        raise ValueError(f"unit {text!r} is not role/shard")
    return role, int(shard)


def validate(config: dict[str, Any]) -> list[list[tuple[str, int, int]]]:
    """Check the models, prompts and queues; return the queues as (role, shard, shards)."""
    models = config["models"]
    for role, model in models.items():
        if not _COMMIT.fullmatch(str(model["revision"])):
            raise ValueError(f"{role}: revision must be a full commit sha, never a branch")
        kinds = list(model["prompts"])
        if not kinds or len(set(kinds)) != len(kinds):
            raise ValueError(f"{role}: prompts must be a non-empty list without repeats")
        for kind in kinds:
            if kind not in PROMPT_KINDS or kind not in config["prompts"]:
                raise ValueError(f"{role}: unregistered prompt kind {kind!r}")
        if model["primary_prompt"] not in kinds:
            raise ValueError(f"{role}: primary prompt is not one of its prompts")
        if int(model["shards"]) < 1:
            raise ValueError(f"{role}: shards must be at least 1")
    queues = [[_unit(u) for u in queue] for queue in config["gpu_queues"]]
    listed = [u for queue in queues for u in queue]
    expected = {(role, s) for role, model in models.items() for s in range(int(model["shards"]))}
    if len(listed) != len(set(listed)) or set(listed) != expected:
        raise ValueError("gpu_queues must list every (role, shard) exactly once")
    cap = config.get("budget_cap_t4_hours")
    if cap is not None:
        for queue in queues:
            hours = [models[role].get("unit_deadline_hours") for role, _ in queue]
            if None in hours or sum(float(h) for h in hours) > float(cap):
                raise ValueError("every unit needs a deadline, and a queue's deadlines must fit the budget cap")
    return [[(role, shard, int(models[role]["shards"])) for role, shard in queue]
            for queue in queues]


def unit_command(module: str, name: str, args: list) -> dict[str, Any]:
    """One worker unit: run `python -m module --remote-spec SPEC *args`, logged as `name`."""
    return {"name": name, "module": module, "args": [str(a) for a in args]}


def m1_commands(queues: list[list[tuple[str, int, int]]]) -> list[list[dict[str, Any]]]:
    """M1's GPU queues as worker units (the command each unit ran in M1)."""
    return [[unit_command("labbs2026.model_survey.remote", f"m1_{role}_shard-{shard}-of-{shards}",
                          ["--role", role, "--shard", shard, "--shards", shards])
             for role, shard, shards in queue] for queue in queues]


def select(queues: list[list[tuple[str, int, int]]], roles: list[str]) -> list[list[tuple[str, int, int]]]:
    """The queues restricted to `roles` (a partial run keeps each unit on its GPU)."""
    unknown = set(roles) - {u[0] for q in queues for u in q}
    if unknown:
        raise ValueError(f"unknown roles {sorted(unknown)}")
    return [[u for u in queue if u[0] in roles] for queue in queues]
