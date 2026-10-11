"""MODEL_SURVEY_M3 — Wayu with loop escape: plan, unit commands, records, built-in control, stop-only twin.

One run arm, `E` (`model_survey.escape`), on M1's items, image policy, prompt
and decoding, split into position shards across the two T4s.

**Stop-only twin (`E0`).** An escaped output starts with greedy's output up to
the first rollback, the end of the first loop's first copy. That prefix is
what stopping at the loop yields, so `E0` (each escaped output cut to its
greedy prefix; every other output as it is) is the stop-only reading of the
same run. `E` − `E0` isolates what decoding past the loop adds, with no
cross-run difference.

**Built-in control.** Against M1's greedy outputs (`G`): an output without an
escape must equal `G`'s token for token, and an escaped output's greedy prefix
must be a prefix of `G`'s output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from labbs2026.model_survey.plan import unit_command
from labbs2026.thai_marks.generation import generation_kwargs

T1_GENERATION = {"do_sample": False, "num_beams": 1, "repetition_penalty": 1.0, "no_repeat_ngram_size": 0}


def validate(config: dict[str, Any]) -> list[list[tuple[str, int, int]]]:
    """Check decoding, escape settings, shards and budget; return the GPU queues as (arm, shard, shards)."""
    if config["runtime"]["generation"] != T1_GENERATION:
        raise ValueError("M3 decodes exactly as T1 and M1; only the escape is added")
    generation_kwargs(config["runtime"]["generation"], int(config["runtime"]["max_new_tokens"]))
    e = config["escape"]
    if int(e["every"]) < 1 or int(e["max_escapes"]) < 0:
        raise ValueError("escape.every must be >= 1 and escape.max_escapes >= 0")
    if int(e["max_total_steps"]) < int(config["runtime"]["max_new_tokens"]):
        raise ValueError("escape.max_total_steps must allow at least max_new_tokens")
    shards = int(config["shards"])
    if shards < 1:
        raise ValueError("shards must be >= 1")
    if float(config["unit_deadline_hours"]) > float(config["budget_cap_t4_hours"]):
        raise ValueError("a unit's deadline must fit the budget cap")
    return [[(e["arm"], k, shards)] for k in range(shards)]


def m3_commands(queues: list[list[tuple[str, int, int]]]) -> list[list[dict[str, Any]]]:
    """The worker's unit commands, one per shard."""
    return [[unit_command("labbs2026.model_survey.remote_m3", f"m3_{arm}_shard-{k}-of-{n}",
                          ["--shard", k, "--shards", n]) for arm, k, n in queue] for queue in queues]


def load_shards(run_root: Path, arm: str, shards: int) -> tuple[list[dict], list[dict]]:
    """All shards' records and manifests; refuses an unfinished shard, a miscount or a duplicate item."""
    records: list[dict] = []
    manifests: list[dict] = []
    for k in range(shards):
        leg = run_root / "m3" / arm / f"shard-{k}-of-{shards}"
        if not (leg / "manifest.json").is_file():
            raise FileNotFoundError(f"{leg}: no manifest.json (shard did not finish)")
        manifest = json.loads((leg / "manifest.json").read_text("utf-8"))
        rows = [json.loads(line) for line in (leg / "records.jsonl").read_text("utf-8").splitlines()
                if line.strip()]
        if len(rows) != manifest["items"] - len(manifest["failures"]):
            raise ValueError(f"{leg}: {len(rows)} records, manifest implies "
                             f"{manifest['items'] - len(manifest['failures'])}")
        records += rows
        manifests.append(manifest)
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("an item is recorded twice")
    return records, manifests


def stop_only(record: dict[str, Any]) -> dict[str, Any]:
    """`E0`: an escaped output cut to its greedy prefix (what stopping at the first loop yields)."""
    if not record["escapes"] and not record["final_cut"]:
        return {**record, "escaped": False}
    return {**record, "raw_output": record["raw_output"][:record["greedy_prefix_chars"]],
            "generated_tokens": record["greedy_prefix_tokens"], "reached_max_new_tokens": False,
            "escaped": True}


def control(records: list[dict], greedy: dict[str, dict]) -> dict[str, Any]:
    """The built-in control against M1's greedy outputs (`greedy`: id -> record).

    No escape: the output equals greedy's, text and token count. Escaped: its
    greedy prefix is a prefix of greedy's output.
    """
    items = []
    for r in records:
        g = greedy.get(r["id"])
        escaped = bool(r["escapes"]) or bool(r["final_cut"])
        if g is None:
            ok = False
        elif escaped:
            ok = g["raw_output"].startswith(r["raw_output"][:r["greedy_prefix_chars"]])
        else:
            ok = r["raw_output"] == g["raw_output"] and r["generated_tokens"] == g["generated_tokens"]
        items.append({"id": r["id"], "task": r["task"], "escaped": escaped, "ok": ok})
    plain = [i for i in items if not i["escaped"]]
    escaped_items = [i for i in items if i["escaped"]]
    return {"n": len(items), "no_escape": len(plain), "no_escape_identical": sum(i["ok"] for i in plain),
            "escaped": len(escaped_items), "escaped_prefix_ok": sum(i["ok"] for i in escaped_items),
            "all_ok": bool(items) and all(i["ok"] for i in items),
            "failed": [i["id"] for i in items if not i["ok"]]}


def escape_summary(records: list[dict]) -> dict[str, Any]:
    """Escape diagnostics for one task's records."""
    escaped = [r for r in records if r["escapes"] or r["final_cut"]]
    return {"n": len(records), "escaped": len(escaped),
            "escapes": sum(len(r["escapes"]) for r in records),
            "final_cut": sum(bool(r["final_cut"]) for r in records),
            "step_cap_hit": sum(bool(r["step_cap_hit"]) for r in records),
            "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in records),
            "kept_tokens": sum(r["generated_tokens"] for r in records),
            "decoded_tokens": sum(r["total_steps"] for r in records),
            "seconds_generate": sum(r["seconds_generate"] for r in records)}

