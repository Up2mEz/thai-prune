"""`remedies.pai` on a random-weight Qwen3-VL, CPU fp32. No pinned weights."""

import pytest
import torch

from labbs2026.remedies import pai

from test_remedies_contrastive import _image_inputs
from test_spec_decode_identity import _toy_qwen3vl

MAX_NEW = 20


def _eager_toy():
    model = _toy_qwen3vl()
    model.set_attn_implementation("eager")
    return model


def _generate(model, inputs, **extra):
    with torch.no_grad():
        out = model.generate(**inputs, do_sample=False, max_new_tokens=MAX_NEW, min_new_tokens=MAX_NEW,
                             eos_token_id=511, pad_token_id=511, **extra)
    return out[0, inputs["input_ids"].shape[-1]:].tolist()


def test_amplify_touches_only_image_columns():
    scores = torch.tensor([[[[-2.0, 1.0, -0.5, 3.0]]]])
    out = pai.amplify(scores, torch.tensor([1, 2]), 0.5)
    assert torch.allclose(out, torch.tensor([[[[-2.0, 1.5, -0.25, 3.0]]]]))
    assert torch.equal(pai.amplify(scores, torch.tensor([1]), 0.0), scores)


def test_zero_alpha_equals_eager_generate():
    model = _eager_toy()
    inputs = _image_inputs(0)
    reference = _generate(model, inputs)
    with pai.amplified_image_attention(model, inputs["input_ids"], image_token_id=500,
                                       layers=range(4), alpha=0.0):
        assert _generate(model, inputs) == reference
    assert model.model.language_model.config._attn_implementation == "eager"


def _image_attention_mass(model, inputs, layer, **pai_kwargs):
    """Attention mass the first decode-step query puts on image keys, in `layer`."""
    captured = {}
    attn = model.model.language_model.layers[layer].self_attn

    def hook(_module, _args, output):
        captured.setdefault("w", []).append(output[1])

    handle = attn.register_forward_hook(hook)
    try:
        if pai_kwargs:
            with pai.amplified_image_attention(model, inputs["input_ids"], image_token_id=500, **pai_kwargs):
                _generate(model, inputs)
        else:
            _generate(model, inputs)
    finally:
        handle.remove()
    decode = captured["w"][1]  # [0] is prefill, [1] the first single-token step
    keys = (inputs["input_ids"][0] == 500).nonzero().flatten()
    return float(decode[0, :, -1, keys].sum(-1).mean()), captured["w"][0]


def test_positive_alpha_raises_image_attention_only_in_chosen_layers_and_decode_steps():
    model = _eager_toy()
    inputs = _image_inputs(1)
    base_mass, base_prefill = _image_attention_mass(model, inputs, layer=2)
    amp_mass, amp_prefill = _image_attention_mass(model, inputs, layer=2, layers=[2], alpha=1.0)
    other_mass, _ = _image_attention_mass(model, inputs, layer=1, layers=[2], alpha=1.0)
    base_other, _ = _image_attention_mass(model, inputs, layer=1)
    assert amp_mass > base_mass
    assert torch.allclose(amp_prefill, base_prefill)   # decode_only: prompt untouched
    # layer 1 is not amplified; its first decode step sees the same prompt cache
    assert other_mass == pytest.approx(base_other, abs=1e-6)


def test_bad_arguments():
    model = _eager_toy()
    ids = _image_inputs(0)["input_ids"]
    with pytest.raises(ValueError):
        with pai.amplified_image_attention(model, ids, image_token_id=500, layers=[99], alpha=1.0):
            pass
    with pytest.raises(ValueError):
        with pai.amplified_image_attention(model, ids, image_token_id=500, layers=[0], alpha=-1.0):
            pass
