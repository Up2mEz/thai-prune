"""The T2 scoring window never collapses to an empty string."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.orthography import Site, window_variants
from labbs2026.thai_marks.runtime import scoring_window_token

MAI_THO = "้"


def _always_clean(_: int) -> bool:
    return True


def test_a_final_mark_that_starts_its_own_token_gets_its_base_in_the_window() -> None:
    # "ข้า" … ending in a mark tokenized alone, as on 10 sites of the 2026-09-27 run.
    text = "ไปก่อน" + MAI_THO
    offsets = [(0, 2), (2, 6), (6, 7)]  # the final ้ is its own token
    site = Site(kind="TONE", index=6, reference=MAI_THO)
    k = scoring_window_token(offsets, site.index, _always_clean, len(text))
    assert offsets[k][0] < site.index
    windows = dict(window_variants(text, site, offsets[k][0], 8))
    assert all(windows.values()), windows  # "none" is no longer empty


def test_a_site_inside_a_token_keeps_that_token() -> None:
    offsets = [(0, 3), (3, 7)]
    assert scoring_window_token(offsets, 5, _always_clean, 7) == 1


def test_unclean_byte_boundaries_step_back() -> None:
    offsets = [(0, 3), (3, 5), (5, 8)]
    assert scoring_window_token(offsets, 6, lambda j: j != 2, 8) == 1


def test_an_uncovered_character_is_an_error() -> None:
    with pytest.raises(RuntimeError):
        scoring_window_token([(0, 2)], 5, _always_clean, 6)


def test_a_mark_starting_its_token_mid_text_keeps_the_registered_window() -> None:
    offsets = [(0, 2), (2, 3), (3, 6)]  # a mark at 2 starts its own token, text goes on
    assert scoring_window_token(offsets, 2, _always_clean, 6) == 1


# --- scoring conventions -------------------------------------------------------

from labbs2026.thai_marks.analysis import oracle_by_convention, variant_scores  # noqa: E402


def _variant(ids, logps):
    def entry():
        return {"logprob": sum(logps), "tokens": len(ids), "token_ids": list(ids),
                "token_logprobs": list(logps)}
    return {"image": entry(), "no_image": entry()}


def _site():
    # Shared first token 7; at the decision token the reference (้) wins, but the
    # rare variant (๊) collects easy follow-on tokens and wins the summed score.
    return {"kind": "TONE", "index": 0, "reference": "้", "variants": {
        "้": _variant([7, 1, 2], [-0.1, -1.0, -3.0]),
        "๊": _variant([7, 5, 6, 8], [-0.1, -2.5, -0.2, -0.1]),
    }}


def test_conventions_can_disagree_and_first_divergent_scores_the_decision() -> None:
    site = _site()
    assert max(variant_scores(site, "image", "sum").items(), key=lambda kv: kv[1])[0] == "๊"
    first = variant_scores(site, "image", "first_divergent")
    assert first == {"้": -1.0, "๊": -2.5}


def test_records_without_per_token_data_fall_back_to_sum_only() -> None:
    site = _site()
    for v in site["variants"].values():
        for c in v.values():
            del c["token_ids"], c["token_logprobs"]
    assert variant_scores(site, "image", "sum") is not None
    assert variant_scores(site, "image", "first_divergent") is None


def test_oracle_by_convention_counts_sites_per_kind() -> None:
    result = oracle_by_convention([{"sites": [_site()]}])
    assert result["sum"]["TONE"]["oracle"] == 0.0
    assert result["first_divergent"]["TONE"]["oracle"] == 1.0
    assert result["first_divergent"]["TONE"]["sites"] == 1


# --- in-context tokenization of variants -----------------------------------------

from labbs2026.thai_marks.runtime import continuation_split  # noqa: E402


def _merging_tokenizer():
    """Character tokens, except "้ง" merges -- but only when it starts a chunk."""
    def encode(text: str) -> list[int]:
        out, i = [], 0
        while i < len(text):
            if i == 0 and text.startswith("้ง"):
                out.append(9000); i += 2
            else:
                out.append(ord(text[i])); i += 1
        return out

    def decode(ids: list[int]) -> str:
        return "".join("้ง" if t == 9000 else chr(t) for t in ids)
    return encode, decode


def test_variants_are_scored_with_their_in_context_tokens_not_standalone_ones() -> None:
    enc, dec = _merging_tokenizer()
    prefix = "ตั"
    windows = {"้": "้งแต่", "none": "งแต่"}
    assert enc(windows["้"])[0] == 9000  # standalone: the never-seen merged token
    shared, targets = continuation_split(enc, dec, prefix, windows, own=enc(prefix))
    assert dec(shared) == "ตั"
    assert targets["้"] == [ord(c) for c in "้งแต่"]  # in context: canonical characters
