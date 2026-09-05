"""Frozen-candidate-order construction and strict Stage 0 parser."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForcedChoice:
    order_group_id: str
    candidate_a: str
    candidate_b: str
    expected_label: str
    orientation: str
    prompt: str


def parse_choice(raw_output: str) -> tuple[str | None, str]:
    normalized = raw_output.strip().upper()
    if re.fullmatch(r"[AB]", normalized):
        return normalized, "PARSED"
    return None, "PARSER_FAILURE"


def make_forced_choice(
    *,
    pair_id: str,
    condition_id: str,
    displayed_member: str,
    text_a: str,
    text_b: str,
    seed: int,
    prompt_template: str,
) -> ForcedChoice:
    if displayed_member not in {"a", "b"}:
        raise ValueError("displayed_member must be 'a' or 'b'")
    order_group_id = f"{pair_id}|{condition_id}"
    digest = hashlib.sha256(f"{seed}|{order_group_id}".encode("utf-8")).digest()
    reversed_order = bool(digest[0] & 1)
    if reversed_order:
        candidate_a, candidate_b = text_b, text_a
        expected_label = "A" if displayed_member == "b" else "B"
        orientation = "B_THEN_A"
    else:
        candidate_a, candidate_b = text_a, text_b
        expected_label = "A" if displayed_member == "a" else "B"
        orientation = "A_THEN_B"
    prompt = prompt_template.format(candidate_a=candidate_a, candidate_b=candidate_b)
    return ForcedChoice(
        order_group_id=order_group_id,
        candidate_a=candidate_a,
        candidate_b=candidate_b,
        expected_label=expected_label,
        orientation=orientation,
        prompt=prompt,
    )
