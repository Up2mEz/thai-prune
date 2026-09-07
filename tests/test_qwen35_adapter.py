from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from labbs2026.adapters.factory import build_adapter, validate_model_config
from labbs2026.adapters.qwen35 import Qwen35Adapter


REVISION = "8" * 40


class _Grid:
    def __getitem__(self, _index: int) -> SimpleNamespace:
        return SimpleNamespace(tolist=lambda: [1, 28, 28])


class _InputIds:
    def __eq__(self, token_id: int) -> SimpleNamespace:
        assert token_id == 248056
        return SimpleNamespace(sum=lambda: SimpleNamespace(item=lambda: 196))


def _config() -> dict:
    return {
        "schema_version": 1,
        "model": {
            "adapter": "qwen35",
            "model_id": "Qwen/Qwen3.5-4B",
            "revision": REVISION,
            "processor_revision": REVISION,
            "tokenizer_revision": REVISION,
            "required_transformers_version": "5.12.0",
            "official_parameter_count": 4_659_865_088,
            "checkpoint_weight_bytes": 9_319_828_096,
            "cache_dir": ".cache",
            "device": "cuda",
            "dtype": "float16",
            "attention_implementation": "sdpa",
            "use_fast_processor": True,
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": 1,
            "min_new_tokens": 1,
            "chat_template_kwargs": {"enable_thinking": False},
            "output_contract": {
                "mode": "canonical_label_token_constraint_v1",
                "allowed_labels": ["A", "B"],
                "expected_label_token_ids": {"A": 32, "B": 33},
            },
        },
    }


def test_qwen35_factory_requires_explicit_immutable_contract(tmp_path: Path) -> None:
    config = _config()
    assert validate_model_config(config) == "qwen35"
    adapter = build_adapter(config, tmp_path)
    assert isinstance(adapter, Qwen35Adapter)
    assert adapter.chat_template_kwargs == {"enable_thinking": False}
    assert adapter.tokenizer_revision == REVISION


def test_qwen35_rejects_mutable_revision_and_implicit_thinking() -> None:
    config = _config()
    config["model"]["revision"] = "main"
    with pytest.raises(ValueError, match="immutable"):
        validate_model_config(config)
    config = _config()
    config["generation"]["chat_template_kwargs"] = {}
    with pytest.raises(ValueError, match="disable thinking"):
        validate_model_config(config)


def test_qwen35_visual_accounting_reconciles_grid_prompt_and_runtime() -> None:
    adapter = object.__new__(Qwen35Adapter)
    adapter._last_runtime_premerge_count = 784
    processor = SimpleNamespace(
        patch_size=16, temporal_patch_size=2, merge_size=2,
    )
    adapter._processor = SimpleNamespace(image_processor=processor, image_token_id=248056)
    inputs = {
        "image_grid_thw": _Grid(),
        "input_ids": _InputIds(),
    }
    image = Image.new("RGB", (448, 448), "white")

    metadata = adapter._metadata_from_inputs(inputs, image, runtime_count=196)

    assert metadata.premerge_patch_count == 784
    assert metadata.runtime_premerge_patch_count == 784
    assert metadata.llm_visual_token_count == 196
    assert metadata.input_image_token_count == 196
    assert metadata.runtime_vision_output_count == 196
    assert metadata.runtime_llm_input_position_count == 196


def test_qwen35_visual_accounting_fails_closed_on_runtime_mismatch() -> None:
    adapter = object.__new__(Qwen35Adapter)
    adapter._last_runtime_premerge_count = 783
    processor = SimpleNamespace(patch_size=16, temporal_patch_size=2, merge_size=2)
    adapter._processor = SimpleNamespace(image_processor=processor, image_token_id=248056)
    inputs = {
        "image_grid_thw": _Grid(),
        "input_ids": _InputIds(),
    }
    with pytest.raises(RuntimeError, match="runtime premerge=783"):
        adapter._metadata_from_inputs(inputs, Image.new("RGB", (448, 448)), runtime_count=196)
