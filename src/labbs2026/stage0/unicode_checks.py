"""Deterministic Unicode checks for the proposed Thai candidate inventory."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


THAI_CONSONANT_RANGE = range(0x0E01, 0x0E2F)
THAI_UPPER_VOWELS = {0x0E34, 0x0E35, 0x0E36, 0x0E37}
THAI_LOWER_VOWELS = {0x0E38, 0x0E39}
MAI_EK = 0x0E48


@dataclass(frozen=True)
class UnicodeValidation:
    codepoints_a: tuple[str, ...]
    codepoints_b: tuple[str, ...]
    normalization_a: str
    normalization_b: str
    issues: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.issues


def codepoints(text: str) -> tuple[str, ...]:
    return tuple(f"U+{ord(character):04X}" for character in text)


def normalization_form(text: str) -> str:
    forms = [form for form in ("NFC", "NFD", "NFKC", "NFKD") if unicodedata.normalize(form, text) == text]
    return "+".join(forms) if forms else "UNNORMALIZED"


def _canonical_mark_order(text: str) -> bool:
    rank = {}
    rank.update({value: 1 for value in THAI_UPPER_VOWELS | THAI_LOWER_VOWELS})
    rank.update({value: 2 for value in range(0x0E48, 0x0E4C)})
    previous = 0
    for character in text:
        value = rank.get(ord(character), 0)
        if value and value < previous:
            return False
        if value:
            previous = value
        elif ord(character) in THAI_CONSONANT_RANGE:
            previous = 0
    return True


def _single_addition(plain: str, marked: str, value: int) -> bool:
    for index, character in enumerate(marked):
        if ord(character) == value and marked[:index] + marked[index + 1 :] == plain:
            return True
    return False


def validate_pair(text_a: str, text_b: str, difference_rule: str) -> UnicodeValidation:
    issues: list[str] = []
    if not text_a or not text_b:
        issues.append("EMPTY_STRING")
    if text_a == text_b:
        issues.append("IDENTICAL_STRINGS")
    for label, text in (("A", text_a), ("B", text_b)):
        if any(not 0x0E00 <= ord(character) <= 0x0E7F for character in text):
            issues.append(f"NON_THAI_CODEPOINT_{label}")
        if unicodedata.normalize("NFC", text) != text:
            issues.append(f"NON_NFC_{label}")
        if not _canonical_mark_order(text):
            issues.append(f"NONCANONICAL_MARK_ORDER_{label}")

    if difference_rule == "BASE_SUBSTITUTION":
        valid_rule = (
            len(text_a) == len(text_b)
            and len(text_a) >= 1
            and text_a[1:] == text_b[1:]
            and ord(text_a[0]) in THAI_CONSONANT_RANGE
            and ord(text_b[0]) in THAI_CONSONANT_RANGE
            and text_a[0] != text_b[0]
        )
    elif difference_rule == "MAI_EK_ADDITION":
        valid_rule = _single_addition(text_a, text_b, MAI_EK)
    elif difference_rule == "UPPER_VOWEL_SUBSTITUTION":
        differences = [
            (left, right)
            for left, right in zip(text_a, text_b, strict=False)
            if left != right
        ]
        valid_rule = (
            len(text_a) == len(text_b)
            and len(differences) == 1
            and ord(differences[0][0]) in THAI_UPPER_VOWELS
            and ord(differences[0][1]) in THAI_UPPER_VOWELS
        )
    elif difference_rule == "LOWER_VOWEL_SUBSTITUTION":
        differences = [
            (left, right)
            for left, right in zip(text_a, text_b, strict=False)
            if left != right
        ]
        valid_rule = (
            len(text_a) == len(text_b)
            and len(differences) == 1
            and ord(differences[0][0]) in THAI_LOWER_VOWELS
            and ord(differences[0][1]) in THAI_LOWER_VOWELS
        )
    elif difference_rule == "MAI_EK_IN_UPPER_CONTEXT":
        valid_rule = (
            _single_addition(text_a, text_b, MAI_EK)
            and any(ord(character) in THAI_UPPER_VOWELS for character in text_a)
        )
    else:
        valid_rule = False
        issues.append("UNKNOWN_DIFFERENCE_RULE")

    if not valid_rule and "UNKNOWN_DIFFERENCE_RULE" not in issues:
        issues.append("DIFFERENCE_RULE_MISMATCH")

    return UnicodeValidation(
        codepoints_a=codepoints(text_a),
        codepoints_b=codepoints(text_b),
        normalization_a=normalization_form(text_a),
        normalization_b=normalization_form(text_b),
        issues=tuple(sorted(set(issues))),
    )
