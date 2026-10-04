"""R-FUSE: recover skipped text by merging two reads of the same page.

Reference-free and deterministic; the rule is fixed in
`docs/stage0/R_FUSE_REGISTRATION_DRAFT.md` §5. Inputs are already-extracted
texts (scoring-v2 extraction).
"""

from __future__ import annotations

from labbs2026.thai_marks.decompose import align

MIN_RUN = 10
DUPLICATE_CORE = 12


def _already_present(run: str, anchor: str, core: int) -> bool:
    if len(run) <= core:
        return run in anchor
    middle = len(run) // 2
    return run[middle - core // 2: middle - core // 2 + core] in anchor


def fuse(anchor: str, other: str, *, min_run: int = MIN_RUN,
         duplicate_core: int | None = DUPLICATE_CORE) -> str:
    """`anchor`, plus every run of >= `min_run` characters only `other` has.

    Disagreeing characters keep the anchor's. A run whose central
    `duplicate_core` characters already occur in the anchor is a block the
    anchor read in another order and is not inserted again; `None` disables
    that check.
    """
    if not other:
        return anchor
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        text = "".join(run)
        if len(text) >= min_run and not (
            duplicate_core is not None and _already_present(text, anchor, duplicate_core)
        ):
            out.append(text)
        run.clear()

    for a, b in align(anchor, other):  # the anchor plays the reference's role
        if a is None:
            run.append(other[b])
            continue
        flush()
        out.append(anchor[a])
    flush()
    return "".join(out)


def concatenate(anchor: str, other: str) -> str:
    """Negative control: both reads, unmerged."""
    return f"{anchor} {other}".strip()
