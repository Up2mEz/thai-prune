"""`remedies.contrastive` on a random-weight Qwen3-VL, CPU fp32. No pinned weights."""

import math

import numpy as np
import pytest
import torch
from PIL import Image

from labbs2026.remedies.contrastive import (
    Weight,
    contrastive_greedy,
    contrastive_scores,
    noised_image,
)

from test_spec_decode_identity import _toy_qwen3vl

MAX_NEW = 25


def _image_inputs(seed: int, h: int = 8, w: int = 12):
    g = torch.Generator().manual_seed(seed)
    text = torch.randint(0, 400, (12,), generator=g)
    ids = torch.cat([torch.randint(0, 400, (4,), generator=g), torch.tensor([502]),
                     torch.full((h * w // 4,), 500), torch.tensor([503]), text])[None]
    return {
        "input_ids": ids, "attention_mask": torch.ones_like(ids),
        "pixel_values": torch.randn(h * w, 3 * 2 * 16 * 16, generator=g),
        "image_grid_thw": torch.tensor([[1, h, w]]), "mm_token_type_ids": (ids == 500).long(),
    }


def _text_only(inputs):
    """The same prompt with the image block (placeholders and delimiters) removed."""
    ids = inputs["input_ids"][0]
    keep = (inputs["mm_token_type_ids"][0] == 0) & (ids != 502) & (ids != 503)
    ids = ids[keep][None]
    return {"input_ids": ids, "attention_mask": torch.ones_like(ids)}


def _greedy(model, inputs):
    with torch.no_grad():
        out = model.generate(**inputs, do_sample=False, max_new_tokens=MAX_NEW, min_new_tokens=MAX_NEW,
                             eos_token_id=511, pad_token_id=511)
    return out[0, inputs["input_ids"].shape[-1]:].tolist()


@pytest.mark.parametrize("contrast", ["no_image", "other_image"])
@pytest.mark.parametrize("beta", [0.0, 0.1])
def test_zero_weight_reproduces_generate_greedy(contrast, beta):
    """Guards the explicit M-RoPE positions: a contrast stream with no image, or a
    different image grid, must not disturb the real stream."""
    model = _toy_qwen3vl()
    real = _image_inputs(0)
    other = _text_only(real) if contrast == "no_image" else _image_inputs(1, h=12, w=16)
    reference = _greedy(model, real)
    out = contrastive_greedy(model, real, other, weight=Weight("constant", alpha=0.0), beta=beta,
                             max_new_tokens=MAX_NEW, eos_token_ids=[511])
    assert out["new_token_ids"] == reference
    assert out["changed_steps"] == []


def test_positive_weight_is_deterministic_and_reports_changes():
    model = _toy_qwen3vl()
    real = _image_inputs(2)
    contrast = _text_only(real)
    runs = [contrastive_greedy(model, real, contrast, weight=Weight("constant", alpha=3.0), beta=0.0,
                               max_new_tokens=MAX_NEW, eos_token_ids=[511]) for _ in range(2)]
    assert runs[0] == runs[1]
    reference = _greedy(model, real)
    first_change = next((i for i, (a, b) in enumerate(zip(runs[0]["new_token_ids"], reference)) if a != b), None)
    if first_change is not None:
        assert runs[0]["changed_steps"][0] == first_change


def test_contrastive_scores_formula_and_plausibility():
    real = torch.log(torch.tensor([0.6, 0.3, 0.1]))
    contrast = torch.log(torch.tensor([0.7, 0.1, 0.2]))
    s = contrastive_scores(real, contrast, 1.0, 0.0)
    expected = 2 * torch.log(torch.tensor([0.6, 0.3, 0.1])) - torch.log(torch.tensor([0.7, 0.1, 0.2]))
    assert torch.allclose(s, expected, atol=1e-6)
    assert int(torch.argmax(s)) == 1          # the contrast flips the choice
    cut = contrastive_scores(real, contrast, 1.0, 0.6)
    assert torch.isinf(cut[1]) and torch.isinf(cut[2]) and not torch.isinf(cut[0])  # 0.3 < 0.6*0.6
    assert int(torch.argmax(cut)) == 0        # plausibility keeps greedy
    with pytest.raises(ValueError):
        contrastive_scores(real, contrast, 1.0, 1.5)


def test_weights():
    assert Weight("constant", alpha=0.7)(0) == Weight("constant", alpha=0.7)(99) == 0.7
    m = Weight("m3id", lam=0.1, max_weight=5.0)
    assert m(0) == 0.0
    assert m(1) == pytest.approx((1 - math.exp(-0.1)) / math.exp(-0.1))
    assert all(m(t) <= m(t + 1) for t in range(50))
    assert m(1000) == 5.0
    with pytest.raises(ValueError):
        Weight("other")(0)


def test_noised_image_is_deterministic_and_follows_the_schedule():
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(0, 256, (32, 48, 3), dtype=np.uint8), mode="RGB")
    a, b = noised_image(img, step=500, seed=3), noised_image(img, step=500, seed=3)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    assert a.size == img.size
    x0 = np.asarray(img, dtype=float).ravel()
    early = np.asarray(noised_image(img, step=0, seed=3), dtype=float).ravel()
    late = np.asarray(noised_image(img, step=999, seed=3), dtype=float).ravel()
    assert np.corrcoef(x0, early)[0, 1] > 0.99
    assert abs(np.corrcoef(x0, late)[0, 1]) < 0.1
    with pytest.raises(ValueError):
        noised_image(img, step=1000)
