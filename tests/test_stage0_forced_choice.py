from labbs2026.stage0.forced_choice import make_forced_choice, parse_choice


PROMPT = "A. {candidate_a}\nB. {candidate_b}"


def test_pair_members_share_order_and_balance_expected_labels() -> None:
    first = make_forced_choice(
        pair_id="tone_ka",
        condition_id="condition",
        displayed_member="a",
        text_a="กา",
        text_b="ก่า",
        seed=7,
        prompt_template=PROMPT,
    )
    second = make_forced_choice(
        pair_id="tone_ka",
        condition_id="condition",
        displayed_member="b",
        text_a="กา",
        text_b="ก่า",
        seed=7,
        prompt_template=PROMPT,
    )

    assert (first.candidate_a, first.candidate_b) == (
        second.candidate_a,
        second.candidate_b,
    )
    assert {first.expected_label, second.expected_label} == {"A", "B"}
    assert first.orientation == second.orientation


def test_order_is_seeded_and_reproducible() -> None:
    arguments = dict(
        pair_id="tone_ka",
        condition_id="condition",
        displayed_member="a",
        text_a="กา",
        text_b="ก่า",
        seed=20260906,
        prompt_template=PROMPT,
    )

    assert make_forced_choice(**arguments) == make_forced_choice(**arguments)


def test_parser_separates_exact_label_from_additional_text() -> None:
    assert parse_choice(" a\n") == ("A", "PARSED")
    assert parse_choice("B") == ("B", "PARSED")
    assert parse_choice("คำตอบคือ A") == (None, "PARSER_FAILURE")
    assert parse_choice("A.") == (None, "PARSER_FAILURE")
