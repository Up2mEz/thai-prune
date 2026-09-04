"""Backend-neutral interfaces used by model feasibility and later stages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VisualStageMetadata:
    original_image_shape: tuple[int, int]
    preprocessed_image_shape: tuple[int, int]
    image_grid_thw: tuple[int, int, int]
    patch_size: int
    temporal_patch_size: int
    spatial_merge_size: int
    premerge_patch_count: int
    llm_visual_token_count: int
    input_image_token_count: int
    runtime_vision_output_count: int | None
    measurement_boundary: str
    processor_class: str


@dataclass(frozen=True)
class PredictionResult:
    raw_output: str
    parsed_output: str | None
    parse_status: str
    metadata: VisualStageMetadata
    preprocess_seconds: float
    generation_seconds: float


class VLMAdapter(ABC):
    """Minimal interface required by ARCHITECTURE.md."""

    @abstractmethod
    def predict(self, image_path: Path, prompt: str) -> PredictionResult:
        """Generate one deterministic prediction and retain the raw output."""

    @abstractmethod
    def get_preprocessed_image_shape(self, image_path: Path, prompt: str) -> tuple[int, int]:
        """Return the actual height and width supplied to the visual path."""

    @abstractmethod
    def get_visual_token_count(self, image_path: Path, prompt: str) -> int:
        """Return visual representations at the declared LLM boundary."""

    @abstractmethod
    def get_visual_stage_metadata(self, image_path: Path, prompt: str) -> VisualStageMetadata:
        """Return auditable model-specific preprocessing and token metadata."""

    @abstractmethod
    def architecture_record(self) -> dict[str, Any]:
        """Return pinned model and processor facts used by this adapter."""
