"""Qwen2.5-VL adapter with explicit LLM-boundary visual-token accounting."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PIL import Image

from labbs2026.adapters.base import PredictionResult, VLMAdapter, VisualStageMetadata


MEASUREMENT_BOUNDARY = (
    "Qwen2.5-VL Vision Encoder output after spatial merger, matched to "
    "image-token positions in the language-model input"
)
CANONICAL_LABEL_CONSTRAINT = "canonical_label_token_constraint_v1"


@dataclass(frozen=True)
class DecisionLogitResult:
    """Raw A/B decision logits captured before generation-time processors."""

    prediction: PredictionResult
    logit_a: float
    logit_b: float
    direct_forward_logit_a: float | None
    direct_forward_logit_b: float | None
    generate_direct_exact: bool | None


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


def inspect_canonical_label_contract(
    tokenizer: Any, prefix_text: str, labels: tuple[str, ...] = ("A", "B")
) -> dict[str, Any]:
    """Resolve canonical labels at the actual chat-generation text boundary."""

    if labels != ("A", "B"):
        raise ValueError("the registered Stage 0 labels must be exactly A and B")
    prefix_ids = tokenizer.encode(prefix_text, add_special_tokens=False)
    mapping: dict[str, int] = {}
    forms: dict[str, dict[str, Any]] = {}
    for form in ("A", "B", " A", " B", "A\n", "B\n"):
        isolated = tokenizer.encode(form, add_special_tokens=False)
        appended = tokenizer.encode(prefix_text + form, add_special_tokens=False)
        prefix_stable = appended[: len(prefix_ids)] == prefix_ids
        suffix = appended[len(prefix_ids) :] if prefix_stable else None
        forms[repr(form)] = {
            "isolated_token_ids": [int(value) for value in isolated],
            "appended_prefix_stable": prefix_stable,
            "appended_suffix_token_ids": (
                [int(value) for value in suffix] if suffix is not None else None
            ),
            "decoded_isolated": tokenizer.decode(
                isolated,
                skip_special_tokens=False,
                clean_up_tokenization_spaces=False,
            ),
        }
    for label in labels:
        record = forms[repr(label)]
        token_ids = record["isolated_token_ids"]
        if (
            len(token_ids) != 1
            or not record["appended_prefix_stable"]
            or record["appended_suffix_token_ids"] != token_ids
            or record["decoded_isolated"] != label
        ):
            raise RuntimeError(
                f"canonical label {label!r} is not one exact token at the generation boundary"
            )
        mapping[label] = token_ids[0]
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("canonical labels do not map to distinct token IDs")
    return {
        "contract_version": CANONICAL_LABEL_CONSTRAINT,
        "labels": list(labels),
        "label_token_ids": mapping,
        "allowed_first_token_ids": [mapping[label] for label in labels],
        "prefix_token_count": len(prefix_ids),
        "prefix_tail_token_ids": [int(value) for value in prefix_ids[-20:]],
        "forms": forms,
        "valid": True,
    }


def canonical_label_from_generated_tokens(
    tokenizer: Any, generated_token_ids: tuple[int, ...], label_token_ids: dict[str, int]
) -> tuple[str, str | None, str, bool]:
    """Decode one constrained token and fail closed on any non-canonical output."""

    raw_output = tokenizer.decode(
        list(generated_token_ids),
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    reverse = {int(token_id): label for label, token_id in label_token_ids.items()}
    token_label = (
        reverse.get(int(generated_token_ids[0]))
        if len(generated_token_ids) == 1
        else None
    )
    parsed, parse_status = parse_ab(raw_output)
    conforms = token_label is not None and parsed == token_label and parse_status == "PARSED"
    return raw_output, parsed if conforms else None, (
        "PARSED" if conforms else "OUTPUT_CONTRACT_VIOLATION"
    ), conforms


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
        do_sample: bool = False,
        output_contract_mode: str = "free_generation",
        allowed_labels: tuple[str, ...] = ("A", "B"),
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
        self.do_sample = do_sample
        self.output_contract_mode = output_contract_mode
        self.allowed_labels = allowed_labels
        if self.output_contract_mode == CANONICAL_LABEL_CONSTRAINT:
            if self.max_new_tokens != 1 or self.do_sample:
                raise ValueError(
                    "canonical label constraint requires do_sample=false and max_new_tokens=1"
                )
        elif self.output_contract_mode != "free_generation":
            raise ValueError(f"unsupported output contract: {self.output_contract_mode}")
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

    def _chat_prefix(self, prompt: str) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    def inspect_output_contract(self, prompt: str) -> dict[str, Any]:
        if self.output_contract_mode != CANONICAL_LABEL_CONSTRAINT:
            return {
                "contract_version": "free_generation",
                "valid": True,
            }
        result = inspect_canonical_label_contract(
            self.processor.tokenizer, self._chat_prefix(prompt), self.allowed_labels
        )
        return {
            **result,
            "tokenizer_class": type(self.processor.tokenizer).__name__,
            "tokenizer_name_or_path": self.processor.tokenizer.name_or_path,
            "tokenizer_revision": self.processor_revision,
        }

    def _prepare(
        self, image_path: Path, prompt: str
    ) -> tuple[Any, Image.Image, float, str]:
        import torch

        image = Image.open(image_path).convert("RGB")
        text = self._chat_prefix(prompt)
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
        return inputs, image, time.perf_counter() - started, text

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
        inputs, image, _, _ = self._prepare(image_path, prompt)
        return self._metadata_from_inputs(inputs, image)

    def get_preprocessed_image_shape(self, image_path: Path, prompt: str) -> tuple[int, int]:
        return self.get_visual_stage_metadata(image_path, prompt).preprocessed_image_shape

    def get_visual_token_count(self, image_path: Path, prompt: str) -> int:
        return self.get_visual_stage_metadata(image_path, prompt).llm_visual_token_count

    def predict(self, image_path: Path, prompt: str) -> PredictionResult:
        import torch

        inputs, image, preprocess_seconds, prefix_text = self._prepare(image_path, prompt)
        captured: dict[str, int] = {}
        contract = self.inspect_output_contract(prompt)

        def capture_vision_count(_module: Any, _args: Any, output: Any) -> None:
            captured["count"] = int(output.shape[0])

        hook = self.model.model.visual.register_forward_hook(capture_vision_count)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                generation_kwargs: dict[str, Any] = {
                    "do_sample": self.do_sample,
                    "max_new_tokens": self.max_new_tokens,
                }
                if self.output_contract_mode == CANONICAL_LABEL_CONSTRAINT:
                    allowed = tuple(int(value) for value in contract["allowed_first_token_ids"])

                    def allowed_tokens(_batch_id: int, _input_ids: Any) -> list[int]:
                        return list(allowed)

                    generation_kwargs.update(
                        {
                            "min_new_tokens": 1,
                            "prefix_allowed_tokens_fn": allowed_tokens,
                        }
                    )
                generated = self.model.generate(
                    **inputs,
                    **generation_kwargs,
                )
        finally:
            hook.remove()
        generation_seconds = time.perf_counter() - started
        generated_only = generated[:, inputs["input_ids"].shape[1] :]
        generated_token_ids = tuple(int(value) for value in generated_only[0].tolist())
        if self.output_contract_mode == CANONICAL_LABEL_CONSTRAINT:
            raw_output, parsed, parse_status, conforms = canonical_label_from_generated_tokens(
                self.processor.tokenizer,
                generated_token_ids,
                contract["label_token_ids"],
            )
        else:
            raw_output = self.processor.batch_decode(
                generated_only,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]
            parsed, parse_status = parse_ab(raw_output)
            conforms = None
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
            generated_token_ids=generated_token_ids,
            output_contract_conformance=conforms,
            output_contract=contract,
            resolved_generation_config={
                "do_sample": self.do_sample,
                "max_new_tokens": self.max_new_tokens,
                "min_new_tokens": (
                    1 if self.output_contract_mode == CANONICAL_LABEL_CONSTRAINT else None
                ),
                "output_contract_mode": self.output_contract_mode,
            },
        )

    def predict_with_decision_logits(
        self,
        image_path: Path,
        prompt: str,
        *,
        verify_direct_forward: bool = False,
    ) -> DecisionLogitResult:
        """Predict one registered label and expose its raw pre-processor A/B logits.

        ``generate(..., output_logits=True)`` returns the model logits before the
        generation logits processors are applied.  The optional direct forward
        pass is an engineering cross-check at the same final prompt position; it
        is deliberately used only by the smoke test.
        """

        import torch

        if self.output_contract_mode != CANONICAL_LABEL_CONSTRAINT:
            raise RuntimeError("decision-logit capture requires the canonical A/B contract")
        inputs, image, preprocess_seconds, _prefix_text = self._prepare(image_path, prompt)
        contract = self.inspect_output_contract(prompt)
        label_token_ids = {
            label: int(token_id) for label, token_id in contract["label_token_ids"].items()
        }
        captured: dict[str, int] = {}

        def capture_vision_count(_module: Any, _args: Any, output: Any) -> None:
            captured["count"] = int(output.shape[0])

        allowed = tuple(int(value) for value in contract["allowed_first_token_ids"])

        def allowed_tokens(_batch_id: int, _input_ids: Any) -> list[int]:
            return list(allowed)

        direct_a: float | None = None
        direct_b: float | None = None
        hook = self.model.model.visual.register_forward_hook(capture_vision_count)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                if verify_direct_forward:
                    direct = self.model(
                        **inputs,
                        use_cache=False,
                        return_dict=True,
                        logits_to_keep=1,
                    ).logits[0, -1].float()
                    direct_a = float(direct[label_token_ids["A"]].item())
                    direct_b = float(direct[label_token_ids["B"]].item())
                generated = self.model.generate(
                    **inputs,
                    do_sample=self.do_sample,
                    max_new_tokens=self.max_new_tokens,
                    min_new_tokens=1,
                    prefix_allowed_tokens_fn=allowed_tokens,
                    return_dict_in_generate=True,
                    output_logits=True,
                )
        finally:
            hook.remove()
        generation_seconds = time.perf_counter() - started
        if len(generated.logits) != 1:
            raise RuntimeError("expected exactly one pre-decision logit tensor")
        next_logits = generated.logits[0][0].float()
        logit_a = float(next_logits[label_token_ids["A"]].item())
        logit_b = float(next_logits[label_token_ids["B"]].item())
        generated_only = generated.sequences[:, inputs["input_ids"].shape[1] :]
        generated_token_ids = tuple(int(value) for value in generated_only[0].tolist())
        raw_output, parsed, parse_status, conforms = canonical_label_from_generated_tokens(
            self.processor.tokenizer,
            generated_token_ids,
            label_token_ids,
        )
        runtime_count = captured.get("count")
        if runtime_count is None:
            raise RuntimeError("Vision Encoder output count was not observed during inference")
        metadata = self._metadata_from_inputs(inputs, image, runtime_count=runtime_count)
        prediction = PredictionResult(
            raw_output=raw_output,
            parsed_output=parsed,
            parse_status=parse_status,
            metadata=replace(metadata, runtime_vision_output_count=runtime_count),
            preprocess_seconds=preprocess_seconds,
            generation_seconds=generation_seconds,
            generated_token_ids=generated_token_ids,
            output_contract_conformance=conforms,
            output_contract=contract,
            resolved_generation_config={
                "do_sample": self.do_sample,
                "max_new_tokens": self.max_new_tokens,
                "min_new_tokens": 1,
                "output_contract_mode": self.output_contract_mode,
                "return_dict_in_generate": True,
                "output_logits": True,
            },
        )
        exact = (
            logit_a == direct_a and logit_b == direct_b
            if verify_direct_forward
            else None
        )
        return DecisionLogitResult(
            prediction=prediction,
            logit_a=logit_a,
            logit_b=logit_b,
            direct_forward_logit_a=direct_a,
            direct_forward_logit_b=direct_b,
            generate_direct_exact=exact,
        )

    def architecture_record(self) -> dict[str, Any]:
        processor = self.processor.image_processor
        return {
            "model_id": self.model_id,
            "model_revision": self.revision,
            "processor_revision": self.processor_revision,
            "tokenizer_revision": self.processor_revision,
            "tokenizer_class": type(self.processor.tokenizer).__name__,
            "processor_class": type(processor).__name__,
            "use_fast_processor": self.use_fast_processor,
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
            "measurement_boundary": MEASUREMENT_BOUNDARY,
            "count_formula": "prod(image_grid_thw) / spatial_merge_size^2",
            "device": self.device,
            "dtype": self.dtype_name,
            "attention_implementation": self.attention_implementation,
            "generation": {
                "do_sample": self.do_sample,
                "max_new_tokens": self.max_new_tokens,
                "output_contract_mode": self.output_contract_mode,
                "allowed_labels": list(self.allowed_labels),
            },
        }
