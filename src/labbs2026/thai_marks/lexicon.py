"""Real-word versus non-word mark errors.

A Thai tone mark is lexically contrastive, so a mark error can land on another
real word (ข้าว read as ขาว) or on a string that is no word at all (ไฟฟ้า read as
ไฟฟา). The two shapes point at different causes: a real-word substitution is
what a language prior overriding weak visual evidence would produce, while a
non-word is what failed perception with no prior correction would produce. This
module only classifies; it infers nothing on its own.

Lexicon: PyThaiNLP `words_th.txt`, CC0-1.0. Segmentation: PyThaiNLP `newmm`.
"""

from __future__ import annotations

import collections
from functools import lru_cache
from typing import Any

from labbs2026.thai_marks.decompose import MARK_CLASSES, _fates_from, align


@lru_cache(maxsize=1)
def lexicon() -> frozenset[str]:
    from pythainlp.corpus import thai_words

    return frozenset(thai_words())


def word_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of `newmm` words, skipping whitespace."""
    from pythainlp.tokenize import word_tokenize

    spans, cursor = [], 0
    for word in word_tokenize(text, engine="newmm", keep_whitespace=True):
        start = cursor
        cursor += len(word)
        if word.strip():
            spans.append((start, cursor))
    if cursor != len(text):
        raise RuntimeError("segmentation does not cover the text")
    return spans


def classify_mark_errors(reference: str, hypothesis: str, pairs: list | None = None,
                         words: frozenset[str] | None = None) -> dict[str, Any]:
    """Counts of mark errors by the lexical status of the misread word, per class."""
    if pairs is None:
        pairs = align(reference, hypothesis)
    if words is None:
        words = lexicon()
    fates, _ = _fates_from(pairs, reference, hypothesis)
    hyp_of = {r: h for r, h in pairs if r is not None and h is not None}
    spans = word_spans(reference)

    out: dict[str, Any] = {name: collections.Counter() for name in MARK_CLASSES}
    for name, members in MARK_CLASSES.items():
        for index, char in enumerate(reference):
            if char not in members or fates.get(index) == "correct":
                continue
            span = next((s for s in spans if s[0] <= index < s[1]), None)
            if span is None:
                continue
            ref_word = reference[span[0]:span[1]]
            if ref_word not in words:
                out[name]["reference_not_in_lexicon"] += 1
                continue
            aligned = [hyp_of[i] for i in range(*span) if i in hyp_of]
            if not aligned:
                out[name]["word_lost"] += 1
                continue
            hyp_word = hypothesis[min(aligned):max(aligned) + 1]
            if hyp_word == ref_word:
                out[name]["span_unchanged"] += 1
            elif hyp_word in words:
                out[name]["real_word"] += 1
            else:
                out[name]["non_word"] += 1
    return {name: dict(counts) for name, counts in out.items()}
