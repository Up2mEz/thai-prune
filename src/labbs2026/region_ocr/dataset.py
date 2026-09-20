"""TEMS region-OCR metadata loading and pre-declared sample selection.

Ground truth is read from the metadata CSV, never from filenames: 1.6% of the
released filenames are filesystem-sanitised variants that disagree with the
`label` column.
"""

from __future__ import annotations

import csv
import hashlib
import io
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

REQUIRED_COLUMNS = (
    "source_photo_id",
    "image_id",
    "filename",
    "label",
    "file_size_mb",
    "script_type",
    "text_length",
    "image_width",
    "image_height",
    "split",
)

# The evaluation split is never opened during development.
DEVELOPMENT_SPLITS = ("train",)

THAI_BLOCK = ("฀", "๿")


def has_thai(text: str) -> bool:
    """True if the label contains at least one Thai codepoint.

    TEMS is a multiscript corpus: 46% of its regions are English-only and carry
    no Thai orthography at all. Eligibility is decided on the label itself
    rather than on the `script_type` column, so the filter does not depend on
    the metadata being right.
    """
    return any(THAI_BLOCK[0] <= character <= THAI_BLOCK[1] for character in text)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_tems_metadata(path: Path) -> list[dict[str, Any]]:
    """Read the TEMS metadata CSV and fail closed on any schema drift.

    The file is UTF-8 with a BOM; Windows' default cp874 codec cannot decode it,
    so the encoding is always specified explicitly.
    """
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        if columns != REQUIRED_COLUMNS:
            raise RuntimeError(f"unexpected TEMS schema: {columns!r}")
        rows = list(reader)

    if not rows:
        raise RuntimeError("TEMS metadata is empty")
    for row in rows:
        if not row["source_photo_id"].strip():
            raise RuntimeError(f"blank source_photo_id for image_id={row['image_id']!r}")
        if not row["label"]:
            raise RuntimeError(f"blank label for image_id={row['image_id']!r}")
        row["image_width"] = int(row["image_width"])
        row["image_height"] = int(row["image_height"])
        row["text_length"] = int(row["text_length"])
    return rows


def assert_split_disjoint_by_photo(rows: Iterable[dict[str, Any]]) -> None:
    """A source photograph must never appear on both sides of a split."""
    splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        splits[row["source_photo_id"]].add(row["split"])
    straddling = sorted(photo for photo, seen in splits.items() if len(seen) > 1)
    if straddling:
        raise RuntimeError(f"source photos span multiple splits: {straddling[:5]}")


def select_smoke_sample(
    rows: Sequence[dict[str, Any]],
    *,
    seed: int,
    photos: int,
    crops_per_photo: int,
    available_filenames: set[str] | None = None,
    splits: Sequence[str] = DEVELOPMENT_SPLITS,
    require_thai: bool = True,
) -> list[dict[str, Any]]:
    """Deterministically pick an engineering-smoke sample.

    Selection is by source photograph, so every returned crop belongs to a photo
    that was chosen as a whole. `available_filenames` restricts the pool to files
    that can actually be retrieved; that restriction is an artifact of the
    distribution API and must be recorded, since it is not a scientific sampling
    frame.

    Raises rather than returning a short sample: quietly shrinking a quota hides
    the fact that the requested design was not met.
    """
    if photos < 1 or crops_per_photo < 1:
        raise ValueError("photos and crops_per_photo must be >= 1")

    pool = [row for row in rows if row["split"] in splits]
    if require_thai:
        pool = [row for row in pool if has_thai(row["label"])]
    if available_filenames is not None:
        pool = [row for row in pool if row["filename"] in available_filenames]

    by_photo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pool:
        by_photo[row["source_photo_id"]].append(row)

    eligible = sorted(
        photo for photo, crops in by_photo.items() if len(crops) >= crops_per_photo
    )
    if len(eligible) < photos:
        raise RuntimeError(
            f"need {photos} photos with >= {crops_per_photo} available crops, "
            f"found {len(eligible)}"
        )

    rng = random.Random(seed)
    chosen_photos = sorted(rng.sample(eligible, photos))

    selection: list[dict[str, Any]] = []
    for photo in chosen_photos:
        crops = sorted(by_photo[photo], key=lambda row: row["image_id"])
        selection.extend(crops[:crops_per_photo])
    return selection


def selection_manifest(
    selection: Sequence[dict[str, Any]], *, seed: int, splits: Sequence[str]
) -> dict[str, Any]:
    """Provenance record for a selection, written before any model is run."""
    return {
        "seed": seed,
        "splits": list(splits),
        "region_count": len(selection),
        "photo_count": len({row["source_photo_id"] for row in selection}),
        "regions": [
            {
                "source_photo_id": row["source_photo_id"],
                "image_id": row["image_id"],
                "filename": row["filename"],
                "label": row["label"],
                "image_width": row["image_width"],
                "image_height": row["image_height"],
                "split": row["split"],
            }
            for row in selection
        ],
    }
