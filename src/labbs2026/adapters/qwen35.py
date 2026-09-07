"""Qwen3.5 dense-VLM adapter with runtime-verified merger accounting."""

from __future__ import annotations

import time
from dataclasses import replace
from importlib.metadata import version
from typing import Any

from labbs2026.adapters.base import VisualStageMetadata
from labbs2026.adapters.qwen25_vl import Qwen25VLAdapter


MEASUREMENT_BOUNDARY = (
    "Qwen3.5 Vision Encoder spatial-merger output (pooler_output), matched to "
    "the image placeholder positions replaced in the language-model input"
)


class Qwen35Adapter(Qwen25VLAdapter):
    """Pinned Qwen3.5 adapter; shared A/B logic remains backbone-independent."""

    def __init__(
        self,
        *,
        required_transformers_version: str,
        official_parameter_count: int,
        checkpoint_weight_bytes: int,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.required_transformers_version = required_transformers_version
        self.official_parameter_count = int(official_parameter_count)
        self.checkpoint_weight_bytes = int(checkpoint_weight_bytes)
        self._last_runtime_premerge_count: int | None = None

    def _verify_transformers_runtime(self) -> None:
        observed = version("transformers")
        if observed != self.required_transformers_version:
            raise RuntimeError(
                "Qwen3.5 runtime requires exact transformers version "
                f"{self.required_transformers_version}, observed {observed}"
            )

    @property
    def processor(self) -> Any:
        if self._processor is None:
            self._verify_transformers_runtime()
            from transformers import AutoProcessor

            self._processor = AutoProcessor.from_pretrained(
                self.model_id,
                revision=self.processor_revision,
                cache_dir=self.cache_dir,
                use_fast=self.use_fast_processor,
            )
        return self._processor

    @property
    def model(self) -> Any:
        if self._model is None:
            self._verify_transformers_runtime()
            import torch
            from transformers import Qwen3_5ForConditionalGeneration

            dtype_by_name = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }
            if self.dtype_name not in dtype_by_name:
                raise ValueError(f"unsupported dtype: {self.dtype_name}")
            started = time.perf_counter()
            self._model = Qwen3_5ForConditionalGeneration.from_pretrained(
                self.model_id,
                revision=self.revision,
                cache_dir=self.cache_dir,
                dtype=dtype_by_name[self.dtype_name],
                attn_implementation=self.attention_implementation,
                device_map=self.device,
                low_cpu_mem_usage=True,
            )
            self._model.eval()
            self.model_load_seconds = time.perf_counter() - started
        return self._model

    def _register_runtime_visual_hooks(self, captured: dict[str, int]) -> list[Any]:
        def capture_premerge(_module: Any, _args: Any, output: Any) -> None:
            captured["premerge"] = int(output.shape[0])
            self._last_runtime_premerge_count = captured["premerge"]

        def capture_postmerge(_module: Any, _args: Any, output: Any) -> None:
            captured["postmerge"] = int(output.shape[0])

        visual = self.model.model.visual
        return [
            visual.patch_embed.register_forward_hook(capture_premerge),
            visual.merger.register_forward_hook(capture_postmerge),
        ]

    def _metadata_from_inputs(
        self, inputs: Any, image: Any, runtime_count: int | None = None
    ) -> VisualStageMetadata:
        metadata = super()._metadata_from_inputs(inputs, image, runtime_count=runtime_count)
        runtime_premerge = self._last_runtime_premerge_count if runtime_count is not None else None
        if runtime_count is not None and runtime_premerge != metadata.premerge_patch_count:
            raise RuntimeError(
                "visual-token mismatch: "
                f"grid premerge={metadata.premerge_patch_count}, "
                f"runtime premerge={runtime_premerge}"
            )
        return replace(
            metadata,
            measurement_boundary=MEASUREMENT_BOUNDARY,
            runtime_premerge_patch_count=runtime_premerge,
            runtime_llm_input_position_count=runtime_count,
        )

    def architecture_record(self) -> dict[str, Any]:
        self._verify_transformers_runtime()
        from transformers import AutoConfig

        processor = self.processor.image_processor
        config = AutoConfig.from_pretrained(
            self.model_id,
            revision=self.revision,
            cache_dir=self.cache_dir,
        )
        vision = config.vision_config
        return {
            "adapter": "qwen35",
            "model_id": self.model_id,
            "model_revision": self.revision,
            "processor_revision": self.processor_revision,
            "tokenizer_revision": self.tokenizer_revision,
            "model_class": "Qwen3_5ForConditionalGeneration",
            "processor_wrapper_class": type(self.processor).__name__,
            "tokenizer_class": type(self.processor.tokenizer).__name__,
            "processor_class": type(processor).__name__,
            "use_fast_processor": self.use_fast_processor,
            "transformers_version": version("transformers"),
            "required_transformers_version": self.required_transformers_version,
            "official_parameter_count": self.official_parameter_count,
            "checkpoint_weight_bytes": self.checkpoint_weight_bytes,
            "vision_depth": int(vision.depth),
            "vision_hidden_size": int(vision.hidden_size),
            "vision_output_hidden_size": int(vision.out_hidden_size),
            "patch_size": int(processor.patch_size),
            "temporal_patch_size": int(processor.temporal_patch_size),
            "spatial_merge_size": int(processor.merge_size),
            "min_pixels": int(processor.size["shortest_edge"]),
            "max_pixels": int(processor.size["longest_edge"]),
            "do_resize": bool(processor.do_resize),
            "resample": int(processor.resample),
            "do_rescale": bool(processor.do_rescale),
            "rescale_factor": float(processor.rescale_factor),
            "do_normalize": bool(processor.do_normalize),
            "image_mean": [float(value) for value in processor.image_mean],
            "image_std": [float(value) for value in processor.image_std],
            "do_convert_rgb": bool(processor.do_convert_rgb),
            "deepstack_visual_indexes": list(vision.deepstack_visual_indexes),
            "measurement_boundary": MEASUREMENT_BOUNDARY,
            "count_formula": "prod(image_grid_thw) / spatial_merge_size^2",
            "runtime_verification": (
                "patch_embed output + spatial merger output + processor image "
                "placeholder count"
            ),
            "device": self.device,
            "dtype": self.dtype_name,
            "attention_implementation": self.attention_implementation,
            "chat_template_kwargs": self.chat_template_kwargs,
            "generation": {
                "do_sample": self.do_sample,
                "max_new_tokens": self.max_new_tokens,
                "output_contract_mode": self.output_contract_mode,
                "allowed_labels": list(self.allowed_labels),
            },
        }
