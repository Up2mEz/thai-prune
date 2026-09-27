"""Content identity for immutable locked-source archives and expanded trees."""

from __future__ import annotations

import hashlib
import json
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_relative_posix(path: str) -> str:
    if not path or "\\" in path or unicodedata.normalize("NFC", path) != path:
        raise RuntimeError(f"invalid or ambiguous archive path: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise RuntimeError(f"unsafe archive path: {path!r}")
    normalized = pure.as_posix()
    if normalized != path.rstrip("/"):
        raise RuntimeError(f"ambiguous normalized archive path: {path!r}")
    if pure.parts[0].endswith(":"):
        raise RuntimeError(f"drive-qualified archive path: {path!r}")
    return normalized


def build_locked_content_manifest(archive_path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    exact_paths: set[str] = set()
    casefold_paths: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            normalized = normalize_relative_posix(info.filename)
            folded = normalized.casefold()
            if normalized in exact_paths:
                raise RuntimeError(f"duplicate archive path: {normalized}")
            if folded in casefold_paths:
                raise RuntimeError(f"case-colliding archive path: {normalized}")
            exact_paths.add(normalized)
            casefold_paths.add(folded)
            unix_mode = info.external_attr >> 16
            file_type = stat.S_IFMT(unix_mode)
            if file_type == stat.S_IFLNK:
                raise RuntimeError(f"symlink archive entry: {normalized}")
            if info.is_dir():
                if file_type not in (0, stat.S_IFDIR):
                    raise RuntimeError(f"non-directory archive entry type: {normalized}")
                continue
            if file_type not in (0, stat.S_IFREG):
                raise RuntimeError(f"non-regular archive entry: {normalized}")
            payload = archive.read(info)
            if len(payload) != info.file_size:
                raise RuntimeError(f"archive member size mismatch: {normalized}")
            records.append(
                {
                    "path": normalized,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    records.sort(key=lambda row: row["path"])
    return {
        "schema_version": 1,
        "identity_semantics": "EXACT_RELATIVE_PATH_SIZE_AND_UNCOMPRESSED_SHA256",
        "original_transport_archive_sha256": sha256_file(archive_path),
        "member_count": len(records),
        "total_uncompressed_bytes": sum(row["bytes"] for row in records),
        "files": records,
    }


def verify_expanded_locked_content(
    source_root: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    expected = {row["path"]: row for row in manifest["files"]}
    observed: dict[str, Path] = {}
    casefold_paths: set[str] = set()
    for path in source_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"symlink in expanded source: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"non-regular expanded source entry: {path}")
        relative = normalize_relative_posix(path.relative_to(source_root).as_posix())
        folded = relative.casefold()
        if relative in observed or folded in casefold_paths:
            raise RuntimeError(f"duplicate or case-colliding expanded path: {relative}")
        observed[relative] = path
        casefold_paths.add(folded)
    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        raise RuntimeError(
            f"expanded source path-set mismatch: missing={len(missing)}, "
            f"unexpected={len(unexpected)}"
        )
    for relative, expected_record in expected.items():
        path = observed[relative]
        if path.stat().st_size != expected_record["bytes"]:
            raise RuntimeError(f"expanded source size mismatch: {relative}")
        if sha256_file(path) != expected_record["sha256"]:
            raise RuntimeError(f"expanded source hash mismatch: {relative}")
    return {
        "member_count": len(observed),
        "total_uncompressed_bytes": sum(path.stat().st_size for path in observed.values()),
        "exact_path_set": True,
        "all_sizes_match": True,
        "all_sha256_match": True,
    }

