"""Device-placement guard: catches the GPU-only failure without needing a GPU."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from labbs2026.region_ocr.execute import _assert_same_device


class FakeModel:
    def __init__(self, device="cpu"):
        self._p = torch.nn.Parameter(torch.zeros(1, device=device))

    def parameters(self):
        yield self._p


def test_matching_devices_pass() -> None:
    model = FakeModel()
    assert _assert_same_device(model, {"a": torch.zeros(2), "b": torch.ones(3)}) is None


def test_non_tensor_entries_are_ignored() -> None:
    _assert_same_device(FakeModel(), {"a": torch.zeros(2), "note": "text", "n": 5})


def test_mismatch_raises_with_the_offending_names() -> None:
    """The real failure surfaced deep inside a convolution; this names the tensor."""
    model = FakeModel()

    class Elsewhere(torch.Tensor):
        pass

    wrong = torch.zeros(2)
    object.__setattr__(model, "_p", torch.nn.Parameter(torch.zeros(1)))
    # Simulate a device difference by comparing against a meta-device tensor.
    meta = torch.zeros(2, device="meta")
    with pytest.raises(RuntimeError, match="tensors not on"):
        _assert_same_device(model, {"pixel_values": meta, "input_ids": wrong})
