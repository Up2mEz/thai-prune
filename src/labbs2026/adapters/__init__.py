"""Backend-neutral VLM adapter interfaces and implementations."""

from labbs2026.adapters.base import PredictionResult, VLMAdapter, VisualStageMetadata
from labbs2026.adapters.factory import build_adapter, validate_model_config
from labbs2026.adapters.forced_choice import DecisionLogitResult

__all__ = [
    "DecisionLogitResult",
    "PredictionResult",
    "VLMAdapter",
    "VisualStageMetadata",
    "build_adapter",
    "validate_model_config",
]
