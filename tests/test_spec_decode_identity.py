import pytest
import torch

from labbs2026.spec_decode.identity import (
    IdentityResult,
    compare_outputs,
    identity_rate,
    truncate_new_tokens,
)


def test_truncate_new_tokens_drops_prompt_and_overshoot():
    # assisted decoding can return one token past the budget
    assert truncate_new_tokens([1, 2, 3, 10, 11, 12, 13], prompt_length=3, max_new_tokens=3) == [10, 11, 12]


def test_truncate_new_tokens_keeps_short_output():
    assert truncate_new_tokens([1, 2, 10], prompt_length=2, max_new_tokens=5) == [10]


def test_truncate_new_tokens_rejects_bad_lengths():
    with pytest.raises(ValueError):
        truncate_new_tokens([1, 2], prompt_length=3, max_new_tokens=1)
    with pytest.raises(ValueError):
        truncate_new_tokens([1, 2], prompt_length=-1, max_new_tokens=1)


def test_compare_outputs_identical():
    assert compare_outputs([5, 6, 7], [5, 6, 7]) == IdentityResult(True, None, 3, 3)


def test_compare_outputs_reports_first_divergence():
    assert compare_outputs([5, 6, 7, 8], [5, 6, 9, 8]) == IdentityResult(False, 2, 4, 4)


def test_compare_outputs_prefix_is_not_identical():
    assert compare_outputs([5, 6, 7], [5, 6]) == IdentityResult(False, 2, 3, 2)
    assert compare_outputs([], [1]) == IdentityResult(False, 0, 0, 1)


def test_identity_rate():
    same = IdentityResult(True, None, 1, 1)
    diff = IdentityResult(False, 0, 1, 1)
    assert identity_rate([same, same, diff, same]) == 0.75
    with pytest.raises(ValueError):
        identity_rate([])


def _toy_qwen3vl():
    from transformers import Qwen3VLConfig, Qwen3VLForConditionalGeneration

    torch.manual_seed(0)
    cfg = Qwen3VLConfig(
        text_config=dict(
            vocab_size=512, hidden_size=64, intermediate_size=128, num_hidden_layers=4,
            num_attention_heads=4, num_key_value_heads=2, head_dim=16,
            rope_scaling={"rope_type": "default", "mrope_section": [2, 3, 3], "mrope_interleaved": True},
            max_position_embeddings=4096,
        ),
        vision_config=dict(
            depth=4, hidden_size=64, intermediate_size=128, num_heads=4, out_hidden_size=64,
            patch_size=16, spatial_merge_size=2, temporal_patch_size=2,
            deepstack_visual_indexes=[1, 2, 3], num_position_embeddings=256,
        ),
        image_token_id=500, video_token_id=501, vision_start_token_id=502, vision_end_token_id=503,
    )
    return Qwen3VLForConditionalGeneration(cfg).eval()


def test_prompt_lookup_matches_greedy_on_random_weight_qwen3vl():
    """Weight-free check that assisted decoding reproduces greedy with an image in
    the prompt (M-RoPE and DeepStack live), and that drafts are actually accepted.
    fp32 on CPU only: says nothing about fp16 on T4."""
    model = _toy_qwen3vl()
    max_new = 40
    for trial in range(3):
        g = torch.Generator().manual_seed(trial)
        t, h, w = 1, 8, 12
        n_img = t * h * w // 4
        text = torch.randint(0, 400, (20,), generator=g)
        text = torch.cat([text, text[:10]])  # repeated n-grams give prompt lookup something to draft
        ids = torch.cat([
            torch.randint(0, 400, (5,), generator=g), torch.tensor([502]),
            torch.full((n_img,), 500), torch.tensor([503]), text,
        ])[None]
        kw = dict(
            input_ids=ids, attention_mask=torch.ones_like(ids),
            pixel_values=torch.randn(t * h * w, 3 * 2 * 16 * 16, generator=g),
            image_grid_thw=torch.tensor([[t, h, w]]), mm_token_type_ids=(ids == 500).long(),
            max_new_tokens=max_new, min_new_tokens=max_new, do_sample=False,
            eos_token_id=511, pad_token_id=511,
        )
        calls = [0]
        hook = model.model.language_model.register_forward_hook(
            lambda *_: calls.__setitem__(0, calls[0] + 1)
        )
        try:
            with torch.no_grad():
                ref = model.generate(**kw)[0].tolist()
                greedy_forwards, calls[0] = calls[0], 0
                cand = model.generate(**kw, prompt_lookup_num_tokens=5)[0].tolist()
                lookup_forwards = calls[0]
        finally:
            hook.remove()
        p = ids.shape[1]
        result = compare_outputs(
            truncate_new_tokens(ref, p, max_new), truncate_new_tokens(cand, p, max_new)
        )
        assert result.identical, result
        assert lookup_forwards < greedy_forwards
