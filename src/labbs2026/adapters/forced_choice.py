"""Backbone-independent one-token A/B decision contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from labbs2026.adapters.base import PredictionResult


CANONICAL_LABEL_CONSTRAINT = "canonical_label_token_constraint_v1"


@dataclass(frozen=True)
class DecisionLogitResult:
    """Raw A/B decision logits captured before generation-time processors."""

    prediction: PredictionResult
    logit_a: float
    logit_b: float
    direct_forward_logit_a: float | None
    direct_forward_logit_b: float | None
    generate_direct_exact: bool | None


def parse_ab(raw_output: str) -> tuple[str | None, str]:
    """Parse only an exact forced-choice label; retain all other text as invalid."""

    normalized = raw_output.strip().upper()
    if re.fullmatch(r"[AB]", normalized):
        return normalized, "PARSED"
    return None, "PARSER_FAILURE"


def inspect_canonical_label_contract(
    tokenizer: Any, prefix_text: str, labels: tuple[str, ...] = ("A", "B")
) -> dict[str, Any]:
    """Resolve canonical labels at the actual chat-generation text boundary."""

    if labels != ("A", "B"):
        raise ValueError("the registered Stage 0 labels must be exactly A and B")
    prefix_ids = tokenizer.encode(prefix_text, add_special_tokens=False)
    mapping: dict[str, int] = {}
    forms: dict[str, dict[str, Any]] = {}
    for form in ("A", "B", " A", " B", "A\n", "B\n"):
        isolated = tokenizer.encode(form, add_special_tokens=False)
        appended = tokenizer.encode(prefix_text + form, add_special_tokens=False)
        prefix_stable = appended[: len(prefix_ids)] == prefix_ids
        suffix = appended[len(prefix_ids) :] if prefix_stable else None
        forms[repr(form)] = {
            "isolated_token_ids": [int(value) for value in isolated],
            "appended_prefix_stable": prefix_stable,
            "appended_suffix_token_ids": (
                [int(value) for value in suffix] if suffix is not None else None
            ),
            "decoded_isolated": tokenizer.decode(
                isolated,
                skip_special_tokens=False,
                clean_up_tokenization_spaces=False,
            ),
        }
    for label in labels:
        record = forms[repr(label)]
        token_ids = record["isolated_token_ids"]
        if (
            len(token_ids) != 1
            or not record["appended_prefix_stable"]
            or record["appended_suffix_token_ids"] != token_ids
            or record["decoded_isolated"] != label
        ):
            raise RuntimeError(
                f"canonical label {label!r} is not one exact token at the generation boundary"
            )
        mapping[label] = token_ids[0]
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("canonical labels do not map to distinct token IDs")
    return {
        "contract_version": CANONICAL_LABEL_CONSTRAINT,
        "labels": list(labels),
        "label_token_ids": mapping,
        "allowed_first_token_ids": [mapping[label] for label in labels],
        "prefix_token_count": len(prefix_ids),
        "prefix_tail_token_ids": [int(value) for value in prefix_ids[-20:]],
        "forms": forms,
        "valid": True,
    }


def canonical_label_from_generated_tokens(
    tokenizer: Any, generated_token_ids: tuple[int, ...], label_token_ids: dict[str, int]
) -> tuple[str, str | None, str, bool]:
    """Decode one constrained token and fail closed on any non-canonical output."""

    raw_output = tokenizer.decode(
        list(generated_token_ids),
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    reverse = {int(token_id): label for label, token_id in label_token_ids.items()}
    token_label = (
        reverse.get(int(generated_token_ids[0]))
        if len(generated_token_ids) == 1
        else None
    )
    parsed, parse_status = parse_ab(raw_output)
    conforms = token_label is not None and parsed == token_label and parse_status == "PARSED"
    return raw_output, parsed if conforms else None, (
        "PARSED" if conforms else "OUTPUT_CONTRACT_VIOLATION"
    ), conforms
