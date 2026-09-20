"""Stage-resolved timing and memory accounting for one observation.

Latency measured around `generate()` as a single blob cannot answer the
question the efficiency claim needs. Two separate problems:

1. *Code path.* Until now `FULL`/`RR` handed `pixel_values` to `generate()` and
   let it run the vision tower, while pruning ran the tower itself and passed
   `inputs_embeds`. Those are different call graphs, so their wall times were
   never comparable and no cross-family efficiency statement could be made from
   them. The fix is upstream of this module: every family now walks the same
   staged path. This module only exists to time the stages.

2. *Mixture.* Post-encoder pruning cannot reduce vision-tower cost by
   construction, and its language-model saving lands almost entirely in prefill,
   which scales with sequence length, not in decode, which scales with how many
   tokens the model chose to emit. A single total hides both facts, and since
   pruning also changes the output length, totals are confounded by an outcome
   of the intervention.

CUDA is asynchronous, so a timer that does not synchronise measures queue
submission rather than work. Every stage therefore synchronises on entry and
exit; on CPU those calls are skipped and the timings are plain wall clock.

Peak allocation is captured per stage via a reset-and-read pair. That is a
process-wide counter, so stages must not overlap - they do not here, and the
meter enforces it by refusing to nest.
"""

from __future__ import annotations

import time
from typing import Any


def _cuda_ready(device: Any) -> bool:
    try:
        import torch
    except ImportError:  # pragma: no cover - torch is required at runtime
        return False
    return torch.cuda.is_available() and str(device).startswith("cuda")


class CostMeter:
    """Accumulates per-stage seconds and peak bytes for one observation."""

    def __init__(self, device: Any) -> None:
        self.device = device
        self._cuda = _cuda_ready(device)
        self.seconds: dict[str, float] = {}
        self.peak_bytes: dict[str, int] = {}
        self._open: str | None = None

    def _sync(self) -> None:
        if self._cuda:
            import torch

            torch.cuda.synchronize(self.device)

    def stage(self, name: str) -> "_Stage":
        if self._open is not None:
            raise RuntimeError(f"stage {self._open!r} is still open; stages must not nest")
        if name in self.seconds:
            raise RuntimeError(f"stage {name!r} was already measured")
        return _Stage(self, name)

    def record(self) -> dict[str, Any]:
        """Flat record, prefixed so stage keys cannot collide with result keys."""
        out: dict[str, Any] = {f"seconds_{k}": v for k, v in self.seconds.items()}
        out.update({f"peak_bytes_{k}": v for k, v in self.peak_bytes.items()})
        out["seconds_measured_total"] = sum(self.seconds.values())
        out["peak_bytes_observation"] = max(self.peak_bytes.values(), default=0)
        out["memory_measured"] = self._cuda
        return out


class _Stage:
    def __init__(self, meter: CostMeter, name: str) -> None:
        self._meter = meter
        self._name = name

    def __enter__(self) -> "_Stage":
        meter = self._meter
        meter._open = self._name
        meter._sync()
        if meter._cuda:
            import torch

            torch.cuda.reset_peak_memory_stats(meter.device)
        self._started = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        meter = self._meter
        meter._sync()
        meter.seconds[self._name] = time.perf_counter() - self._started
        if meter._cuda:
            import torch

            meter.peak_bytes[self._name] = int(torch.cuda.max_memory_allocated(meter.device))
        meter._open = None


def analytic_compute(*, grid: list[int], merge: int, llm_visual_positions: int,
                     prompt_length: int) -> dict[str, Any]:
    """Size counters that determine cost, independent of hardware noise.

    Reported alongside measured time because wall clock on a shared T4 is not
    reproducible while these are. `vision_patches` is what the encoder must
    process and is identical for every post-encoder condition by construction -
    that invariance is itself a result worth showing, not a defect.
    """
    patches = grid[0] * grid[1] * grid[2]
    return {
        "vision_patches": patches,
        "vision_tokens_after_merge": patches // (merge * merge),
        "llm_prefill_positions": prompt_length,
        "llm_visual_positions": llm_visual_positions,
    }
