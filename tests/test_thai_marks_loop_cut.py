"""Loop onset detection and cutting."""

from __future__ import annotations

from labbs2026.thai_marks.loop_cut import cut_at_loop, loop_onset, variant_a, variant_b

HEAD = "ถนนสุขุมวิท ใกล้สถานีรถไฟ\n"


def test_a_short_loop_is_cut_after_its_first_copy() -> None:
    text = HEAD + "ซอยจุฬาภรณ์ " * 20
    assert cut_at_loop(text, 4, 3) == HEAD + "ซอยจุฬาภรณ์ "


def test_fewer_than_k_repeats_are_kept() -> None:
    text = HEAD + "ซอยจุฬาภรณ์ " * 3 + "จบ"
    assert cut_at_loop(text, 4, 3) == text


def test_units_without_letters_are_never_cut() -> None:
    text = "ชื่อ " + "." * 200 + " ที่อยู่ " + "_" * 100
    assert loop_onset(text, 4, 3) is None


def test_a_long_block_needs_fewer_repeats() -> None:
    block = "แผนที่แสดงพื้นที่โครงการโดยสังเขป แสดงตำแหน่งของถนนสุขุมวิท ซอยจุฬาภรณ์\n"
    assert len(block) >= 50
    text = HEAD + block * 3
    # The onset may be found one rotation early (unit starting at the newline
    # before it); the first copy is kept either way, so compare without
    # trailing whitespace.
    assert cut_at_loop(text, 4, 3).rstrip() == (HEAD + block).rstrip()
    assert cut_at_loop(text, 8, 6) == text


def test_the_earliest_onset_wins() -> None:
    text = HEAD + "MFA\nX" * 2 + "QMS\n" * 10 + "ภควโต " * 10
    start, unit = loop_onset(text, 4, 3)
    assert text[start:start + unit] == "QMS\n"


def test_variant_a_touches_only_runaway_outputs() -> None:
    looping = HEAD + "QMS\n" * 50
    assert variant_a({"raw_output": looping, "reached_max_new_tokens": False}) == looping
    assert variant_a({"raw_output": looping, "reached_max_new_tokens": True}).rstrip() == HEAD + "QMS"


def test_variant_b_needs_eight_repeats() -> None:
    seven = HEAD + "QMS\n" * 7 + "จบ"
    assert variant_b({"raw_output": seven, "reached_max_new_tokens": False}) == seven
    nine = HEAD + "QMS\n" * 9
    assert variant_b({"raw_output": nine, "reached_max_new_tokens": False}).rstrip() == HEAD + "QMS"
