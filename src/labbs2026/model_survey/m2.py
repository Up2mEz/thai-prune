"""MODEL_SURVEY_M2 — Wayu's loops: decoding arms, per-item seeds, and the offline stop.

Arms change only decoding; everything else is M1's. A greedy arm overrides T1's
`repetition_penalty`; a sampling arm (the model card's recipe) also sets
`do_sample`, `temperature` and `top_p`, with one seed per item derived from the
item id, so a result does not depend on item order or sharding. The offline
stop is T5b's variant B (`thai_marks.loop_cut`, Decision Log 2026-10-03e):
cutting an output where an exact repeat completes its 8th copy (6th for long
units) is what stopping decoding there would have produced, because decoding
never revisits earlier tokens. A control arm (registration Addendum 1) decodes
exactly as T1 and must reproduce M1's outputs (`G`) token for token.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from labbs2026.thai_marks.generation import generation_kwargs
from labbs2026.thai_marks.loop_cut import variant_b

GREEDY_KEYS = frozenset({"do_sample", "repetition_penalty"})
SAMPLING_KEYS = frozenset({"do_sample", "temperature", "top_p", "repetition_penalty"})


def arm_kwargs(base: dict[str, Any], arm: dict[str, Any], max_new_tokens: int) -> dict[str, Any]:
    """`generate()` kwargs for one arm: T1's pinned greedy settings with the arm's overrides."""
    kwargs = generation_kwargs(base, max_new_tokens)
    penalty = float(arm["repetition_penalty"])
    if penalty < 1.0:
        raise ValueError("repetition_penalty below 1.0 rewards repetition")
    if arm["do_sample"] is False:
        if set(arm) != GREEDY_KEYS:
            raise ValueError(f"a greedy arm has exactly {sorted(GREEDY_KEYS)}")
        return {**kwargs, "repetition_penalty": penalty}
    if arm["do_sample"] is not True or set(arm) != SAMPLING_KEYS:
        raise ValueError(f"a sampling arm has exactly {sorted(SAMPLING_KEYS)}")
    temperature, top_p = float(arm["temperature"]), float(arm["top_p"])
    if temperature <= 0 or not 0 < top_p <= 1:
        raise ValueError("temperature must be > 0 and top_p in (0, 1]")
    return {**kwargs, "do_sample": True, "temperature": temperature, "top_p": top_p,
            "repetition_penalty": penalty}


def item_seed(base: int, item_id: str) -> int:
    """The sampling seed of one item: fixed by the run's seed and the item's id."""
    return int.from_bytes(hashlib.sha256(f"{base}:{item_id}".encode("utf-8")).digest()[:4], "big")


def validate(config: dict[str, Any]) -> list[list[str]]:
    """Check arms, queues and deadlines; return the GPU queues as lists of arm names."""
    arms = config["arms"]
    base, max_new = config["runtime"]["generation"], int(config["runtime"]["max_new_tokens"])
    for name, arm in arms.items():
        arm_kwargs(base, arm, max_new)
        if name in config.get("offline_arms", {}):
            raise ValueError(f"{name} is both a run arm and an offline arm")
    for name, arm in config.get("control", {}).get("arms", {}).items():
        if name in arms or name in config.get("offline_arms", {}) or name == config["reference_arm"]["name"]:
            raise ValueError(f"{name} is both a control arm and another arm")
        if arm_kwargs(base, arm, max_new) != generation_kwargs(base, max_new):
            raise ValueError(f"control arm {name} must decode exactly as T1 and M1's G")
    queues = [list(q) for q in config["gpu_queues"]]
    listed = [a for q in queues for a in q]
    if len(listed) != len(set(listed)) or set(listed) != set(arms):
        raise ValueError("gpu_queues must list every arm exactly once")
    for queue in queues:
        if float(config["unit_deadline_hours"]) * len(queue) > float(config["budget_cap_t4_hours"]):
            raise ValueError("a queue's deadlines must fit the budget cap")
    return queues


def load_arm(run_root: Path, arm: str) -> tuple[list[dict], dict]:
    """One run arm's records and manifest; refuses an unfinished arm or a miscount."""
    leg = run_root / "m2" / arm
    if not (leg / "manifest.json").is_file():
        raise FileNotFoundError(f"{leg}: no manifest.json (arm did not finish)")
    manifest = json.loads((leg / "manifest.json").read_text("utf-8"))
    records = [json.loads(line) for line in (leg / "records.jsonl").read_text("utf-8").splitlines()
               if line.strip()]
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{leg}: an item is recorded twice")
    if len(records) != manifest["items"] - len(manifest["failures"]):
        raise ValueError(f"{leg}: {len(records)} records, manifest implies "
                         f"{manifest['items'] - len(manifest['failures'])}")
    return records, manifest


def reproduces(control: list[dict], reference: dict[str, dict]) -> dict[str, Any]:
    """Whether each control output equals the reference arm's output for its item, token for token.

    Token for token is read as the same text and the same generated-token
    count (records keep text, not token ids). `reference` maps item id to record.
    """
    items = []
    for r in control:
        g = reference.get(r["id"])
        text = g is not None and r["raw_output"] == g["raw_output"]
        first = None
        if g is not None and not text:
            a, b = r["raw_output"], g["raw_output"]
            first = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        items.append({"id": r["id"], "task": r["task"], "in_reference": g is not None, "same_text": text,
                      "same_tokens": g is not None and r["generated_tokens"] == g["generated_tokens"],
                      "first_difference": first, "generated_tokens": r["generated_tokens"],
                      "reached_max_new_tokens": r["reached_max_new_tokens"]})
    same = [i["same_text"] and i["same_tokens"] for i in items]
    return {"n": len(items), "reproduced": sum(same), "all_reproduced": bool(items) and all(same),
            "items": items}


def cost(records: list[dict]) -> dict[str, Any]:
    """Decoding cost and loop counts of one arm's records in one task."""
    return {"n": len(records),
            "generated_tokens": sum(r["generated_tokens"] for r in records),
            "seconds_generate": sum(r["seconds_generate"] for r in records),
            "reached_max_new_tokens": sum(bool(r["reached_max_new_tokens"]) for r in records),
            "t5b_cut": sum(bool(r.get("t5b_cut")) for r in records)}


def stop_at_loop(record: dict[str, Any]) -> dict[str, Any]:
    """T5b variant B on one record: the output a decode-time stop would have produced.

    A cut output did not reach `max_new_tokens`; the tokens and seconds it would
    have saved are scaled by characters (an approximation, as in T5b).
    """
    cut = variant_b(record)
    if cut == record["raw_output"]:
        return {**record, "t5b_cut": False}
    share = len(cut) / max(1, len(record["raw_output"]))
    return {**record, "raw_output": cut, "reached_max_new_tokens": False, "t5b_cut": True,
            "generated_tokens": round(record["generated_tokens"] * share),
            "seconds_generate": record["seconds_generate"] * share}
