"""Auditable adapter selection and model-config validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from labbs2026.adapters.base import VLMAdapter


IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")


def adapter_name(model: dict[str, Any]) -> str:
    explicit = model.get("adapter")
    if explicit:
        return str(explicit)
    if model.get("model_id") == "Qwen/Qwen2.5-VL-3B-Instruct":
        return "qwen25_vl"
    raise ValueError("model.adapter is required for an unrecognized backbone")


def validate_model_config(config: dict[str, Any]) -> str:
    if config.get("schema_version") != 1:
        raise ValueError("model config schema_version must be 1")
    model = config.get("model")
    generation = config.get("generation")
    if not isinstance(model, dict) or not isinstance(generation, dict):
        raise ValueError("model config requires model and generation mappings")
    name = adapter_name(model)
    if name not in {"qwen25_vl", "qwen35"}:
        raise ValueError(f"unsupported adapter: {name}")
    revision_keys = ["revision", "processor_revision"]
    if name == "qwen35" or "tokenizer_revision" in model:
        revision_keys.append("tokenizer_revision")
    for key in revision_keys:
        value = model.get(key)
        if not isinstance(value, str) or not IMMUTABLE_REVISION.fullmatch(value):
            raise ValueError(f"model.{key} must be an immutable 40-character Git SHA")
    contract = generation.get("output_contract", {})
    if contract.get("mode") == "canonical_label_token_constraint_v1":
        if generation.get("do_sample") is not False:
            raise ValueError("canonical A/B generation requires do_sample=false")
        if generation.get("max_new_tokens") != 1 or generation.get("min_new_tokens") != 1:
            raise ValueError("canonical A/B generation requires exactly one token")
        if contract.get("allowed_labels") != ["A", "B"]:
            raise ValueError("canonical Stage 0 labels must be [A, B]")
    if name == "qwen35":
        if model.get("model_id") not in {"Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-2B"}:
            raise ValueError("qwen35 adapter requires an official Qwen3.5 model ID")
        if model.get("required_transformers_version") is None:
            raise ValueError("qwen35 config must pin required_transformers_version")
        if generation.get("chat_template_kwargs") != {"enable_thinking": False}:
            raise ValueError("Qwen3.5 Stage 0 must explicitly disable thinking")
    return name


def build_adapter(
    config: dict[str, Any], root: Path, runtime: dict[str, Any] | None = None
) -> VLMAdapter:
    name = validate_model_config(config)
    model = config["model"]
    generation = config["generation"]
    model_runtime = (runtime or {}).get("model_runtime", {})
    cache_value = model_runtime.get("cache_dir", model["cache_dir"])
    cache_dir = Path(cache_value)
    if not cache_dir.is_absolute():
        cache_dir = (root / cache_dir).resolve()
    kwargs = {
        "model_id": model["model_id"],
        "revision": model["revision"],
        "processor_revision": model["processor_revision"],
        "tokenizer_revision": model.get("tokenizer_revision", model["processor_revision"]),
        "cache_dir": cache_dir,
        "device": model_runtime.get("device", model["device"]),
        "dtype": model_runtime.get("dtype", model["dtype"]),
        "attention_implementation": model_runtime.get(
            "attention_implementation", model["attention_implementation"]
        ),
        "use_fast_processor": bool(model["use_fast_processor"]),
        "max_new_tokens": int(generation["max_new_tokens"]),
        "do_sample": bool(generation.get("do_sample", False)),
        "output_contract_mode": generation.get("output_contract", {}).get(
            "mode", "free_generation"
        ),
        "allowed_labels": tuple(
            generation.get("output_contract", {}).get("allowed_labels", ["A", "B"])
        ),
        "chat_template_kwargs": generation.get("chat_template_kwargs", {}),
    }
    if name == "qwen25_vl":
        from labbs2026.adapters.qwen25_vl import Qwen25VLAdapter

        return Qwen25VLAdapter(**kwargs)
    from labbs2026.adapters.qwen35 import Qwen35Adapter

    return Qwen35Adapter(
        **kwargs,
        required_transformers_version=str(model["required_transformers_version"]),
        official_parameter_count=int(model["official_parameter_count"]),
        checkpoint_weight_bytes=int(model["checkpoint_weight_bytes"]),
    )
