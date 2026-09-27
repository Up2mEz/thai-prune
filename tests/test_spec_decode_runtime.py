"""`spec_decode.runtime` on a random-weight Qwen3-VL, CPU fp32. No pinned weights."""

import torch

from labbs2026.spec_decode import runtime
from labbs2026.spec_decode.identity import compare_outputs, truncate_new_tokens

from test_spec_decode_identity import _toy_qwen3vl

MAX_NEW = 30


def _inputs(seed: int):
    g = torch.Generator().manual_seed(seed)
    t, h, w = 1, 8, 12
    text = torch.randint(0, 400, (16,), generator=g)
    text = torch.cat([text, text[:8]])
    ids = torch.cat([torch.randint(0, 400, (4,), generator=g), torch.tensor([502]),
                     torch.full((t * h * w // 4,), 500), torch.tensor([503]), text])[None]
    return {
        "input_ids": ids, "attention_mask": torch.ones_like(ids),
        "pixel_values": torch.randn(t * h * w, 3 * 2 * 16 * 16, generator=g),
        "image_grid_thw": torch.tensor([[t, h, w]]), "mm_token_type_ids": (ids == 500).long(),
    }


def _arm(model, inputs, extra):
    return runtime.run_arm(model, inputs, {"min_new_tokens": MAX_NEW, "eos_token_id": 511,
                                           "pad_token_id": 511, **extra},
                           max_new_tokens=MAX_NEW, device="cpu")


def test_run_arm_records_ids_counts_and_identity():
    model = _toy_qwen3vl()
    inputs = _inputs(0)
    ref = _arm(model, inputs, {})
    pld = _arm(model, inputs, {"prompt_lookup_num_tokens": 5, "max_matching_ngram_size": 2})
    assert ref["generated_tokens"] == MAX_NEW and ref["reached_max_new_tokens"]
    assert ref["target_forwards"] == MAX_NEW
    assert pld["target_forwards"] < ref["target_forwards"]
    assert ref["prompt_tokens"] == inputs["input_ids"].shape[-1]
    assert ref["seconds_generate"] > 0 and ref["peak_bytes"] is None
    result = compare_outputs(truncate_new_tokens(ref["new_token_ids"], 0, MAX_NEW),
                             truncate_new_tokens(pld["new_token_ids"], 0, MAX_NEW))
    assert result.identical


def test_ref_margin_reproduces_greedy_choice():
    """Teacher-forcing REF's own prefix must give back REF's token at every checked
    position, with a non-negative margin; otherwise the margin would describe a
    different sequence than the one generated."""
    model = _toy_qwen3vl()
    inputs = _inputs(1)
    ref = _arm(model, inputs, {})["new_token_ids"]
    for position in (0, 7, MAX_NEW - 1):
        out = runtime.ref_margin_at(model, inputs, ref, position)
        assert out["teacher_forced_argmax"] == out["ref_token"] == ref[position]
        assert out["margin_logits"] >= 0


def _chat_shaped_inputs():
    """Like Qwen's chat template: "\\n" before <|vision_start|>, prompt ending in "\\n"."""
    nl, t, h, w = 7, 1, 8, 12
    ids = torch.tensor([[1, 2, nl, 502] + [500] * (t * h * w // 4) + [503, 30, 31, 32, 3, nl]])
    g = torch.Generator().manual_seed(3)
    return {
        "input_ids": ids, "attention_mask": torch.ones_like(ids),
        "pixel_values": torch.randn(t * h * w, 3 * 2 * 16 * 16, generator=g),
        "image_grid_thw": torch.tensor([[t, h, w]]), "mm_token_type_ids": (ids == 500).long(),
    }


def test_unfiltered_prompt_lookup_drafts_image_tokens_and_crashes():
    """The Kaggle smoke failure, reproduced: without the filter, the draft after the
    matching "\\n" is <|vision_start|><|image_pad|>..., which breaks verification."""
    model = _toy_qwen3vl()
    inputs = _chat_shaped_inputs()
    try:
        with torch.no_grad():
            model.generate(**inputs, do_sample=False, max_new_tokens=5, prompt_lookup_num_tokens=10,
                           eos_token_id=511, pad_token_id=511)
    except ValueError as exc:
        assert "Image features and image tokens do not match" in str(exc)
    else:
        raise AssertionError("expected the unfiltered draft to fail verification")


def test_filtered_prompt_lookup_matches_ref_on_chat_shaped_prompt():
    model = _toy_qwen3vl()
    assert runtime.multimodal_token_ids(model) == [500, 501, 502, 503]
    inputs = _chat_shaped_inputs()
    ref = _arm(model, inputs, {})
    for k in (5, 10):
        pld = _arm(model, inputs, {"prompt_lookup_num_tokens": k, "max_matching_ngram_size": 2})
        result = compare_outputs(truncate_new_tokens(ref["new_token_ids"], 0, MAX_NEW),
                                 truncate_new_tokens(pld["new_token_ids"], 0, MAX_NEW))
        assert result.identical, (k, result)


def test_drafts_without_restores_the_library():
    from transformers.generation.candidate_generator import PromptLookupCandidateGenerator

    before = PromptLookupCandidateGenerator.get_candidates
    with runtime.drafts_without([500]):
        assert PromptLookupCandidateGenerator.get_candidates is not before
    assert PromptLookupCandidateGenerator.get_candidates is before


def test_seconds_to_first_token_positive():
    model = _toy_qwen3vl()
    assert runtime.seconds_to_first_token(model, _inputs(2), device="cpu") > 0
