"""Thai mark sites and the legal variants that differ only in one mark.

T2 asks, for each place a Thai mark sits or could sit, whether the model's own
scoring prefers the reference mark over the few alternatives the script
allows. The alternatives are deliberately narrow: only the mark changes, never
the consonant, so every variant stays a plausible Thai spelling and the
comparison isolates the mark itself.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

TONE_MARKS = ("่", "้", "๊", "๋")
UPPER_VOWELS = ("ั", "ิ", "ี", "ึ", "ื", "็")
# Phinthu (U+0E3A) is a lower mark too, but it is a Pali-script sign rather than
# a vowel and has no substitutable alternatives here, so it is not a site.
LOWER_VOWELS = ("ุ", "ู")
CONSONANTS = tuple(chr(code) for code in range(0x0E01, 0x0E2F))
# Every Thai combining (Mn) character: a consonant followed by one of these is
# already carrying a mark and is not a bare-consonant site.
COMBINING = frozenset(
    ["ั"] + [chr(c) for c in range(0x0E34, 0x0E3B)] + [chr(c) for c in range(0x0E47, 0x0E4F)]
)

NONE = "none"

CLASS_VARIANTS: dict[str, tuple[str, ...]] = {
    "TONE": (NONE, *TONE_MARKS),
    "UPPER": (NONE, *UPPER_VOWELS),
    "LOWER": (NONE, *LOWER_VOWELS),
    "TONE_ABSENT": (NONE, *TONE_MARKS),
}

SITE_CAPS = {"TONE": 24, "UPPER": 12, "LOWER": 8, "TONE_ABSENT": 12}


@dataclass(frozen=True)
class Site:
    kind: str
    index: int  # character index of the mark, or of the bare consonant
    reference: str  # the reference variant label

    @property
    def inserts(self) -> bool:
        return self.kind == "TONE_ABSENT"


def find_sites(text: str) -> list[Site]:
    """Every mark site and bare-consonant site in a reference string."""
    sites: list[Site] = []
    for index, char in enumerate(text):
        if char in TONE_MARKS:
            sites.append(Site("TONE", index, char))
        elif char in UPPER_VOWELS:
            sites.append(Site("UPPER", index, char))
        elif char in LOWER_VOWELS:
            sites.append(Site("LOWER", index, char))
        elif (
            char in CONSONANTS
            and index + 1 < len(text)
            and text[index + 1] not in COMBINING
        ):
            sites.append(Site("TONE_ABSENT", index, NONE))
    return sites


def sample_sites(sites: Sequence[Site], item_id: str, seed: int = 20260927) -> list[Site]:
    """At most `SITE_CAPS[kind]` sites per class, drawn reproducibly per item."""
    rng = random.Random(f"{seed}:{item_id}")
    chosen: list[Site] = []
    for kind, cap in SITE_CAPS.items():
        pool = [s for s in sites if s.kind == kind]
        if len(pool) > cap:
            pool = rng.sample(pool, cap)
        chosen.extend(pool)
    return sorted(chosen, key=lambda s: (s.index, s.kind))


def apply_variant(text: str, site: Site, label: str) -> str:
    """The text with only this site's mark changed to `label`."""
    if label not in CLASS_VARIANTS[site.kind]:
        raise ValueError(f"{label!r} is not a {site.kind} variant")
    mark = "" if label == NONE else label
    if site.inserts:
        return text[: site.index + 1] + mark + text[site.index + 1 :]
    return text[: site.index] + mark + text[site.index + 1 :]


def window_variants(
    text: str, site: Site, window_start: int, after: int = 8
) -> list[tuple[str, str]]:
    """(label, window text) for every variant of a site.

    The window runs from `window_start` — the start of the reference token
    containing the site — to `after` characters past the site in the reference,
    with the edit applied inside it. Every variant shares the same boundaries,
    so the only difference between two windows is the mark.
    """
    if not 0 <= window_start <= site.index:
        raise ValueError("window must start at or before the site")
    end = min(len(text), site.index + 1 + after)
    out = []
    for label in CLASS_VARIANTS[site.kind]:
        edited = apply_variant(text, site, label)
        shift = len(edited) - len(text)
        out.append((label, edited[window_start : end + shift]))
    return out
