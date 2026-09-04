"""Qwen2.5-VL adapter with explicit LLM-boundary visual-token accounting."""

from __future__ import annotations

import re
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image

from labbs2026.adapters.base import PredictionResult, VLMAdapter, VisualStageMetadata


MEASUREMENT_BOUNDARY = (
    "Qwen2.5-VL Vision Encoder output after spatial merger, matched to "
    "image-token positions in the language-model input"
)


def visual_counts_from_grid(
    grid_thw: tuple[int, int, int], spatial_merge_size: int
) -> tuple[int, int]:
    """Return pre-merge patch count and post-merge LLM visual positions."""

    if len(grid_thw) != 3 or any(value <= 0 for value in grid_thw):
        raise ValueError("image_grid_thw must contain three positive integers")
    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    premerge = grid_thw[0] * grid_thw[1] * grid_thw[2]
    merge_area = spatial_merge_size**2
    if premerge % merge_area:
        raise ValueError("image grid is not divisible by the spatial merge area")
    return premerge, premerge // merge_area


def parse_ab(raw_output: str) -> tuple[str | None, str]:
    """Parse only an exact forced-choice label; retain all other text as invalid."""

    normalized = raw_output.strip().upper()
    if re.fullmatch(r"[AB]", normalized):
        return normalized, "PARSED"
    return None, "PARSER_FAILURE"


class Qwen25VLAdapter(VLMAdapter):
    """Pinned primary-backbone adapter; imports model libraries lazily."""

    def __init__(
        self,
        *,
        model_id: str,
        revision: str,
        processor_revision: str,
        cache_dir: Path,
        device: str,
        dtype: str,
        attention_implementation: str,
        use_fast_processor: bool,
        max_new_tokens: int,
    ) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("model revision must be an immutable 40-character Git SHA")
        if not re.fullmatch(r"[0-9a-f]{40}", processor_revision):
            raise ValueError("processor revision must be an immutable 40-character Git SHA")
        self.model_id = model_id
        self.revision = revision
        self.processor_revision = processor_revision
        self.cache_dir = cache_dir
        self.device = device
        self.dtype_name = dtype
        self.attention_implementation = attention_implementation
        self.use_fast_processor = use_fast_processor
        self.max_new_tokens = max_new_tokens
        self._processor: Any | None = None
        self._model: Any | None = None
        self._runtime_vision_output_count: int | None = None
        self.model_load_seconds: float | None = None

    @property
    def processor(self) -> Any:
        if self._processor is None:
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
            import torch
            from transformers import Qwen2_5_VLForConditionalGeneration

            dtype_by_name = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }
            if self.dtype_name not in dtype_by_name:
                raise ValueError(f"unsupported dtype: {self.dtype_name}")
            started = time.perf_counter()
            self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
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

    def _prepare(self, image_path: Path, prompt: str) -> tuple[Any, Image.Image, float]:
        import torch

        image = Image.open(image_path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        started = time.perf_counter()
        inputs = self.processor(
            text=[text],
            images=[image],
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.device)
        if inputs["image_grid_thw"].shape != torch.Size([1, 3]):
            raise ValueError("Step 3 adapter expects exactly one image per prediction")
        return inputs, image, time.perf_counter() - started

    def _metadata_from_inputs(
        self, inputs: Any, image: Image.Image, runtime_count: int | None = None
    ) -> VisualStageMetadata:
        grid = tuple(int(value) for value in inputs["image_grid_thw"][0].tolist())
        processor = self.processor.image_processor
        patch_size = int(processor.patch_size)
        temporal_patch_size = int(processor.temporal_patch_size)
        merge_size = int(processor.merge_size)
        premerge, llm_count = visual_counts_from_grid(grid, merge_size)
        image_token_id = int(self.processor.image_token_id)
        prompt_count = int((inputs["input_ids"] == image_token_id).sum().item())
        if prompt_count != llm_count:
            raise RuntimeError(
                f"visual-token mismatch: grid={llm_count}, prompt={prompt_count}"
            )
        if runtime_count is not None and runtime_count != llm_count:
            raise RuntimeError(
                f"visual-token mismatch: grid={llm_count}, runtime={runtime_count}"
            )
        return VisualStageMetadata(
            original_image_shape=(image.height, image.width),
            preprocessed_image_shape=(grid[1] * patch_size, grid[2] * patch_size),
            image_grid_thw=grid,
            patch_size=patch_size,
            temporal_patch_size=temporal_patch_size,
            spatial_merge_size=merge_size,
            premerge_patch_count=premerge,
            llm_visual_token_count=llm_count,
            input_image_token_count=prompt_count,
            runtime_vision_output_count=runtime_count,
            measurement_boundary=MEASUREMENT_BOUNDARY,
            processor_class=type(processor).__name__,
        )

    def get_visual_stage_metadata(self, image_path: Path, prompt: str) -> VisualStageMetadata:
        inputs, image, _ = self._prepare(image_path, prompt)
        return self._metadata_from_inputs(inputs, image)

    def get_preprocessed_image_shape(self, image_path: Path, prompt: str) -> tuple[int, int]:
        return self.get_visual_stage_metadata(image_path, prompt).preprocessed_image_shape

    def get_visual_token_count(self, image_path: Path, prompt: str) -> int:
        return self.get_visual_stage_metadata(image_path, prompt).llm_visual_token_count

    def predict(self, image_path: Path, prompt: str) -> PredictionResult:
        import torch

        inputs, image, preprocess_seconds = self._prepare(image_path, prompt)
        captured: dict[str, int] = {}

        def capture_vision_count(_module: Any, _args: Any, output: Any) -> None:
            captured["count"] = int(output.shape[0])

        hook = self.model.model.visual.register_forward_hook(capture_vision_count)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                generated = self.model.generate(
                    **inputs,
                    do_sample=False,
                    max_new_tokens=self.max_new_tokens,
                )
        finally:
            hook.remove()
        generation_seconds = time.perf_counter() - started
        generated_only = generated[:, inputs["input_ids"].shape[1] :]
        raw_output = self.processor.batch_decode(
            generated_only,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        parsed, parse_status = parse_ab(raw_output)
        runtime_count = captured.get("count")
        if runtime_count is None:
            raise RuntimeError("Vision Encoder output count was not observed during generation")
        metadata = self._metadata_from_inputs(inputs, image, runtime_count=runtime_count)
        self._runtime_vision_output_count = runtime_count
        return PredictionResult(
            raw_output=raw_output,
            parsed_output=parsed,
            parse_status=parse_status,
            metadata=replace(metadata, runtime_vision_output_count=runtime_count),
            preprocess_seconds=preprocess_seconds,
            generation_seconds=generation_seconds,
        )

    def architecture_record(self) -> dict[str, Any]:
        processor = self.processor.image_processor
        return {
            "model_id": self.model_id,
            "model_revision": self.revision,
            "processor_revision": self.processor_revision,
            "processor_class": type(processor).__name__,
            "use_fast_processor": self.use_fast_processor,
            "patch_size": int(processor.patch_size),
            "temporal_patch_size": int(processor.temporal_patch_size),
            "spatial_merge_size": int(processor.merge_size),
            "min_pixels": int(processor.size["shortest_edge"]),
            "max_pixels": int(processor.size["longest_edge"]),
            "measurement_boundary": MEASUREMENT_BOUNDARY,
            "count_formula": "prod(image_grid_thw) / spatial_merge_size^2",
            "device": self.device,
            "dtype": self.dtype_name,
            "attention_implementation": self.attention_implementation,
        }
