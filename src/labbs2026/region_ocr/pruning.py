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

Policy = Literal["RANDOM", "GRID"]


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


def select_keep_indices(
    *, policy: Policy, rows: int, cols: int, kept: int, seed: int | None = None
) -> tuple[int, ...]:
    if policy == "RANDOM":
        if seed is None:
            raise ValueError("RANDOM policy requires a seed")
        return select_random_indices(rows * cols, kept, seed=seed)
    if policy == "GRID":
        return select_grid_indices(rows, cols, kept)
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
