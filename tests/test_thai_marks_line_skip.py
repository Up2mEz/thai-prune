"""T3 boundary construction."""

from __future__ import annotations

from labbs2026.thai_marks.line_skip import boundaries

L1 = "ประกาศกรมราชทัณฑ์ ฉบับที่หนึ่ง"
L2 = "ผู้ต้องขังทุกคนต้องปฏิบัติตาม"
L3 = "ระเบียบของเรือนจำอย่างเคร่งครัด"
L4 = "หากฝ่าฝืนจะถูกลงโทษทางวินัย"


def _record(output: str) -> dict:
    return {"id": "p1", "reference": "\n".join([L1, L2, L3, L4]), "raw_output": output}


def test_a_skipped_line_gives_one_skip_boundary_after_the_last_line_read() -> None:
    cases = boundaries(_record(" ".join([L1, L3, L4])), controls_per_page=0)
    assert [c["kind"] for c in cases] == ["skip"]
    skip = cases[0]
    assert skip["line"] == 1
    assert skip["prefix"].rstrip().endswith(L1[-6:])
    assert skip["expected"] == L2[:12] and skip["actual"] == L3[:12]
    assert skip["marked"]


def test_a_fully_read_page_has_controls_and_no_skips() -> None:
    cases = boundaries(_record(" ".join([L1, L2, L3, L4])), controls_per_page=5)
    assert cases and all(c["kind"] == "control" for c in cases)
    for c in cases:
        assert c["expected"] != c["actual"]  # the next-next line, not the one read


def test_controls_are_seeded() -> None:
    record = _record(" ".join([L1, L2, L3, L4]))
    assert boundaries(record, controls_per_page=1) == boundaries(record, controls_per_page=1)


def test_a_line_read_in_another_order_is_not_a_skip() -> None:
    cases = boundaries(_record(" ".join([L1, L3, L4, L2])), controls_per_page=0)
    assert not [c for c in cases if c["kind"] == "skip"]


def test_the_raw_prefix_keeps_the_newline_the_model_wrote() -> None:
    raw = f"{L1}\n{L3}\n{L4}"
    skip = [c for c in boundaries(_record(raw), controls_per_page=0) if c["kind"] == "skip"][0]
    assert skip["raw_prefix"] == L1 + "\n"
    assert skip["raw_actual"] == L3[:12]


def test_a_prefix_that_cannot_be_placed_in_the_raw_text_is_unscorable() -> None:
    from labbs2026.thai_marks.line_skip import raw_position
    assert raw_position("abc", "xyz") is None
    assert raw_position("ก ข\nค", "ก ข") == 3


# --- token split at the prefix/continuation join -------------------------------

import pytest  # noqa: E402

from labbs2026.thai_marks.runtime import continuation_split  # noqa: E402


def _char_tokenizer(merge: str = ""):
    """One token per character, except that `merge` (if set) is one token."""
    def encode(text: str) -> list[int]:
        out, i = [], 0
        while i < len(text):
            if merge and text.startswith(merge, i):
                out.append(1000); i += len(merge)
            else:
                out.append(ord(text[i])); i += 1
        return out

    def decode(ids: list[int]) -> str:
        return "".join(merge if t == 1000 else chr(t) for t in ids)
    return encode, decode


def test_plain_join_splits_at_the_end_of_the_prefix() -> None:
    enc, dec = _char_tokenizer()
    shared, windows = continuation_split(enc, dec, "ab\n", {"actual": "cd", "skipped": "ef"})
    assert dec(shared) == "ab\n"
    assert dec(windows["actual"]) == "cd" and dec(windows["skipped"]) == "ef"


def test_a_token_merging_across_the_join_moves_the_split_back() -> None:
    enc, dec = _char_tokenizer(merge="\nc")  # "\n" + "c" becomes one token
    shared, windows = continuation_split(enc, dec, "ab\n", {"actual": "cd", "skipped": "ef"})
    assert dec(shared) == "ab"
    assert dec(windows["actual"]) == "\ncd" and dec(windows["skipped"]) == "\nef"


def test_an_empty_continuation_is_refused() -> None:
    enc, dec = _char_tokenizer()
    with pytest.raises(RuntimeError):
        continuation_split(enc, dec, "ab", {"actual": "", "skipped": "x"})


def test_a_case_whose_two_continuations_coincide_is_dropped() -> None:
    # The skipped line begins exactly like the line read instead.
    same = L3[:12] + "อีกบรรทัดหนึ่งที่ต่างออกไป"
    record = {"id": "p2", "reference": "\n".join([L1, same, L3, L4]),
              "raw_output": " ".join([L1, L3, L4])}
    assert not [c for c in boundaries(record, controls_per_page=0) if c["kind"] == "skip"]


# --- T3 summary ------------------------------------------------------------------------

from labbs2026.thai_marks.line_skip import margin, summarize_t3  # noqa: E402


def _scored(kind, actual, expected, actual_noimg=None, expected_noimg=None, prompt="BENCHMARK_QUESTION"):
    def e(lp):
        return {"logprob": lp, "tokens": 4}
    return {"kind": kind, "prompt_kind": prompt, "scores": {
        "actual": {"image": e(actual), "no_image": e(actual if actual_noimg is None else actual_noimg)},
        "expected": {"image": e(expected), "no_image": e(expected if expected_noimg is None else expected_noimg)}}}


def test_margin_is_actual_minus_expected() -> None:
    assert margin(_scored("skip", -2.0, -5.0), "image") == 3.0


def test_summary_separates_skips_from_controls_and_measures_image_support() -> None:
    rows = [_scored("skip", -2.0, -2.5, expected_noimg=-6.0) for _ in range(5)]
    rows += [_scored("control", -1.0, -20.0) for _ in range(20)]
    s = summarize_t3(rows)["BENCHMARK_QUESTION"]
    assert s["skip"]["margin_median"] == 0.5          # near-tie
    assert s["control"]["margin_median"] == 19.0      # an ordinary skip is far
    assert s["skip"]["image_support_median"] == 3.5   # image favours the skipped line
    assert s["skip_share_within_control_q90"] == 1.0
