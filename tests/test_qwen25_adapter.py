import pytest

from labbs2026.adapters.qwen25_vl import parse_ab, visual_counts_from_grid


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
