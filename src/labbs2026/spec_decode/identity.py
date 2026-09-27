"""Output identity between plain greedy and speculative decoding.

`SPEC_DECODE_S1`'s primary outcome is whether speculative decoding returns the
same token ids as plain greedy. Assisted decoding in `transformers` can emit
one token past `max_new_tokens`, so both sequences are cut to the budget before
comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def truncate_new_tokens(
    token_ids: Sequence[int], prompt_length: int, max_new_tokens: int
) -> list[int]:
    """Return the generated part of `token_ids`, at most `max_new_tokens` long."""
    if prompt_length < 0 or max_new_tokens < 0:
        raise ValueError("prompt_length and max_new_tokens must be non-negative")
    if len(token_ids) < prompt_length:
        raise ValueError("token_ids is shorter than the prompt")
    return list(token_ids[prompt_length : prompt_length + max_new_tokens])


@dataclass(frozen=True)
class IdentityResult:
    identical: bool
    first_divergence: int | None
    reference_length: int
    candidate_length: int


def compare_outputs(reference: Sequence[int], candidate: Sequence[int]) -> IdentityResult:
    """Compare two generated sequences token by token.

    `first_divergence` is the first index where they differ, or the length of the
    shorter one when one is a strict prefix of the other; `None` when identical.
    """
    shared = min(len(reference), len(candidate))
    for i in range(shared):
        if reference[i] != candidate[i]:
            return IdentityResult(False, i, len(reference), len(candidate))
    if len(reference) != len(candidate):
        return IdentityResult(False, shared, len(reference), len(candidate))
    return IdentityResult(True, None, len(reference), len(candidate))


def identity_rate(results: Sequence[IdentityResult]) -> float:
    """Fraction of items whose outputs are identical."""
    if not results:
        raise ValueError("no results")
    return sum(r.identical for r in results) / len(results)
