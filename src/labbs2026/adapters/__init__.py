"""Backend-neutral VLM adapter interfaces and implementations."""

from labbs2026.adapters.base import PredictionResult, VLMAdapter, VisualStageMetadata
from labbs2026.adapters.qwen25_vl import DecisionLogitResult

__all__ = ["DecisionLogitResult", "PredictionResult", "VLMAdapter", "VisualStageMetadata"]
