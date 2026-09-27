"""Prepare the non-model visual review for the measurement-contract pilot."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from labbs2026.stage0.rendering import _rasterize, _shape, sha256_file


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _outside_cell_mask(
    canvas_size: tuple[int, int], target_cell: tuple[int, int, int, int]
) -> np.ndarray:
    width, height = canvas_size
    left, top, right, bottom = target_cell
    mask = np.ones((height, width), dtype=bool)
    mask[top:bottom, left:right] = False
    return mask


def _anchor_mask(
    *,
    font_path: Path,
    font_size: int,
    canvas_size: tuple[int, int],
    item_y: tuple[int, int],
    anchor_cells: list[tuple[int, int]],
    anchors: list[str],
    separator_rectangles: list[tuple[int, int, int, int]],
) -> np.ndarray:
    width, height = canvas_size
    combined = np.zeros((height, width), dtype=np.uint8)
    for text, (left, right) in zip(anchors, anchor_cells, strict=True):
        run = _shape(text, font_path, font_size)
        origin = (
            round((left + right) / 2 - (run.bbox[0] + run.bbox[2]) / 2),
            round((item_y[0] + item_y[1]) / 2 - (run.bbox[1] + run.bbox[3]) / 2),
        )
        rendered = _rasterize(run, canvas_size, origin)
        ys, xs = np.where(rendered > 0)
        if not len(xs) or xs.min() < left or xs.max() >= right:
            raise ValueError(f"ANCHOR_INK_OUTSIDE_CELL:{text}:{font_size}")
        if ys.min() < item_y[0] or ys.max() >= item_y[1]:
            raise ValueError(f"ANCHOR_INK_OUTSIDE_VERTICAL_INTERVAL:{text}:{font_size}")
        combined = np.maximum(combined, rendered)
    for left, top, right, bottom in separator_rectangles:
        combined[top:bottom, left:right] = 255
    return combined


def add_surrounding_layout(
    isolated_target: Image.Image,
    *,
    anchor_mask: np.ndarray,
    target_cell: tuple[int, int, int, int],
) -> tuple[Image.Image, dict[str, Any]]:
    """Add fixed context outside a target cell while preserving target bytes."""

    isolated = np.asarray(isolated_target.convert("RGB"), dtype=np.uint8)
    height, width, channels = isolated.shape
    if channels != 3 or anchor_mask.shape != (height, width):
        raise ValueError("PILOT_LAYOUT_SHAPE_MISMATCH")
    outside = _outside_cell_mask((width, height), target_cell)
    if np.any(isolated[outside] != 255):
        raise ValueError("ISOLATED_TARGET_INK_OUTSIDE_TARGET_CELL")
    if np.any(anchor_mask[~outside] != 0):
        raise ValueError("ANCHOR_OR_SEPARATOR_INK_INSIDE_TARGET_CELL")

    layer = np.repeat((255 - anchor_mask)[:, :, None], 3, axis=2)
    surrounded = np.minimum(isolated, layer)
    left, top, right, bottom = target_cell
    isolated_crop = isolated[top:bottom, left:right]
    surrounded_crop = surrounded[top:bottom, left:right]
    identity = np.array_equal(isolated_crop, surrounded_crop)
    if not identity:
        raise ValueError("TARGET_PIXEL_IDENTITY_FAILURE")
    metadata = {
        "target_pixel_identity": "PASS",
        "target_layer_sha256_B": _sha256_bytes(isolated_crop.tobytes()),
        "target_layer_sha256_C": _sha256_bytes(surrounded_crop.tobytes()),
        "anchor_layer_sha256": _sha256_bytes(anchor_mask.tobytes()),
        "non_target_layer_sha256_C": _sha256_bytes(surrounded[outside].tobytes()),
        "full_image_pixel_sha256_C": _sha256_bytes(surrounded.tobytes()),
    }
    return Image.fromarray(surrounded, mode="RGB"), metadata


def _contact_sheet(
    rows: list[dict[str, Any]], output_path: Path, *, title: str
) -> None:
    label_font = ImageFont.load_default(size=16)
    preview = 176
    label_width = 245
    row_height = 194
    sheet = Image.new(
        "RGB", (label_width + 2 * preview + 30, 52 + len(rows) * row_height), "white"
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 8), title, fill="black", font=label_font)
    draw.text((label_width, 30), "B isolated", fill="black", font=label_font)
    draw.text((label_width + preview, 30), "C surrounded", fill="black", font=label_font)
    for index, row in enumerate(rows):
        top = 50 + index * row_height
        draw.text(
            (10, top + 72),
            f"{row['pair_id']} / {row['member']}",
            fill="black",
            font=label_font,
        )
        for column, image in enumerate((row["image_B"], row["image_C"])):
            shown = image.copy()
            shown.thumbnail((preview - 8, preview - 8))
            sheet.paste(shown, (label_width + column * preview, top + 8))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=False)


def build_visual_review(
    *, root: Path, config_path: Path, output_dir: Path
) -> dict[str, Any]:
    """Build B/C contact sheets and byte-level validation without model use."""

    root = root.resolve()
    config_path = config_path.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    config = _load_yaml(config_path)
    if config["prohibitions"]["inference_authorized"] is not False:
        raise ValueError("PILOT_INFERENCE_MUST_REMAIN_UNAUTHORIZED")

    design = _load_yaml(root / config["source_design"])
    inventory = _load_yaml(root / "configs/stage0/candidate_pairs.yaml")
    selected_by_component = config["selection"]["selected_pairs"]
    selected = [pair_id for rows in selected_by_component.values() for pair_id in rows]
    if len(selected) != len(set(selected)) or len(selected) != 25:
        raise ValueError("PILOT_SELECTED_PAIR_COUNT_OR_DUPLICATE_FAILURE")
    open_ids = set(design["allocation"]["calibration_pair_ids"])
    locked_ids = set(design["allocation"]["locked_validation_pair_ids"])
    if not set(selected) <= open_ids or set(selected) & locked_ids:
        raise ValueError("PILOT_SELECTION_NOT_OPEN_ONLY")
    selected_hash = _sha256_bytes("\n".join(sorted(selected)).encode("utf-8"))
    if selected_hash != config["selection"]["selected_id_set_sha256"]:
        raise ValueError("PILOT_SELECTION_HASH_MISMATCH")

    pair_by_id = {pair["pair_id"]: pair for pair in inventory["pairs"]}
    source_bundle = root / config["source_bundle"]
    if sha256_file(source_bundle) != config["source_bundle_sha256"]:
        raise ValueError("PILOT_SOURCE_BUNDLE_HASH_MISMATCH")

    canvas_size = tuple(config["line_layout"]["canvas_size"])
    item_y = tuple(config["line_layout"]["vertical_item_interval"])
    cells = config["line_layout"]["cells_half_open"]
    target_cell = (
        int(cells["target"][0]),
        int(item_y[0]),
        int(cells["target"][1]),
        int(item_y[1]),
    )
    anchor_cells = [
        tuple(cells[key]) for key in ("anchor_1", "anchor_2", "anchor_3", "anchor_4")
    ]
    rectangles = [
        (int(row["x"][0]), int(row["y"][0]), int(row["x"][1]), int(row["y"][1]))
        for row in config["line_layout"]["separator_rectangles_half_open"]
    ]

    output_dir.mkdir(parents=True, exist_ok=False)
    contact_dir = output_dir / "contact_sheets"
    validation_rows: list[dict[str, Any]] = []
    contact_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    non_target_hashes: dict[str, set[str]] = defaultdict(set)

    with zipfile.ZipFile(source_bundle) as bundle:
        manifest = json.loads(bundle.read("render_manifest.json"))
        bundle_manifest = json.loads(bundle.read("bundle_manifest.json"))
        if bundle_manifest["locked_validation_pair_count_in_bundle"] != 0:
            raise ValueError("PILOT_SOURCE_BUNDLE_CONTAINS_LOCKED_PAIRS")
        records = {
            (row["pair_id"], row["condition_id"]): row
            for row in manifest
            if row["pair_id"] in set(selected)
        }
        for component, component_pairs in selected_by_component.items():
            for condition_id in config["render_conditions"]:
                sample = records[(component_pairs[0], condition_id)]
                font_path = root / sample["font_path"]
                mask = _anchor_mask(
                    font_path=font_path,
                    font_size=int(sample["font_size"]),
                    canvas_size=canvas_size,
                    item_y=item_y,
                    anchor_cells=anchor_cells,
                    anchors=list(config["conditions"]["C_line_layout_transcription"]["anchors"]),
                    separator_rectangles=rectangles,
                )
                for pair_id in component_pairs:
                    row = records[(pair_id, condition_id)]
                    if row["component_type"] != component:
                        raise ValueError("PILOT_COMPONENT_ASSIGNMENT_MISMATCH")
                    for member in ("a", "b"):
                        path = row[f"image_{member}_path"]
                        source_png = bundle.read(path)
                        if _sha256_bytes(source_png) != row[f"image_{member}_sha256"]:
                            raise ValueError("PILOT_SOURCE_PNG_HASH_MISMATCH")
                        image_B = Image.open(io.BytesIO(source_png)).convert("RGB")
                        image_C, identity = add_surrounding_layout(
                            image_B, anchor_mask=mask, target_cell=target_cell
                        )
                        non_target_hashes[condition_id].add(
                            identity["non_target_layer_sha256_C"]
                        )
                        validation_rows.append(
                            {
                                "pair_id": pair_id,
                                "component_type": component,
                                "member": member,
                                "condition_id": condition_id,
                                "font_id": row["font_id"],
                                "font_size": row["font_size"],
                                "source_B_path": path,
                                "source_B_png_sha256": row[f"image_{member}_sha256"],
                                **identity,
                            }
                        )
                        contact_rows[(component, condition_id)].append(
                            {
                                "pair_id": pair_id,
                                "member": member,
                                "image_B": image_B,
                                "image_C": image_C,
                            }
                        )

    if len(validation_rows) != 200:
        raise ValueError("PILOT_VISUAL_OBSERVATION_COUNT_MISMATCH")
    if any(len(values) != 1 for values in non_target_hashes.values()):
        raise ValueError("PILOT_NON_TARGET_LAYER_NOT_INVARIANT")

    contact_paths: list[str] = []
    for (component, condition_id), rows in sorted(contact_rows.items()):
        filename = f"{component.lower()}__{condition_id}.png"
        path = contact_dir / filename
        _contact_sheet(rows, path, title=f"{component} / {condition_id}")
        contact_paths.append(path.relative_to(root).as_posix())

    report = {
        "schema_version": 1,
        "status": "PASS_PENDING_FINAL_HUMAN_VISUAL_PROTOCOL_APPROVAL",
        "scientific_use": "PRE_INFERENCE_NON_MODEL_VALIDATION_ONLY",
        "model_inference_performed": False,
        "git_commit": _git_commit(root),
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": sha256_file(config_path),
        "protocol_path": config["protocol"],
        "protocol_sha256": sha256_file(root / config["protocol"]),
        "source_bundle_sha256": sha256_file(source_bundle),
        "selected_pair_count": 25,
        "selected_id_set_sha256": selected_hash,
        "target_observation_count": len(validation_rows),
        "locked_pair_count": 0,
        "target_pixel_identity_failures": 0,
        "non_target_invariance_failures": 0,
        "contact_sheets": contact_paths,
        "non_target_layer_sha256_by_condition": {
            key: next(iter(values)) for key, values in sorted(non_target_hashes.items())
        },
        "rows": validation_rows,
        "human_review_status": "PENDING",
    }
    report_path = output_dir / "pixel_identity_validation.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    index = [
        "# B/C Measurement-Contract Pilot Contact Sheets",
        "",
        "**Status:** `PENDING_FINAL_HUMAN_VISUAL_PROTOCOL_APPROVAL`",
        "",
        "Left is Condition B (isolated target). Right is Condition C (the exact",
        "B pixels plus frozen surrounding layout outside the target cell).",
        "No model inference was used to create these sheets.",
        "",
    ]
    for relative in contact_paths:
        filename = Path(relative).name
        index.extend((f"## `{filename}`", "", f"![{filename}](contact_sheets/{filename})", ""))
    (output_dir / "CONTACT_SHEETS.md").write_text("\n".join(index), encoding="utf-8")
    return report
