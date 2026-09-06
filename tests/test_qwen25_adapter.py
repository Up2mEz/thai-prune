import pytest

from labbs2026.adapters.qwen25_vl import (
    canonical_label_from_generated_tokens,
    inspect_canonical_label_contract,
    parse_ab,
    visual_counts_from_grid,
)


class _FakeTokenizer:
    def __init__(self, *, ambiguous_a: bool = False) -> None:
        self.ambiguous_a = ambiguous_a
        self.mapping = {
            "A": [32, 198] if ambiguous_a else [32],
            "B": [33],
            " A": [362],
            " B": [425],
            "A\n": [32, 198],
            "B\n": [33, 198],
        }

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        prefix = "chat-prefix\n"
        if text.startswith(prefix):
            suffix = text[len(prefix) :]
            return [900, 198] + self.mapping.get(suffix, [])
        return self.mapping[text]

    def decode(self, ids: list[int], **_kwargs: object) -> str:
        reverse = {
            (32,): "A",
            (33,): "B",
            (362,): " A",
            (425,): " B",
            (32, 198): "A\n",
            (33, 198): "B\n",
        }
        return reverse.get(tuple(ids), "candidate text")


def test_visual_counts_match_qwen_spatial_merge() -> None:
    premerge, llm_count = visual_counts_from_grid((1, 32, 32), 2)

    assert premerge == 1024
    assert llm_count == 256


@pytest.mark.parametrize("grid", [(0, 32, 32), (1, 31, 31)])
def test_visual_counts_reject_invalid_grid(grid: tuple[int, int, int]) -> None:
    with pytest.raises(ValueError):
        visual_counts_from_grid(grid, 2)


@pytest.mark.parametrize(
    ("raw", "parsed", "status"),
    [
        ("A", "A", "PARSED"),
        (" b \n", "B", "PARSED"),
        ("The answer is A", None, "PARSER_FAILURE"),
        ("", None, "PARSER_FAILURE"),
    ],
)
def test_forced_choice_parser_is_strict(
    raw: str, parsed: str | None, status: str
) -> None:
    assert parse_ab(raw) == (parsed, status)


def test_canonical_labels_are_resolved_at_generation_boundary() -> None:
    contract = inspect_canonical_label_contract(_FakeTokenizer(), "chat-prefix\n")

    assert contract["label_token_ids"] == {"A": 32, "B": 33}
    assert contract["forms"][repr(" A")]["isolated_token_ids"] == [362]
    assert contract["forms"][repr("A\n")]["isolated_token_ids"] == [32, 198]


def test_ambiguous_multitoken_canonical_label_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="not one exact token"):
        inspect_canonical_label_contract(
            _FakeTokenizer(ambiguous_a=True), "chat-prefix\n"
        )


@pytest.mark.parametrize(
    ("token_ids", "expected", "status", "conforms"),
    [
        ((32,), "A", "PARSED", True),
        ((33,), "B", "PARSED", True),
        ((32, 198), None, "OUTPUT_CONTRACT_VIOLATION", False),
        ((999,), None, "OUTPUT_CONTRACT_VIOLATION", False),
    ],
)
def test_generated_contract_rejects_noncanonical_or_candidate_text(
    token_ids: tuple[int, ...],
    expected: str | None,
    status: str,
    conforms: bool,
) -> None:
    _, parsed, observed_status, observed_conformance = (
        canonical_label_from_generated_tokens(
            _FakeTokenizer(), token_ids, {"A": 32, "B": 33}
        )
    )

    assert (parsed, observed_status, observed_conformance) == (
        expected,
        status,
        conforms,
    )


def test_identical_constrained_token_is_deterministic() -> None:
    tokenizer = _FakeTokenizer()

    first = canonical_label_from_generated_tokens(
        tokenizer, (32,), {"A": 32, "B": 33}
    )
    second = canonical_label_from_generated_tokens(
        tokenizer, (32,), {"A": 32, "B": 33}
    )

    assert first == second
