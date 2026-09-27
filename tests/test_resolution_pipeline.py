from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from labbs2026.stage0.resolution_pipeline import materialize_budget_image


def _source(path: Path) -> None:
    x = np.arange(448, dtype=np.uint8)
    array = np.stack(np.meshgrid(x, x, indexing="ij") + (np.full((448, 448), 127, dtype=np.uint8),), axis=-1)
    Image.fromarray(array, mode="RGB").save(path, format="PNG")


def test_downsampling_is_deterministic_and_records_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _source(source)
    first = materialize_budget_image(source, tmp_path / "a.png", (392, 392))
    second = materialize_budget_image(source, tmp_path / "b.png", (392, 392))
    assert first["output_file_sha256"] == second["output_file_sha256"]
    assert first["output_pixel_sha256"] == second["output_pixel_sha256"]
    assert first["interpolation"] == "Image.Resampling.BICUBIC"


def test_full_budget_preserves_exact_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _source(source)
    record = materialize_budget_image(source, tmp_path / "full.png", (448, 448))
    assert record["source_file_sha256"] == record["output_file_sha256"]


def test_pipeline_refuses_unregistered_size_and_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _source(source)
    with pytest.raises(ValueError):
        materialize_budget_image(source, tmp_path / "bad.png", (336, 336))
    output = tmp_path / "valid.png"
    materialize_budget_image(source, output, (224, 224))
    with pytest.raises(FileExistsError):
        materialize_budget_image(source, output, (224, 224))
