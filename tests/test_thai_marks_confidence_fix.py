"""E1-B1 swap rule."""

from __future__ import annotations

import math

from labbs2026.thai_marks.confidence_fix import apply, flag_threshold, propose

WORDS = frozenset({"ข้าว", "ราคา", "แพง", "ขาว"})


def segment(line: str) -> list[str]:
    # A toy segmenter: greedy longest match on WORDS, else one character.
    out, i = [], 0
    vocab = sorted(WORDS | {"ข้าา"}, key=len, reverse=True)
    while i < len(line):
        for w in vocab:
            if line.startswith(w, i):
                out.append(w)
                i += len(w)
                break
        else:
            out.append(line[i])
            i += 1
    return out


def _case(raw, chosen_at, alts, lp=-3.0):
    # tokens: one per character, the flagged one at `chosen_at`
    offsets = [(i, i + 1) for i in range(len(raw))]
    logprob = [-0.01] * len(raw)
    logprob[chosen_at] = lp
    top_ids = [[0]] * len(raw)
    top_lps = [[-0.01]] * len(raw)
    top_ids[chosen_at] = list(range(1, len(alts) + 1))
    top_lps[chosen_at] = [a[1] for a in alts]
    table = {i + 1: a[0] for i, a in enumerate(alts)}
    return offsets, logprob, top_ids, top_lps, lambda t: table.get(t, "?")


def test_a_low_confidence_non_word_becomes_a_word() -> None:
    raw = "ขาาว ราคา"  # "ขาาว" is not a word; swapping the second า for ้ gives ข้าว? no:
    raw = "ข่าวราคา"  # ข่าว is not in WORDS; ่ -> ้ makes ข้าว
    offsets, lp, ids, lps, dec = _case(raw, 1, [("้", -3.5)])
    swaps = propose(raw, offsets, lp, ids, lps, -1.0, dec, segment, WORDS)
    assert [s["new"] for s in swaps] == ["้"]
    assert apply(raw, swaps) == "ข้าวราคา"


def test_confident_tokens_and_real_words_are_left_alone() -> None:
    raw = "ข้าวราคา"
    offsets, lp, ids, lps, dec = _case(raw, 1, [("่", -3.5)])
    assert propose(raw, offsets, lp, ids, lps, -1.0, dec, segment, WORDS) == []  # w0 is a word
    raw2 = "ข่าวราคา"
    offsets, lp, ids, lps, dec = _case(raw2, 1, [("้", -3.5)], lp=-0.5)
    assert propose(raw2, offsets, lp, ids, lps, -1.0, dec, segment, WORDS) == []  # not flagged


def test_unlikely_or_broken_alternatives_are_rejected() -> None:
    raw = "ข่าวราคา"
    offsets, lp, ids, lps, dec = _case(raw, 1, [("้", -3.0 - math.log(10) - 0.1), ("�", -3.1)])
    assert propose(raw, offsets, lp, ids, lps, -1.0, dec, segment, WORDS) == []


def test_threshold_is_the_lowest_share_of_thai_tokens() -> None:
    lps = [[-0.1] * 95 + [-5.0] * 5]
    texts = [["ก"] * 100]
    assert flag_threshold(lps, texts, 0.05) == -5.0
    assert flag_threshold([[-9.0]], [["a"]], 0.05) == -math.inf
