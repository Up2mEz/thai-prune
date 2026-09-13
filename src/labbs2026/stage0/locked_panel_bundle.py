"""Build the authorized locked-panel source bundle outside Git."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import yaml

from labbs2026.stage0.bundle import _json_bytes, _zip_write_bytes
from labbs2026.step3 import sha256_file


def build_locked_source_bundle(
    review_dir: Path,
    design_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    design = yaml.safe_load(design_path.read_text("utf-8"))
    locked_ids = set(design["allocation"]["locked_validation_pair_ids"])
    calibration_ids = set(design["allocation"]["calibration_pair_ids"])
    condition_ids = set(design["render_condition_selection"]["selected_condition_ids"])
    if locked_ids & calibration_ids or len(locked_ids) != 100:
        raise RuntimeError("frozen pair allocation is invalid")
    if sha256_file(review_dir / "review_packet.json") != design["source_review_packet_sha256"]:
        raise RuntimeError("candidate-review packet hash mismatch")

    pairs = json.loads((review_dir / "resolved_pairs.json").read_text("utf-8"))
    renders = json.loads((review_dir / "render_manifest.json").read_text("utf-8"))
    selected_pairs = sorted(
        (row for row in pairs if row["pair_id"] in locked_ids),
        key=lambda row: row["pair_id"],
    )
    selected_renders = sorted(
        (
            row
            for row in renders
            if row["pair_id"] in locked_ids and row["condition_id"] in condition_ids
        ),
        key=lambda row: (row["pair_id"], row["condition_id"]),
    )
    if {row["pair_id"] for row in selected_pairs} != locked_ids:
        raise RuntimeError("candidate review is missing a locked pair")
    if len(selected_renders) != 400:
        raise RuntimeError("expected 400 locked pair-condition rows")
    if {row["pair_id"] for row in selected_renders} != locked_ids:
        raise RuntimeError("candidate review is missing a locked rendering")
    if {row["condition_id"] for row in selected_renders} != condition_ids:
        raise RuntimeError("candidate review is missing a registered condition")

    payloads: dict[str, bytes] = {
        "resolved_pairs.json": _json_bytes(selected_pairs),
        "render_manifest.json": _json_bytes(selected_renders),
    }
    for row in selected_renders:
        for key in ("image_a_path", "image_b_path"):
            relative = row[key]
            payload = (review_dir / relative).read_bytes()
            if hashlib.sha256(payload).hexdigest() != row[key.replace("path", "sha256")]:
                raise RuntimeError(f"registered image hash mismatch: {relative}")
            payloads[relative] = payload

    file_hashes = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in sorted(payloads.items())
    }
    manifest = {
        "schema_version": 1,
        "scientific_scope": "AUTHORIZED_LOCKED_PANEL_SOURCE_448_RGB",
        "source_review_packet_sha256": design["source_review_packet_sha256"],
        "allocation_sha256": design["allocation"]["sha256"],
        "registered_locked_pair_count": 100,
        "render_condition_count": 4,
        "pair_condition_count": 400,
        "source_png_count": 800,
        "file_sha256": file_hashes,
    }
    payloads["bundle_manifest.json"] = _json_bytes(manifest)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite locked source bundle: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as archive:
        for name, payload in sorted(payloads.items()):
            _zip_write_bytes(archive, name, payload)
    return {**manifest, "bundle_sha256": sha256_file(output_path)}


def verify_locked_source_bundle(bundle_path: Path, expected_sha256: str) -> dict[str, Any]:
    if sha256_file(bundle_path) != expected_sha256:
        raise RuntimeError("locked source bundle hash mismatch")
    with zipfile.ZipFile(bundle_path) as archive:
        manifest = json.loads(archive.read("bundle_manifest.json"))
        names = set(archive.namelist())
        for relative, expected in manifest["file_sha256"].items():
            if relative not in names or hashlib.sha256(archive.read(relative)).hexdigest() != expected:
                raise RuntimeError(f"locked bundle member mismatch: {relative}")
    if manifest["registered_locked_pair_count"] != 100 or manifest["source_png_count"] != 800:
        raise RuntimeError("locked source bundle scope mismatch")
    return manifest
