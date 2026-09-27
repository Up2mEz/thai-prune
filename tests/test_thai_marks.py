"""Tests for the T1/T2 instrument: sites, variants, normalization, split, fates."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks.decompose import (
    align,
    is_repetitive,
    mark_decomposition,
    reference_fates,
)
from labbs2026.thai_marks.normalize import collapse_whitespace, normalize_text
from labbs2026.thai_marks.orthography import (
    NONE,
    SITE_CAPS,
    Site,
    apply_variant,
    find_sites,
    sample_sites,
    window_variants,
)
from labbs2026.thai_marks.split import calibration_ids

MAI_THO = "้"
MAI_EK = "่"
SARA_I = "ิ"
SARA_U = "ุ"

# --- sites and variants ------------------------------------------------------


def test_sites_cover_tone_upper_lower_and_bare_consonants() -> None:
    text = "ไฟฟ้า"  # ไ ฟ ฟ ้ า
    kinds = [(s.kind, s.index) for s in find_sites(text)]
    assert ("TONE", 3) in kinds
    assert ("TONE_ABSENT", 1) in kinds  # first ฟ, followed by ฟ
    assert all(k != "TONE_ABSENT" or i != 2 for k, i in kinds)  # second ฟ carries the mark


def test_upper_and_lower_vowels_are_sites() -> None:
    kinds = {s.kind for s in find_sites("กิน" + "ปุ๋ย")}
    assert {"UPPER", "LOWER", "TONE"} <= kinds


def test_a_consonant_at_the_end_is_not_a_bare_site() -> None:
    assert not [s for s in find_sites("กข") if s.index == 1]


def test_variants_change_only_the_mark() -> None:
    text = "ไฟฟ้า"
    site = Site("TONE", 3, MAI_THO)
    assert apply_variant(text, site, NONE) == "ไฟฟา"
    assert apply_variant(text, site, MAI_EK) == "ไฟฟ่า"
    assert apply_variant(text, site, MAI_THO) == text


def test_insertion_variants_add_after_the_consonant() -> None:
    site = Site("TONE_ABSENT", 0, NONE)
    assert apply_variant("นา", site, MAI_THO) == "น้า"
    assert apply_variant("นา", site, NONE) == "นา"


def test_a_foreign_label_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_variant("นา", Site("TONE", 0, MAI_EK), SARA_I)


def test_windows_share_boundaries_and_differ_only_in_the_mark() -> None:
    text = "ข้าวผัดกุ้ง"
    site = Site("TONE", 1, MAI_THO)
    windows = dict(window_variants(text, site, window_start=0, after=3))
    # `after=3` keeps the three characters after the site: า ว ผ.
    assert windows[MAI_THO] == "ข้าวผ"
    assert windows[NONE] == "ขาวผ"
    assert windows[MAI_EK] == "ข่าวผ"
    assert len(windows) == 5


def test_window_must_not_start_after_the_site() -> None:
    with pytest.raises(ValueError):
        window_variants("นา", Site("TONE_ABSENT", 0, NONE), window_start=1)


def test_sampling_respects_caps_and_is_reproducible() -> None:
    text = "น้" * 60
    sites = find_sites(text)
    first = sample_sites(sites, "item-7")
    assert first == sample_sites(sites, "item-7")
    assert sum(s.kind == "TONE" for s in first) == SITE_CAPS["TONE"]
    assert first != sample_sites(sites, "item-8")


# --- normalization -----------------------------------------------------------


def test_normalization_strips_structure_but_never_thai() -> None:
    raw = ("# หัวข้อ\n**ตัวหนา** <table><tr><td>ก่อน</td><td>หลัง</td></tr></table>\n"
           "<figure>ภาพคนกำลังเดิน</figure> <page_number>08</page_number> $x^2$ a | b")
    out = normalize_text(raw)
    assert out == "หัวข้อ ตัวหนา ก่อน หลัง 08 x^2 a b"
    assert "ภาพคน" not in out  # figure descriptions are not page text


def test_normalization_is_idempotent_and_keeps_marks() -> None:
    text = "ไฟฟ้า  ผู้อำนวยการ\nกี่"
    once = normalize_text(text)
    assert normalize_text(once) == once
    assert once == "ไฟฟ้า ผู้อำนวยการ กี่"


def test_collapse_whitespace_only_touches_whitespace() -> None:
    assert collapse_whitespace(" ก่อน\n\tหลัง | x ") == "ก่อน หลัง | x"


# --- split -------------------------------------------------------------------


def _items(n: int, strata: int = 3):
    return [(f"id{i}", "Full-page OCR", f"cat{i % strata}") for i in range(n)]


def test_split_takes_the_ceiling_within_each_stratum() -> None:
    chosen = calibration_ids(_items(30), fraction=0.3)
    per_stratum = [sum(1 for i in chosen if int(i[2:]) % 3 == s) for s in range(3)]
    assert per_stratum == [3, 3, 3]


def test_split_is_seed_dependent_and_deterministic() -> None:
    items = _items(40)
    assert calibration_ids(items) == calibration_ids(items)
    assert calibration_ids(items, seed=1) != calibration_ids(items, seed=2)


def test_split_rejects_duplicates_and_bad_fractions() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        calibration_ids([("a", "t", "c"), ("a", "t", "c")])
    with pytest.raises(ValueError):
        calibration_ids(_items(3), fraction=1.0)


# --- fates and decomposition -------------------------------------------------


def test_alignment_of_identical_strings_is_diagonal() -> None:
    assert align("abc", "abc") == [(0, 0), (1, 1), (2, 2)]


def test_a_dropped_tone_mark_is_a_deletion() -> None:
    fates = reference_fates("ไฟฟ้า", "ไฟฟา")
    assert fates[3] == "deleted"
    assert all(fates[i] == "correct" for i in (0, 1, 2, 4))


def test_decomposition_separates_mark_specific_from_syllable_errors() -> None:
    reference = "ไฟฟ้า น้ำ"
    out = mark_decomposition(reference, "ไฟฟา นํา")  # tone lost twice; second base kept
    tone = out["TONE"]
    assert tone["n"] == 2
    assert tone["base_correct_n"] == 2
    assert tone["base_correct_error"] == 2
    out2 = mark_decomposition("น้า", "ม้า")  # base misread, mark kept
    assert out2["TONE"]["correct"] == 1
    assert out2["TONE"].get("base_correct_n", 0) == 0
    assert out2["CONSONANT"] == {"n": 1, "error": 1}


def test_same_class_substitution_is_distinguished() -> None:
    out = mark_decomposition("น้า", "น่า")
    assert out["TONE"]["same_class"] == 1


def test_repetition_detector() -> None:
    assert is_repetitive("2564 ดร " * 40)
    assert not is_repetitive("ข้อความปกติที่ไม่ซ้ำกันเลยแม้แต่น้อย " + "abcdefghij" * 3)


# --- positions ---------------------------------------------------------------

torch = pytest.importorskip("torch")


def test_continuation_positions_advance_from_the_boundary_on_every_axis() -> None:
    from labbs2026.thai_marks.runtime import continuation_positions

    prefix = torch.tensor([[[0, 1, 5, 9]], [[0, 1, 5, 9]], [[0, 1, 5, 9]]])
    out = continuation_positions(prefix, boundary=2, length=3)
    assert out.shape == (3, 1, 3)
    assert out[0, 0].tolist() == [5, 6, 7]
    assert out[2, 0].tolist() == [5, 6, 7]
