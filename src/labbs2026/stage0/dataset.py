"""Build the non-model Stage 0 candidate review inventory and render audit."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

from labbs2026.preflight import inspect_repository
from labbs2026.stage0.adequacy import assess_pair_inventory
from labbs2026.stage0.rendering import (
    metadata_dict,
    render_pair,
    renderer_versions,
    sha256_file,
)
from labbs2026.stage0.unicode_checks import validate_pair


LEXICAL_STATUSES = {"REAL", "CONSTRUCTED", "UNCERTAIN"}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(value: str) -> float:
        channels = [int(value.lstrip("#")[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def _contact_sheet(
    rows: list[dict[str, Any]], run_dir: Path, output_path: Path
) -> None:
    label_font = ImageFont.load_default(size=18)
    cell_size = 176
    row_height = 220
    sheet = Image.new("RGB", (3 * cell_size + 60, len(rows) * row_height + 50), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), "A member | B member | difference mask", fill="black", font=label_font)
    for row_index, row in enumerate(rows):
        top = 45 + row_index * row_height
        draw.text((10, top), row["pair_id"], fill="black", font=label_font)
        for column, key in enumerate(("image_a_path", "image_b_path", "difference_mask_path")):
            image = Image.open(run_dir / row[key]).convert("RGB")
            image.thumbnail((cell_size - 12, cell_size - 12))
            left = 10 + column * cell_size
            sheet.paste(image, (left, top + 28))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=False)


def build_candidate_review(
    inventory_path: Path,
    rendering_path: Path,
    calibration_design_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = Path(__file__).resolve().parents[3]
    preflight = inspect_repository(root)
    if not preflight.valid:
        raise RuntimeError(f"clean repository preflight required: {preflight}")
    inventory = _load_yaml(inventory_path)
    rendering = _load_yaml(rendering_path)
    calibration_design = (
        _load_yaml(calibration_design_path) if calibration_design_path else None
    )
    commit = _git_commit(root)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / "runs" / "stage0" / "candidate_review" / f"{timestamp}_{commit[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)

    pairs = inventory.get("pairs", [])
    planning = inventory.get("planning", {})
    pair_ids = [pair.get("pair_id") for pair in pairs]
    duplicate_ids = sorted(pair_id for pair_id, count in Counter(pair_ids).items() if count > 1)
    unordered = [tuple(sorted((pair["text_a"], pair["text_b"]))) for pair in pairs]
    duplicate_strings = sorted(pair for pair, count in Counter(unordered).items() if count > 1)
    inventory_issues: list[str] = []
    if duplicate_ids:
        inventory_issues.append(f"DUPLICATE_PAIR_IDS:{duplicate_ids}")
    if duplicate_strings:
        inventory_issues.append(f"DUPLICATE_UNORDERED_PAIRS:{duplicate_strings}")
    for pair in pairs:
        for member in ("a", "b"):
            status = pair.get(f"lexical_status_{member}")
            if status not in LEXICAL_STATUSES:
                inventory_issues.append(
                    f"{pair.get('pair_id')}:INVALID_LEXICAL_STATUS_{member.upper()}:{status}"
                )

    canvas = (int(rendering["canvas"]["width"]), int(rendering["canvas"]["height"]))
    foreground = rendering["colors"]["foreground"]
    background = rendering["colors"]["background"]
    difference_threshold = int(
        rendering["difference_mask"]["coverage_delta_threshold"]
    )
    rerender_audit = bool(
        rendering["difference_mask"].get("deterministic_rerender_audit", False)
    )
    font_by_id = {font["font_id"]: font for font in rendering["fonts"]}
    for font in rendering["fonts"]:
        font_path = root / font["path"]
        if sha256_file(font_path) != font["sha256"]:
            inventory_issues.append(f"FONT_HASH_MISMATCH:{font['font_id']}")

    resolved_pairs: list[dict[str, Any]] = []
    render_records: list[dict[str, Any]] = []
    preview_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        unicode_result = validate_pair(
            pair["text_a"], pair["text_b"], pair["difference_rule"]
        )
        pair_record = {
            **pair,
            "unicode": {
                "codepoints_a": unicode_result.codepoints_a,
                "codepoints_b": unicode_result.codepoints_b,
                "normalization_a": unicode_result.normalization_a,
                "normalization_b": unicode_result.normalization_b,
            },
            "automated_unicode_status": "PASS" if unicode_result.valid else "FAIL",
            "automated_unicode_issues": unicode_result.issues,
            "human_linguistic_status": "PENDING",
            "human_notes": None,
        }
        resolved_pairs.append(pair_record)
        if not unicode_result.valid:
            inventory_issues.extend(
                f"{pair['pair_id']}:{issue}" for issue in unicode_result.issues
            )

        for font in rendering["fonts"]:
            for font_size in rendering["font_sizes"]:
                for position in rendering["position_offsets"]:
                    condition_id = f"{font['font_id']}__{font_size}__{position['position_id']}"
                    relative_dir = Path("renders") / condition_id
                    absolute_dir = run_dir / relative_dir
                    absolute_dir.mkdir(parents=True, exist_ok=True)
                    image_a, image_b, difference, render_metadata = render_pair(
                        pair["text_a"],
                        pair["text_b"],
                        font_path=root / font["path"],
                        font_size=int(font_size),
                        canvas=canvas,
                        position_offset=(int(position["x"]), int(position["y"])),
                        foreground=foreground,
                        background=background,
                        difference_threshold=difference_threshold,
                    )
                    deterministic_rerender_status = "NOT_REQUESTED"
                    if rerender_audit:
                        repeated = render_pair(
                            pair["text_a"],
                            pair["text_b"],
                            font_path=root / font["path"],
                            font_size=int(font_size),
                            canvas=canvas,
                            position_offset=(int(position["x"]), int(position["y"])),
                            foreground=foreground,
                            background=background,
                            difference_threshold=difference_threshold,
                        )
                        deterministic_rerender_status = (
                            "PASS"
                            if image_a.tobytes() == repeated[0].tobytes()
                            and image_b.tobytes() == repeated[1].tobytes()
                            and difference.tobytes() == repeated[2].tobytes()
                            and render_metadata == repeated[3]
                            else "FAIL"
                        )
                    image_a_path = relative_dir / f"{pair['pair_id']}__a.png"
                    image_b_path = relative_dir / f"{pair['pair_id']}__b.png"
                    mask_path = relative_dir / f"{pair['pair_id']}__difference.png"
                    image_a.save(run_dir / image_a_path, format="PNG", optimize=False)
                    image_b.save(run_dir / image_b_path, format="PNG", optimize=False)
                    difference.save(run_dir / mask_path, format="PNG", optimize=False)
                    values = metadata_dict(render_metadata)
                    render_issues: list[str] = []
                    if values["missing_glyph"]:
                        render_issues.append("MISSING_GLYPH")
                    if values["ink_pixels_a"] <= 0 or values["ink_pixels_b"] <= 0:
                        render_issues.append("EMPTY_RENDER")
                    if values["critical_pixel_area"] <= 0:
                        render_issues.append("EMPTY_DIFFERENCE_MASK")
                    if tuple(values["actual_origin_delta"]) != (0, 0):
                        render_issues.append("GLOBAL_LAYOUT_SHIFT")
                    if deterministic_rerender_status == "FAIL":
                        render_issues.append("NONDETERMINISTIC_RERENDER")
                    record = {
                        "pair_id": pair["pair_id"],
                        "component_type": pair["component_type"],
                        "condition_id": condition_id,
                        "font_id": font["font_id"],
                        "font_path": font["path"],
                        "font_sha256": font["sha256"],
                        "font_size": int(font_size),
                        "canvas_size": list(canvas),
                        "position_id": position["position_id"],
                        "position_offset": [int(position["x"]), int(position["y"])],
                        "foreground": foreground,
                        "background": background,
                        "contrast_ratio": _contrast_ratio(foreground, background),
                        "image_a_path": image_a_path.as_posix(),
                        "image_b_path": image_b_path.as_posix(),
                        "difference_mask_path": mask_path.as_posix(),
                        "image_a_sha256": sha256_file(run_dir / image_a_path),
                        "image_b_sha256": sha256_file(run_dir / image_b_path),
                        "difference_mask_sha256": sha256_file(run_dir / mask_path),
                        "render_metadata": values,
                        "deterministic_rerender_status": deterministic_rerender_status,
                        "automated_render_status": "PASS" if not render_issues else "FAIL",
                        "automated_render_issues": render_issues,
                        "human_render_status": "PENDING",
                    }
                    render_records.append(record)
                    if render_issues:
                        inventory_issues.extend(
                            f"{pair['pair_id']}:{condition_id}:{issue}"
                            for issue in render_issues
                        )
                    preview = rendering["preview_condition"]
                    if (
                        font["font_id"] == preview["font_id"]
                        and int(font_size) == int(preview["font_size"])
                        and position["position_id"] == preview["position_id"]
                    ):
                        preview_records[pair["component_type"]].append(record)

    contact_sheets: dict[str, list[str]] = {}
    for component_type, records in sorted(preview_records.items()):
        paths: list[str] = []
        for page_index, start in enumerate(range(0, len(records), 10), start=1):
            path = (
                Path("contact_sheets")
                / f"{component_type.lower()}__page_{page_index:02d}.png"
            )
            _contact_sheet(records[start : start + 10], run_dir, run_dir / path)
            paths.append(path.as_posix())
        contact_sheets[component_type] = paths

    adequacy = assess_pair_inventory(
        pairs,
        seoi_absolute_pp=float(planning["seoi_absolute_pp"]),
        seed=int(planning["allocation_seed"]),
    )
    _write_json(run_dir / "inventory_adequacy.json", adequacy)
    proposed_design: dict[str, Any] | None = None
    if calibration_design is not None:
        calibration_ids = calibration_design["allocation"]["calibration_pair_ids"]
        locked_ids = calibration_design["allocation"]["locked_validation_pair_ids"]
        condition_ids = calibration_design["render_condition_selection"][
            "selected_condition_ids"
        ]
        blank_ids = calibration_design["controls"][
            "language_candidate_bias_blank_pair_ids"
        ]
        proposal = adequacy["proposed_allocation"]
        if set(calibration_ids) != set(proposal["calibration_pair_ids"]):
            inventory_issues.append("CALIBRATION_ALLOCATION_DIFFERS_FROM_ADEQUACY_PROPOSAL")
        if set(locked_ids) != set(proposal["locked_validation_pair_ids"]):
            inventory_issues.append("LOCKED_ALLOCATION_DIFFERS_FROM_ADEQUACY_PROPOSAL")
        available_conditions = {record["condition_id"] for record in render_records}
        if not set(condition_ids) <= available_conditions:
            inventory_issues.append("PROPOSED_CONDITION_NOT_RENDERED")
        if not set(blank_ids) <= set(calibration_ids):
            inventory_issues.append("BLANK_CONTROL_PAIR_NOT_IN_CALIBRATION")
        full_calls = len(calibration_ids) * len(condition_ids) * 2
        blank_calls = len(blank_ids) * 2
        rerun_count = 2 if calibration_design["reproducibility"]["exact_rerun"] else 1
        proposed_design = {
            "status": "PROPOSED_FINAL_HUMAN_FREEZE_PENDING",
            "calibration_pair_ids": calibration_ids,
            "locked_validation_pair_ids": locked_ids,
            "selected_condition_ids": condition_ids,
            "language_candidate_bias_blank_pair_ids": blank_ids,
            "blank_control_has_visual_ground_truth": False,
            "exact_kaggle_workload": {
                "backend": calibration_design["backend"],
                "full_information_calls_per_run": full_calls,
                "language_candidate_bias_blank_calls_per_run": blank_calls,
                "calls_per_run": full_calls + blank_calls,
                "exact_rerun_count": rerun_count,
                "total_model_calls": (full_calls + blank_calls) * rerun_count,
                "locked_validation_included": False,
            },
        }
        _write_json(run_dir / "proposed_calibration_design.json", proposed_design)

    report = {
        "schema_version": 2,
        "status": "AWAITING_HUMAN_REVIEW" if not inventory_issues else "AUTOMATED_VALIDATION_FAILED",
        "scientific_use": "FORBIDDEN_BEFORE_HUMAN_FREEZE",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "inventory_path": inventory_path.relative_to(root).as_posix(),
        "inventory_sha256": sha256_file(inventory_path),
        "rendering_path": rendering_path.relative_to(root).as_posix(),
        "rendering_sha256": sha256_file(rendering_path),
        "renderer": renderer_versions(),
        "candidate_pair_count": len(pairs),
        "render_condition_count": len(rendering["fonts"]) * len(rendering["font_sizes"]) * len(rendering["position_offsets"]),
        "pair_condition_count": len(render_records),
        "rendered_stimulus_count": len(render_records) * 2,
        "component_counts": dict(Counter(pair["component_type"] for pair in pairs)),
        "lexical_status_member_counts": dict(
            Counter(
                pair[f"lexical_status_{member}"]
                for pair in pairs
                for member in ("a", "b")
            )
        ),
        "difference_mask_construction": {
            "rule": rendering["difference_mask"]["rule"],
            "coverage_delta_threshold": difference_threshold,
            "anti_aliasing": rendering["difference_mask"]["anti_aliasing"],
            "critical_pixel_area": "count of thresholded mask pixels",
            "deterministic_rerender_audit": rerender_audit,
            "global_layout_policy": rendering["global_layout"]["policy"],
            "global_layout_rejection": "reject nonzero actual origin delta; shared union-bbox origin prevents independent recentering",
        },
        "automated_issues": inventory_issues,
        "contact_sheets": contact_sheets,
        "inventory_adequacy": adequacy,
        "calibration_design_path": (
            calibration_design_path.relative_to(root).as_posix()
            if calibration_design_path
            else None
        ),
        "calibration_design_sha256": (
            sha256_file(calibration_design_path) if calibration_design_path else None
        ),
        "proposed_calibration_design": proposed_design,
        "human_decisions_required": [
            "linguistic validity and admissibility for every pair",
            "rendering-factor pool and visible distinction validity",
            "usable pair inventory before calibration allocation",
        ],
    }
    _write_json(run_dir / "resolved_pairs.json", resolved_pairs)
    _write_json(run_dir / "render_manifest.json", render_records)
    _write_json(run_dir / "review_packet.json", report)
    return run_dir, report
