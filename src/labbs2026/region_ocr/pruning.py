"""Post-encoder visual-token selection policies and sequence surgery.

Selecting which visual tokens survive is pure index arithmetic and is kept
separate from any model call so it can be tested exhaustively without a GPU.

Three things must be reduced together or the model silently receives an
inconsistent sequence:

1. the projector's image features, N -> K;
2. the `image_token_id` placeholders in `input_ids`, and the matching entries of
   `mm_token_type_ids` and `attention_mask`;
3. the M-RoPE 3D position ids.

The third is the subtle one. `PaddleOCRVLModel.get_rope_index` derives image
positions from `image_grid_thw`, which describes the *unpruned* layout. Letting
it recompute after pruning would assign positions for N tokens to a K-token
sequence. Positions are therefore computed once for the full layout and then
subset, so every surviving token keeps the 3D position it had before pruning —
which is what "remove tokens, leave the rest untouched" has to mean.
"""

from __future__ import annotations

import random
from typing import Literal, Sequence

Policy = Literal["RANDOM", "GRID", "COVERAGE", "MERGE_GRID"]


def resolve_budget(total: int, kept: int) -> int:
    """Validate a requested surviving-token count."""
    if total < 1:
        raise ValueError("total must be >= 1")
    if not 1 <= kept <= total:
        raise ValueError(f"kept must satisfy 1 <= kept <= {total}, got {kept}")
    return kept


def select_random_indices(total: int, kept: int, *, seed: int) -> tuple[int, ...]:
    """Uniformly random survivors, deterministic for a seed.

    The structure-free reference baseline: if a structured policy cannot beat
    this, that has to be visible.
    """
    resolve_budget(total, kept)
    rng = random.Random(seed)
    return tuple(sorted(rng.sample(range(total), kept)))


def select_grid_indices(rows: int, cols: int, kept: int) -> tuple[int, ...]:
    """Evenly spaced survivors over the 2D token grid.

    Resolution Reduction thins the image uniformly in two dimensions, so its
    post-encoder analogue must thin the token grid in two dimensions as well.
    Striding the flattened sequence instead would drop whole rows and would not
    be the matched comparison the H3 contrast needs.
    """
    total = rows * cols
    resolve_budget(total, kept)

    # Split the budget between axes in proportion to the grid's shape, so a wide
    # grid keeps proportionally more columns than rows.
    ratio = (kept / total) ** 0.5
    keep_rows = max(1, min(rows, round(rows * ratio)))
    keep_cols = max(1, min(cols, -(-kept // keep_rows)))
    while keep_rows * keep_cols < kept and (keep_rows < rows or keep_cols < cols):
        if keep_cols < cols and (keep_cols / cols) <= (keep_rows / rows):
            keep_cols += 1
        elif keep_rows < rows:
            keep_rows += 1
        else:
            break

    def spread(count: int, span: int) -> list[int]:
        if count >= span:
            return list(range(span))
        return [min(span - 1, round(i * span / count)) for i in range(count)]

    chosen_rows = spread(keep_rows, rows)
    chosen_cols = spread(keep_cols, cols)
    flat = sorted({r * cols + c for r in chosen_rows for c in chosen_cols})

    if len(flat) > kept:
        # Thin the surplus evenly rather than truncating one edge of the image.
        keep_positions = {round(i * len(flat) / kept) for i in range(kept)}
        flat = [value for index, value in enumerate(flat) if index in keep_positions]
    while len(flat) < kept:
        for candidate in range(total):
            if candidate not in flat:
                flat.append(candidate)
                break
        flat.sort()
    return tuple(sorted(flat[:kept]))


def assign_to_representatives(
    rows: int, cols: int, representatives: Sequence[int]
) -> tuple[int, ...]:
    """Map every grid token to the nearest surviving representative.

    Returns one entry per token, holding the *ordinal* of its representative
    within `representatives` rather than the representative's flat index, so the
    result indexes directly into a K-row feature tensor.

    This is the shared primitive behind the two policies that need a partition
    of the grid: merging averages each cell onto its representative, and
    coverage-aware selection replaces each cell's representative with the
    highest-signal token inside that same cell. Both therefore inherit exactly
    the spatial layout of `select_grid_indices`, which is what makes them
    comparable to it.

    Distance is Euclidean on (row, col); ties break toward the lower
    representative ordinal so the partition is deterministic.
    """
    total = rows * cols
    reps = list(representatives)
    if not reps:
        raise ValueError("at least one representative is required")
    if len(set(reps)) != len(reps):
        raise ValueError("representatives must be distinct")
    if any(not 0 <= r < total for r in reps):
        raise ValueError(f"representative outside a {rows}x{cols} grid")

    coords = [(r // cols, r % cols) for r in reps]
    assignment: list[int] = []
    for index in range(total):
        row, col = divmod(index, cols)
        best_ordinal = 0
        best_distance = None
        for ordinal, (rep_row, rep_col) in enumerate(coords):
            distance = (row - rep_row) ** 2 + (col - rep_col) ** 2
            if best_distance is None or distance < best_distance:
                best_distance, best_ordinal = distance, ordinal
        assignment.append(best_ordinal)

    for ordinal, rep in enumerate(reps):
        if assignment[rep] != ordinal:
            raise RuntimeError(f"representative {rep} was not assigned to itself")
    return tuple(assignment)


def select_coverage_indices(
    rows: int, cols: int, kept: int, scores: Sequence[float]
) -> tuple[int, ...]:
    """Highest-scoring token within each cell of the even grid partition.

    `select_grid_indices` guarantees spatial coverage but is blind to content:
    on a text region its representative may land on background while a nearby
    token carries the glyph. This keeps the coverage guarantee - exactly one
    survivor per cell - and spends the freedom inside each cell on the token
    with the most signal.

    Ties break toward the lower flat index so the selection is deterministic.
    """
    total = rows * cols
    resolve_budget(total, kept)
    if len(scores) != total:
        raise ValueError(f"expected {total} scores, got {len(scores)}")

    representatives = select_grid_indices(rows, cols, kept)
    assignment = assign_to_representatives(rows, cols, representatives)

    chosen: list[int | None] = [None] * kept
    best: list[float | None] = [None] * kept
    for index in range(total):
        ordinal = assignment[index]
        score = scores[index]
        if best[ordinal] is None or score > best[ordinal]:
            best[ordinal], chosen[ordinal] = score, index
    if any(value is None for value in chosen):
        raise RuntimeError("a cell received no token")
    picked = sorted(int(value) for value in chosen)  # type: ignore[arg-type]
    if len(set(picked)) != kept:
        raise RuntimeError("coverage selection produced duplicate tokens")
    return tuple(picked)


def select_keep_indices(
    *, policy: Policy, rows: int, cols: int, kept: int, seed: int | None = None,
    scores: Sequence[float] | None = None,
) -> tuple[int, ...]:
    if policy == "RANDOM":
        if seed is None:
            raise ValueError("RANDOM policy requires a seed")
        return select_random_indices(rows * cols, kept, seed=seed)
    if policy in ("GRID", "MERGE_GRID"):
        # Merging keeps the grid's survivors unchanged and alters only what their
        # feature vectors contain, so the two policies must select identically.
        return select_grid_indices(rows, cols, kept)
    if policy == "COVERAGE":
        if scores is None:
            raise ValueError("COVERAGE policy requires per-token scores")
        return select_coverage_indices(rows, cols, kept, scores)
    raise ValueError(f"unknown policy: {policy!r}")


def image_token_positions(input_ids: Sequence[int], image_token_id: int) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(input_ids) if value == image_token_id)


def surviving_sequence_mask(
    input_ids: Sequence[int], image_token_id: int, keep_indices: Sequence[int]
) -> tuple[bool, ...]:
    """Which sequence positions remain after dropping unselected image tokens.

    Non-image positions always survive; the i-th image token survives only if i
    is in `keep_indices`.
    """
    positions = image_token_positions(input_ids, image_token_id)
    keep = set(keep_indices)
    unknown = keep - set(range(len(positions)))
    if unknown:
        raise ValueError(f"keep indices out of range for {len(positions)} image tokens: {sorted(unknown)}")
    dropped = {positions[i] for i in range(len(positions)) if i not in keep}
    return tuple(index not in dropped for index in range(len(input_ids)))


def assert_accounting(*, pre_prune: int, post_prune: int, llm_positions: int, expected_kept: int) -> None:
    """Fail closed on the invariants a pruning call must satisfy.

    A policy that zeroes or masks tokens while leaving the sequence length
    unchanged would satisfy none of these, which is the point: the experiment
    measures removing positions from the language model, not hiding them.
    """
    if post_prune != expected_kept:
        raise RuntimeError(f"post-prune features {post_prune} != requested {expected_kept}")
    if llm_positions != expected_kept:
        raise RuntimeError(f"LLM image positions {llm_positions} != requested {expected_kept}")
    if post_prune > pre_prune:
        raise RuntimeError(f"post-prune {post_prune} exceeds pre-prune {pre_prune}")
