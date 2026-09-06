"""Build and verify the exact, calibration-only Stage 0 model-input bundle."""

from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

from labbs2026.step3 import sha256_file


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _zip_write_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload, compresslevel=9)


def build_calibration_bundle(
    review_dir: Path, config_path: Path, output_path: Path
) -> dict[str, Any]:
    """Package only approved calibration pairs/conditions; omit locked stimuli."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    calibration_ids = set(config["allocation"]["calibration_pair_ids"])
    locked_ids = set(config["allocation"]["locked_validation_pair_ids"])
    condition_ids = set(
        config["render_condition_selection"]["selected_condition_ids"]
    )
    if calibration_ids & locked_ids:
        raise ValueError("calibration and locked-validation pair IDs overlap")

    all_pairs = json.loads((review_dir / "resolved_pairs.json").read_text("utf-8"))
    all_renders = json.loads((review_dir / "render_manifest.json").read_text("utf-8"))
    selected_pairs = sorted(
        (pair for pair in all_pairs if pair["pair_id"] in calibration_ids),
        key=lambda pair: pair["pair_id"],
    )
    selected_renders = sorted(
        (
            row
            for row in all_renders
            if row["pair_id"] in calibration_ids
            and row["condition_id"] in condition_ids
        ),
        key=lambda row: (row["pair_id"], row["condition_id"]),
    )
    if {pair["pair_id"] for pair in selected_pairs} != calibration_ids:
        raise ValueError("review artifact is missing a frozen calibration pair")
    if {row["pair_id"] for row in selected_renders} != calibration_ids:
        raise ValueError("review artifact is missing a calibration rendering")
    if {row["condition_id"] for row in selected_renders} != condition_ids:
        raise ValueError("review artifact is missing a frozen rendering condition")

    payloads: dict[str, bytes] = {
        "resolved_pairs.json": _json_bytes(selected_pairs),
        "render_manifest.json": _json_bytes(selected_renders),
    }
    for row in selected_renders:
        for key in ("image_a_path", "image_b_path"):
            relative = row[key]
            payloads[relative] = (review_dir / relative).read_bytes()

    file_hashes = {
        name: hashlib.sha256(payload).hexdigest()
        for name, payload in sorted(payloads.items())
    }
    manifest = {
        "schema_version": 1,
        "scientific_scope": "STAGE0_CALIBRATION_ONLY",
        "source_review_packet_sha256": sha256_file(review_dir / "review_packet.json"),
        "allocation_sha256": config["allocation"]["sha256"],
        "calibration_pair_count": len(calibration_ids),
        "locked_validation_pair_count_in_bundle": 0,
        "render_condition_count": len(condition_ids),
        "pair_condition_count": len(selected_renders),
        "rendered_stimulus_count": len(selected_renders) * 2,
        "calibration_pair_ids": sorted(calibration_ids),
        "render_condition_ids": sorted(condition_ids),
        "file_sha256": file_hashes,
    }
    payloads["bundle_manifest.json"] = _json_bytes(manifest)
    payloads["review_packet.json"] = _json_bytes(
        {
            "schema_version": 1,
            "status": "FROZEN_CALIBRATION_INPUT_SUBSET",
            "scientific_scope": "STAGE0_CALIBRATION_ONLY",
            "source_review_packet_sha256": manifest["source_review_packet_sha256"],
            "allocation_sha256": manifest["allocation_sha256"],
            "locked_validation_pair_count_in_bundle": 0,
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite calibration bundle: {output_path}")
    with zipfile.ZipFile(output_path, "w") as archive:
        for name, payload in sorted(payloads.items()):
            _zip_write_bytes(archive, name, payload)
    return {**manifest, "bundle_sha256": sha256_file(output_path)}


def extract_and_verify_calibration_bundle(
    bundle_path: Path, destination: Path, expected_sha256: str
) -> dict[str, Any]:
    if sha256_file(bundle_path) != expected_sha256:
        raise RuntimeError("calibration input bundle SHA-256 mismatch")
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(bundle_path) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError("calibration input bundle contains an unsafe path")
        archive.extractall(destination)
    manifest = json.loads((destination / "bundle_manifest.json").read_text("utf-8"))
    for relative, expected in manifest["file_sha256"].items():
        path = destination / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"calibration bundle member hash mismatch: {relative}")
    if manifest.get("locked_validation_pair_count_in_bundle") != 0:
        raise RuntimeError("calibration bundle contains locked-validation pairs")
    return manifest


def verify_bundle_roundtrip(bundle_path: Path, expected_sha256: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="labbs-stage0-bundle-") as temporary:
        return extract_and_verify_calibration_bundle(
            bundle_path, Path(temporary) / "extracted", expected_sha256
        )
