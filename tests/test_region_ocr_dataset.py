"""Tests for TEMS metadata loading and smoke-sample selection."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from labbs2026.region_ocr.dataset import (
    REQUIRED_COLUMNS,
    assert_split_disjoint_by_photo,
    has_thai,
    load_tems_metadata,
    select_smoke_sample,
    selection_manifest,
)

HEADER = ",".join(REQUIRED_COLUMNS)


def _row(photo: str, image_id: str, label: str = "กี่", split: str = "train") -> str:
    return f"{photo},{image_id},{image_id}_{label}.jpg,{label},0.01,thai,3,262,49,{split}"


def _write(tmp_path: Path, lines: list[str], *, bom: bool = True) -> Path:
    path = tmp_path / "meta.csv"
    text = "\n".join([HEADER, *lines]) + "\n"
    with io.open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as handle:
        handle.write(text)
    return path


def _rows(photos: int = 6, crops: int = 3, split: str = "train") -> list[dict]:
    out = []
    for p in range(photos):
        for c in range(crops):
            out.append(
                {
                    "source_photo_id": f"signs_{p}",
                    "image_id": f"{p}{c:02d}",
                    "filename": f"{p}{c:02d}_x.jpg",
                    "label": "กี่",
                    "image_width": 262,
                    "image_height": 49,
                    "text_length": 3,
                    "split": split,
                }
            )
    return out


def test_load_tems_metadata_reads_bom_and_thai(tmp_path: Path) -> None:
    path = _write(tmp_path, [_row("signs_1", "1000")])
    rows = load_tems_metadata(path)
    assert len(rows) == 1
    assert rows[0]["source_photo_id"] == "signs_1"
    assert rows[0]["label"] == "กี่"
    assert rows[0]["image_width"] == 262
    assert isinstance(rows[0]["text_length"], int)


def test_load_tems_metadata_rejects_schema_drift(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unexpected TEMS schema"):
        load_tems_metadata(path)


def test_load_tems_metadata_rejects_blank_photo_id_and_label(tmp_path: Path) -> None:
    blank_photo = _write(tmp_path, [_row("", "1000")])
    with pytest.raises(RuntimeError, match="blank source_photo_id"):
        load_tems_metadata(blank_photo)

    blank_label = tmp_path / "b2.csv"
    with io.open(blank_label, "w", encoding="utf-8-sig", newline="") as handle:
        handle.write(HEADER + "\n" + "signs_1,1000,1000_.jpg,,0.01,thai,0,262,49,train\n")
    with pytest.raises(RuntimeError, match="blank label"):
        load_tems_metadata(blank_label)


def test_load_tems_metadata_rejects_empty_file(tmp_path: Path) -> None:
    path = _write(tmp_path, [])
    with pytest.raises(RuntimeError, match="empty"):
        load_tems_metadata(path)


def test_assert_split_disjoint_by_photo() -> None:
    assert_split_disjoint_by_photo(_rows())
    straddling = _rows(photos=1, crops=2)
    straddling[1]["split"] = "test"
    with pytest.raises(RuntimeError, match="span multiple splits"):
        assert_split_disjoint_by_photo(straddling)


def test_selection_is_deterministic_for_a_seed() -> None:
    rows = _rows()
    first = select_smoke_sample(rows, seed=7, photos=2, crops_per_photo=2)
    second = select_smoke_sample(rows, seed=7, photos=2, crops_per_photo=2)
    assert [r["image_id"] for r in first] == [r["image_id"] for r in second]
    assert len(first) == 4


def test_selection_keeps_whole_photos_and_respects_quota() -> None:
    selection = select_smoke_sample(_rows(), seed=1, photos=3, crops_per_photo=2)
    photos = {row["source_photo_id"] for row in selection}
    assert len(photos) == 3
    assert len(selection) == 6
    counts = {p: sum(1 for r in selection if r["source_photo_id"] == p) for p in photos}
    assert set(counts.values()) == {2}


def test_selection_never_touches_non_development_splits() -> None:
    rows = _rows(split="train") + _rows(photos=4, crops=3, split="test")
    selection = select_smoke_sample(rows, seed=3, photos=2, crops_per_photo=2)
    assert {row["split"] for row in selection} == {"train"}


def test_selection_respects_availability_filter() -> None:
    rows = _rows()
    available = {r["filename"] for r in rows if r["source_photo_id"] in {"signs_0", "signs_1"}}
    selection = select_smoke_sample(
        rows, seed=5, photos=2, crops_per_photo=2, available_filenames=available
    )
    assert {row["source_photo_id"] for row in selection} == {"signs_0", "signs_1"}


def test_selection_raises_rather_than_returning_short() -> None:
    with pytest.raises(RuntimeError, match="need 99 photos"):
        select_smoke_sample(_rows(), seed=1, photos=99, crops_per_photo=2)
    with pytest.raises(RuntimeError, match="need 1 photos"):
        select_smoke_sample(_rows(crops=1), seed=1, photos=1, crops_per_photo=5)


def test_selection_rejects_nonsense_quotas() -> None:
    with pytest.raises(ValueError):
        select_smoke_sample(_rows(), seed=1, photos=0, crops_per_photo=1)


def test_has_thai_discriminates_scripts() -> None:
    assert has_thai("กี่")
    assert has_thai("SINGHA ไทย")
    assert not has_thai("NET CONTENTS 320 ml.")
    assert not has_thai("")


def test_selection_excludes_english_only_regions_by_default() -> None:
    """TEMS is multiscript; an unfiltered sample would carry no Thai at all."""
    rows = _rows(photos=3, crops=3)
    english = _rows(photos=3, crops=3)
    for index, row in enumerate(english):
        row["source_photo_id"] = f"packaging_{index}"
        row["image_id"] = f"en{index:03d}"
        row["filename"] = f"en{index:03d}_x.jpg"
        row["label"] = "NET CONTENTS 320 ml."
    selection = select_smoke_sample(rows + english, seed=11, photos=3, crops_per_photo=2)
    assert all(has_thai(row["label"]) for row in selection)
    assert not any(row["source_photo_id"].startswith("packaging_") for row in selection)


def test_selection_can_opt_out_of_thai_filter() -> None:
    english = _rows(photos=2, crops=2)
    for row in english:
        row["label"] = "ABC"
    selection = select_smoke_sample(
        english, seed=1, photos=2, crops_per_photo=2, require_thai=False
    )
    assert len(selection) == 4
    with pytest.raises(RuntimeError):
        select_smoke_sample(english, seed=1, photos=2, crops_per_photo=2)


def test_selection_manifest_records_provenance() -> None:
    selection = select_smoke_sample(_rows(), seed=2, photos=2, crops_per_photo=2)
    manifest = selection_manifest(selection, seed=2, splits=("train",))
    assert manifest["seed"] == 2
    assert manifest["region_count"] == 4
    assert manifest["photo_count"] == 2
    assert manifest["splits"] == ["train"]
    assert set(manifest["regions"][0]) == {
        "source_photo_id",
        "image_id",
        "filename",
        "label",
        "image_width",
        "image_height",
        "split",
    }
