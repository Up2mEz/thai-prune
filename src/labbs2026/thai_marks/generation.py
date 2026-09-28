"""Decoding parameters for T1, pinned in config and recorded as resolved.

Both pinned checkpoints ship a `generation_config.json` for sampling
(`do_sample: true`, temperature 0.7, top_p 0.8, top_k 20). T1 is a
deterministic baseline, so decoding is greedy: the temperature -> 0 limit, in
which temperature, top_p and top_k have no effect. transformers 5.12 applies
arguments passed to `generate()` last, over the checkpoint's defaults, and adds
the temperature/top-k/top-p warpers only when `do_sample` is true
(`generation/utils.py`), so passing the pinned values explicitly is what makes
them the ones used. The resolved configuration is recorded with every run.
"""

from __future__ import annotations

from typing import Any

ALLOWED = frozenset({"do_sample", "num_beams", "repetition_penalty", "no_repeat_ngram_size"})

# Fields that change the output of greedy decoding. Sampling fields
# (temperature, top_p, top_k, ...) are recorded as inactive, not omitted.
ACTIVE_UNDER_GREEDY = ("do_sample", "num_beams", "max_new_tokens", "repetition_penalty",
                       "no_repeat_ngram_size", "eos_token_id", "pad_token_id")
SAMPLING_ONLY = ("temperature", "top_p", "top_k", "min_p", "typical_p")


def generation_kwargs(settings: dict[str, Any], max_new_tokens: int) -> dict[str, Any]:
    """`generate()` keyword arguments from the config's `t1.generation` block."""
    unknown = set(settings) - ALLOWED
    if unknown:
        raise ValueError(f"unregistered generation settings: {sorted(unknown)}")
    missing = ALLOWED - set(settings)
    if missing:
        raise ValueError(f"generation settings must all be pinned; missing {sorted(missing)}")
    if settings["do_sample"] is not False or settings["num_beams"] != 1:
        raise ValueError("T1 is registered as greedy decoding: do_sample false, num_beams 1")
    return {**settings, "max_new_tokens": int(max_new_tokens)}


def describe_resolved(resolved: dict[str, Any]) -> dict[str, Any]:
    """What a resolved generation config means, for the run manifest."""
    return {
        "active": {k: resolved.get(k) for k in ACTIVE_UNDER_GREEDY},
        "inactive_because_greedy": {k: resolved.get(k) for k in SAMPLING_ONLY},
    }
