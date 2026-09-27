"""Feature-space operations for the merge and coverage conditions.

Both conditions are deliberately *not* named after a published method. Token
Merging as published (arXiv:2210.09461) merges tokens between the layers of the
vision transformer; averaging the projector's output afterwards is a different
operation at a different insertion point, and calling it ToMe would tell a
reader we had reproduced work we have not. It is a post-encoder spatial merge
baseline, and the name says where it acts.

What it is for: pruning and merging deliver the same number of positions at the
same grid locations, so any difference between them isolates whether the
discarded tokens' content mattered, separately from how many tokens the
language model received.
"""

from __future__ import annotations

from typing import Any, Sequence


def merge_features(features: Any, assignment: Sequence[int], kept: int) -> Any:
    """Mean of each cell's features, ordered by representative ordinal.

    A cell's representative keeps its own grid position, so the merged sequence
    is positionally identical to the pruned one and only the vectors differ.
    """
    import torch

    if features.shape[0] != len(assignment):
        raise ValueError(
            f"features {features.shape[0]} != assignment length {len(assignment)}"
        )
    index = torch.as_tensor(list(assignment), dtype=torch.long, device=features.device)
    if int(index.max().item()) >= kept or int(index.min().item()) < 0:
        raise ValueError("assignment ordinal outside the kept range")

    totals = torch.zeros(kept, features.shape[1], dtype=features.dtype, device=features.device)
    totals.index_add_(0, index, features)
    counts = torch.zeros(kept, dtype=features.dtype, device=features.device)
    counts.index_add_(0, index, torch.ones_like(index, dtype=features.dtype))
    if int((counts == 0).sum().item()):
        raise RuntimeError("a cell received no token")
    return totals / counts.unsqueeze(1)


def token_ink_scores(pixel_values: Any, *, tokens: int, merge: int) -> list[float]:
    """Per-token contrast of the raw patches, as a cheap proxy for glyph content.

    The processor emits patches already grouped so that each run of `merge**2`
    consecutive rows forms one post-merge token; that grouping is asserted here
    rather than assumed, because a layout change would silently score the wrong
    patches. Only the leading axis is relied on: this checkpoint hands back a 4-D
    `(patches, channels, height, width)` tensor rather than the flat
    `(patches, values)` one, and anything downstream of the first axis is
    flattened instead of being given an assumed shape. Standard deviation is used
    because text regions are high-contrast against a flat background, whereas
    mean brightness would rank a dark background above pale text.

    This reads the image, not the model's attention, so it adds no forward pass
    and cannot leak information from the decoder into the selection.
    """
    import torch

    expected = tokens * merge * merge
    if pixel_values.shape[0] != expected:
        raise RuntimeError(
            f"pixel_values rows {pixel_values.shape[0]} != tokens*merge^2 {expected}"
        )
    grouped = pixel_values.reshape(tokens, -1)
    return [float(v) for v in grouped.float().std(dim=1).tolist()]
