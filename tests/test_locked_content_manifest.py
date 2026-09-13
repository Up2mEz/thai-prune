from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from labbs2026.stage0.locked_content_manifest import (
    build_locked_content_manifest,
    canonical_manifest_bytes,
    normalize_relative_posix,
    verify_expanded_locked_content,
)


def test_manifest_and_expanded_tree_use_exact_content_identity(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("a.json", b"{}\n")
        bundle.writestr("renders/x.png", b"png")
    manifest = build_locked_content_manifest(archive)
    assert [row["path"] for row in manifest["files"]] == ["a.json", "renders/x.png"]
    assert manifest["member_count"] == 2
    json.loads(canonical_manifest_bytes(manifest))
    expanded = tmp_path / "expanded"
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(expanded)
    result = verify_expanded_locked_content(expanded, manifest)
    assert result["exact_path_set"] is True
    assert result["all_sha256_match"] is True


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b"])
def test_manifest_rejects_unsafe_or_ambiguous_paths(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(name, b"x")
    with pytest.raises(RuntimeError):
        build_locked_content_manifest(archive)


def test_normalization_rejects_backslash_path() -> None:
    with pytest.raises(RuntimeError, match="invalid or ambiguous"):
        normalize_relative_posix("a\\b")


def test_manifest_rejects_case_collisions(tmp_path: Path) -> None:
    archive = tmp_path / "collision.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("A.json", b"a")
        bundle.writestr("a.json", b"b")
    with pytest.raises(RuntimeError, match="case-colliding"):
        build_locked_content_manifest(archive)


def test_expanded_tree_rejects_unexpected_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "unexpected").write_bytes(b"x")
    manifest = {"files": []}
    with pytest.raises(RuntimeError, match="path-set mismatch"):
        verify_expanded_locked_content(source, manifest)
