"""Calibration-only diagnostics for Checkpoint D.

The first repaired exact run is the sole analysis source.  The second exact
run is used only to audit reproducibility and is never pooled into estimates.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import yaml
from scipy.stats import spearmanr

from labbs2026.stage0.metrics import compare_reproducibility
from labbs2026.step3 import sha256_file


FULL_INFORMATION = "FULL_INFORMATION"
BLANK_CONTROL = "LANGUAGE_CANDIDATE_BIAS_BLANK"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected YAML mapping: {path}")
    return value


def _accuracy(rows: Sequence[dict[str, Any]]) -> float | None:
    return (
        sum(bool(row["is_correct"]) for row in rows) / len(rows) if rows else None
    )


def canonical_member_for_choice(row: dict[str, Any], choice: str) -> str:
    """Map displayed label A/B to stable canonical member a/b."""

    if choice not in {"A", "B"}:
        raise ValueError(f"invalid canonical choice: {choice}")
    orientation = row["orientation"]
    if orientation == "A_THEN_B":
        return "a" if choice == "A" else "b"
    if orientation == "B_THEN_A":
        return "b" if choice == "A" else "a"
    raise ValueError(f"invalid orientation: {orientation}")


def _stable_seed(base_seed: int, label: str) -> int:
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return (base_seed + int.from_bytes(digest[:4], "big")) % (2**32)


def _cluster_bootstrap_interval(
    rows: Sequence[dict[str, Any]],
    *,
    statistic: Callable[[list[dict[str, Any]]], float | None],
    seed: int,
    resamples: int,
    confidence_level: float,
) -> dict[str, float | int | None]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[str(row["pair_id"])].append(row)
    pair_ids = sorted(by_pair)
    estimate = statistic(list(rows))
    if not pair_ids or estimate is None:
        return {
            "pair_count": len(pair_ids),
            "estimate": estimate,
            "lower": None,
            "upper": None,
        }
    rng = np.random.default_rng(seed)
    estimates: list[float] = []
    for _ in range(resamples):
        sampled = rng.choice(pair_ids, size=len(pair_ids), replace=True)
        sampled_rows = [row for pair_id in sampled for row in by_pair[str(pair_id)]]
        value = statistic(sampled_rows)
        if value is not None and math.isfinite(value):
            estimates.append(float(value))
    if not estimates:
        lower = upper = None
    else:
        alpha = (1 - confidence_level) / 2
        lower = float(np.quantile(estimates, alpha))
        upper = float(np.quantile(estimates, 1 - alpha))
    return {
        "pair_count": len(pair_ids),
        "estimate": float(estimate),
        "lower": lower,
        "upper": upper,
    }


def _accuracy_interval(
    rows: Sequence[dict[str, Any]],
    *,
    seed: int,
    resamples: int,
    confidence_level: float,
    label: str,
) -> dict[str, float | int | None]:
    return _cluster_bootstrap_interval(
        rows,
        statistic=_accuracy,
        seed=_stable_seed(seed, label),
        resamples=resamples,
        confidence_level=confidence_level,
    )


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else None


def _paired_effect(
    rows: Sequence[dict[str, Any]],
    *,
    high_filter: Callable[[dict[str, Any]], bool],
    low_filter: Callable[[dict[str, Any]], bool],
    seed: int,
    resamples: int,
    confidence_level: float,
    label: str,
) -> dict[str, float | int | None]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[str(row["pair_id"])].append(row)
    differences: dict[str, float] = {}
    for pair_id, pair_rows in by_pair.items():
        high = [float(bool(row["is_correct"])) for row in pair_rows if high_filter(row)]
        low = [float(bool(row["is_correct"])) for row in pair_rows if low_filter(row)]
        if high and low:
            differences[pair_id] = float(np.mean(high) - np.mean(low))
    pair_ids = sorted(differences)
    estimate = _mean(differences.values())
    if not pair_ids or estimate is None:
        return {
            "pair_count": len(pair_ids),
            "estimate": estimate,
            "lower": None,
            "upper": None,
        }
    rng = np.random.default_rng(_stable_seed(seed, label))
    bootstrapped = [
        float(np.mean([differences[str(pair_id)] for pair_id in sampled]))
        for sampled in (
            rng.choice(pair_ids, size=len(pair_ids), replace=True)
            for _ in range(resamples)
        )
    ]
    alpha = (1 - confidence_level) / 2
    return {
        "pair_count": len(pair_ids),
        "estimate": float(estimate),
        "lower": float(np.quantile(bootstrapped, alpha)),
        "upper": float(np.quantile(bootstrapped, 1 - alpha)),
    }


def _safe_spearman(rows: list[dict[str, Any]], x_field: str, y_field: str) -> float | None:
    if len(rows) < 3:
        return None
    x = np.asarray([float(row[x_field]) for row in rows], dtype=np.float64)
    y = np.asarray([float(row[y_field]) for row in rows], dtype=np.float64)
    if np.all(x == x[0]) or np.all(y == y[0]):
        return None
    value = float(spearmanr(x, y).statistic)
    return value if math.isfinite(value) else None


def _spearman_interval(
    rows: Sequence[dict[str, Any]],
    *,
    x_field: str,
    y_field: str,
    seed: int,
    resamples: int,
    confidence_level: float,
    label: str,
) -> dict[str, float | int | None]:
    return _cluster_bootstrap_interval(
        rows,
        statistic=lambda sample: _safe_spearman(sample, x_field, y_field),
        seed=_stable_seed(seed, label),
        resamples=resamples,
        confidence_level=confidence_level,
    )


def _blank_maps(blank_rows: Sequence[dict[str, Any]]) -> tuple[dict[tuple[str, str], str], dict[str, dict[str, Any]]]:
    matched: dict[tuple[str, str], str] = {}
    by_pair: dict[str, list[str]] = defaultdict(list)
    for row in blank_rows:
        selected = canonical_member_for_choice(row, str(row["parsed_output"]))
        key = (str(row["pair_id"]), str(row["orientation"]))
        if key in matched:
            raise ValueError(f"duplicate blank control for {key}")
        matched[key] = selected
        by_pair[key[0]].append(selected)
    summaries: dict[str, dict[str, Any]] = {}
    for pair_id, choices in sorted(by_pair.items()):
        counts = Counter(choices)
        preference = (
            "a"
            if counts["a"] > counts["b"]
            else "b"
            if counts["b"] > counts["a"]
            else "TIE"
        )
        summaries[pair_id] = {
            "canonical_member_a_count": counts["a"],
            "canonical_member_b_count": counts["b"],
            "blank_preferred_member": preference,
        }
    return matched, summaries


def _prior_alignment(
    full_rows: Sequence[dict[str, Any]],
    matched_blank: dict[tuple[str, str], str],
    pair_blank: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors = [row for row in full_rows if not row["is_correct"]]
    matched_count = 0
    unique_eligible = 0
    unique_aligned = 0
    for row in errors:
        selected = canonical_member_for_choice(row, str(row["parsed_output"]))
        blank_selected = matched_blank[(str(row["pair_id"]), str(row["orientation"]))]
        matched_count += selected == blank_selected
        pair_preference = pair_blank[str(row["pair_id"])]["blank_preferred_member"]
        if pair_preference != "TIE":
            unique_eligible += 1
            unique_aligned += selected == pair_preference
    return {
        "error_count": len(errors),
        "matched_orientation_prior_aligned_error_count": matched_count,
        "matched_orientation_prior_aligned_error_rate": (
            matched_count / len(errors) if errors else None
        ),
        "unique_pair_preference_eligible_error_count": unique_eligible,
        "unique_pair_preference_aligned_error_count": unique_aligned,
        "unique_pair_preference_aligned_error_rate": (
            unique_aligned / unique_eligible if unique_eligible else None
        ),
    }


def _load_render_manifest(bundle_path: Path, member: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(bundle_path) as archive:
        value = json.loads(archive.read(member))
    if not isinstance(value, list):
        raise TypeError("render manifest must be a JSON list")
    return value


def _condition_metadata(render: dict[str, Any]) -> dict[str, Any]:
    bbox = render["render_metadata"]["critical_bbox"]
    return {
        "condition_id": render["condition_id"],
        "font_id": render["font_id"],
        "font_size": int(render["font_size"]),
        "critical_pixel_area": int(render["render_metadata"]["critical_pixel_area"]),
        "critical_bbox_x0": int(bbox[0]),
        "critical_bbox_y0": int(bbox[1]),
        "critical_bbox_x1_exclusive": int(bbox[2]),
        "critical_bbox_y1_exclusive": int(bbox[3]),
        "critical_bbox_width": int(bbox[2] - bbox[0]),
        "critical_bbox_height": int(bbox[3] - bbox[1]),
    }


def build_checkpoint_d_diagnostics(root: Path, config_path: Path) -> dict[str, Any]:
    config = _load_yaml(config_path)
    source = config["source"]
    settings = config["analysis"]
    design_path = root / source["calibration_design"]
    inventory_path = root / source["candidate_inventory"]
    bundle_path = root / source["frozen_render_bundle"]
    artifact_dir = root / source["artifact_dir"]
    first_path = artifact_dir / source["analysis_exact_run"]
    second_path = artifact_dir / source["reproducibility_only_run"]
    design = _load_yaml(design_path)
    calibration_ids = set(design["allocation"]["calibration_pair_ids"])
    locked_ids = set(design["allocation"]["locked_validation_pair_ids"])
    if calibration_ids & locked_ids:
        raise ValueError("calibration and locked pair sets overlap")

    first = _load_jsonl(first_path)
    second = _load_jsonl(second_path)
    first_ids = {str(row["pair_id"]) for row in first}
    second_ids = {str(row["pair_id"]) for row in second}
    if first_ids != calibration_ids or second_ids != calibration_ids:
        raise ValueError("analysis inputs do not exactly match exposed calibration pair IDs")
    if (first_ids | second_ids) & locked_ids:
        raise ValueError("locked-validation pair exposure detected")
    full = [row for row in first if row["control_type"] == FULL_INFORMATION]
    blank = [row for row in first if row["control_type"] == BLANK_CONTROL]
    if len(full) != 800 or len(blank) != 200:
        raise ValueError("unexpected repaired-calibration analysis grain")

    inventory = _load_yaml(inventory_path)
    pair_records = {
        str(pair["pair_id"]): pair
        for pair in inventory["pairs"]
        if str(pair["pair_id"]) in calibration_ids
    }
    if set(pair_records) != calibration_ids:
        raise ValueError("candidate metadata missing for exposed calibration pair")
    renders = [
        row
        for row in _load_render_manifest(bundle_path, source["render_manifest_member"])
        if str(row["pair_id"]) in calibration_ids
    ]
    if len(renders) != 400 or {str(row["pair_id"]) for row in renders} != calibration_ids:
        raise ValueError("render metadata does not match exposed calibration inventory")
    render_by_key = {
        (str(row["pair_id"]), str(row["condition_id"])): row for row in renders
    }
    if len(render_by_key) != len(renders):
        raise ValueError("duplicate pair-condition render metadata")

    confidence = float(settings["confidence_level"])
    resamples = int(settings["cluster_bootstrap_resamples"])
    seed = int(settings["cluster_bootstrap_seed"])
    components = sorted({str(row["component_type"]) for row in full})
    matched_blank, pair_blank = _blank_maps(blank)

    member_identity: dict[str, Any] = {}
    for component in components:
        selected = [row for row in full if row["component_type"] == component]
        component_result: dict[str, Any] = {}
        for member in ("a", "b"):
            member_rows = [row for row in selected if row["displayed_member"] == member]
            component_result[f"member_{member}"] = {
                "observation_count": len(member_rows),
                "accuracy": _accuracy(member_rows),
                "pair_clustered_interval": _accuracy_interval(
                    member_rows,
                    seed=seed,
                    resamples=resamples,
                    confidence_level=confidence,
                    label=f"member|{component}|{member}",
                ),
            }
        errors = [row for row in selected if not row["is_correct"]]
        error_selected = Counter(
            canonical_member_for_choice(row, str(row["parsed_output"])) for row in errors
        )
        component_result["error_collapse"] = {
            "error_count": len(errors),
            "selected_member_a_count": error_selected["a"],
            "selected_member_b_count": error_selected["b"],
            "selected_member_a_rate": error_selected["a"] / len(errors) if errors else None,
            "selected_member_b_rate": error_selected["b"] / len(errors) if errors else None,
        }
        member_identity[component] = component_result

    prior_alignment = {
        "definition": {
            "matched_orientation": "For each FULL_INFORMATION error, selected canonical member equals the blank selection for the same pair_id and candidate orientation.",
            "unique_pair_preference": "For pairs whose two blank orientations yield a strict canonical-member majority, the error selects that majority member; tied pairs are excluded only from this secondary denominator.",
        },
        "overall": _prior_alignment(full, matched_blank, pair_blank),
        "per_component": {
            component: _prior_alignment(
                [row for row in full if row["component_type"] == component],
                matched_blank,
                pair_blank,
            )
            for component in components
        },
        "pair_preference_counts": dict(
            sorted(Counter(value["blank_preferred_member"] for value in pair_blank.values()).items())
        ),
    }

    condition_rows: list[dict[str, Any]] = []
    for pair_id in sorted(calibration_ids):
        pair_full = [row for row in full if row["pair_id"] == pair_id]
        component = str(pair_records[pair_id]["component_type"])
        for condition_id in sorted({str(row["condition_id"]) for row in pair_full}):
            cell = [row for row in pair_full if row["condition_id"] == condition_id]
            metadata = _condition_metadata(render_by_key[(pair_id, condition_id)])
            condition_rows.append(
                {
                    "pair_id": pair_id,
                    "component_type": component,
                    **metadata,
                    "observation_count": len(cell),
                    "accuracy": _accuracy(cell),
                    "member_a_accuracy": _accuracy(
                        [row for row in cell if row["displayed_member"] == "a"]
                    ),
                    "member_b_accuracy": _accuracy(
                        [row for row in cell if row["displayed_member"] == "b"]
                    ),
                }
            )

    component_conditions: dict[str, Any] = {}
    size_effects: dict[str, Any] = {}
    font_effects: dict[str, Any] = {}
    for component in components:
        selected = [row for row in full if row["component_type"] == component]
        cells: dict[str, Any] = {}
        for font_id in ("noto_sans_thai_regular", "noto_serif_thai_regular"):
            for font_size in (72, 96):
                condition_id = f"{font_id}__{font_size}__center"
                cell = [row for row in selected if row["condition_id"] == condition_id]
                cells[condition_id] = {
                    "font_id": font_id,
                    "font_size": font_size,
                    "observation_count": len(cell),
                    "accuracy": _accuracy(cell),
                    "pair_clustered_interval": _accuracy_interval(
                        cell,
                        seed=seed,
                        resamples=resamples,
                        confidence_level=confidence,
                        label=f"condition|{component}|{condition_id}",
                    ),
                }
        component_conditions[component] = cells
        size_effects[component] = {
            font_id: _paired_effect(
                selected,
                high_filter=lambda row, font_id=font_id: row["condition_id"]
                == f"{font_id}__96__center",
                low_filter=lambda row, font_id=font_id: row["condition_id"]
                == f"{font_id}__72__center",
                seed=seed,
                resamples=resamples,
                confidence_level=confidence,
                label=f"size|{component}|{font_id}",
            )
            for font_id in ("noto_sans_thai_regular", "noto_serif_thai_regular")
        }
        size_effects[component]["ALL_FONTS"] = _paired_effect(
            selected,
            high_filter=lambda row: "__96__" in row["condition_id"],
            low_filter=lambda row: "__72__" in row["condition_id"],
            seed=seed,
            resamples=resamples,
            confidence_level=confidence,
            label=f"size|{component}|all",
        )
        font_effects[component] = {
            str(font_size): _paired_effect(
                selected,
                high_filter=lambda row, font_size=font_size: row["condition_id"]
                == f"noto_serif_thai_regular__{font_size}__center",
                low_filter=lambda row, font_size=font_size: row["condition_id"]
                == f"noto_sans_thai_regular__{font_size}__center",
                seed=seed,
                resamples=resamples,
                confidence_level=confidence,
                label=f"font|{component}|{font_size}",
            )
            for font_size in (72, 96)
        }

    pair_rows: list[dict[str, Any]] = []
    for pair_id in sorted(calibration_ids):
        pair = pair_records[pair_id]
        pair_full = [row for row in full if row["pair_id"] == pair_id]
        pair_errors = [row for row in pair_full if not row["is_correct"]]
        aligned = sum(
            canonical_member_for_choice(row, str(row["parsed_output"]))
            == matched_blank[(pair_id, str(row["orientation"]))]
            for row in pair_errors
        )
        render_cells = [row for row in condition_rows if row["pair_id"] == pair_id]
        areas = [int(row["critical_pixel_area"]) for row in render_cells]
        widths = [int(row["critical_bbox_width"]) for row in render_cells]
        heights = [int(row["critical_bbox_height"]) for row in render_cells]
        blank_by_orientation = {
            orientation: matched_blank[(pair_id, orientation)]
            for orientation in ("A_THEN_B", "B_THEN_A")
        }
        pair_rows.append(
            {
                "pair_id": pair_id,
                "component_type": pair["component_type"],
                "text_a": pair["text_a"],
                "text_b": pair["text_b"],
                "lexical_status_a": pair["lexical_status_a"],
                "lexical_status_b": pair["lexical_status_b"],
                "observation_count": len(pair_full),
                "overall_accuracy": _accuracy(pair_full),
                "member_a_accuracy": _accuracy(
                    [row for row in pair_full if row["displayed_member"] == "a"]
                ),
                "member_b_accuracy": _accuracy(
                    [row for row in pair_full if row["displayed_member"] == "b"]
                ),
                "blank_a_then_b_selected_member": blank_by_orientation["A_THEN_B"],
                "blank_b_then_a_selected_member": blank_by_orientation["B_THEN_A"],
                "blank_preferred_member": pair_blank[pair_id]["blank_preferred_member"],
                "full_error_count": len(pair_errors),
                "matched_orientation_prior_aligned_error_count": aligned,
                "matched_orientation_prior_aligned_error_rate": (
                    aligned / len(pair_errors) if pair_errors else None
                ),
                "font_effect_serif_minus_sans": _mean(
                    float(bool(row["is_correct"]))
                    * (1 if row["condition_id"].startswith("noto_serif") else -1)
                    for row in pair_full
                )
                * 2,
                "size_effect_96_minus_72": _mean(
                    float(bool(row["is_correct"]))
                    * (1 if "__96__" in row["condition_id"] else -1)
                    for row in pair_full
                )
                * 2,
                "critical_pixel_area_mean": _mean(areas),
                "critical_pixel_area_min": min(areas),
                "critical_pixel_area_max": max(areas),
                "critical_bbox_width_mean": _mean(widths),
                "critical_bbox_width_min": min(widths),
                "critical_bbox_width_max": max(widths),
                "critical_bbox_height_mean": _mean(heights),
                "critical_bbox_height_min": min(heights),
                "critical_bbox_height_max": max(heights),
            }
        )

    lexical_status = {
        status: {
            "observation_count": len(status_rows),
            "accuracy": _accuracy(status_rows),
            "pair_clustered_interval": _accuracy_interval(
                status_rows,
                seed=seed,
                resamples=resamples,
                confidence_level=confidence,
                label=f"lexical|{status}",
            ),
        }
        for status in ("REAL", "CONSTRUCTED", "UNCERTAIN")
        if (
            status_rows := [
                row for row in full if row["displayed_lexical_status"] == status
            ]
        )
    }

    association_features = (
        "critical_pixel_area_mean",
        "critical_bbox_width_mean",
        "critical_bbox_height_mean",
    )
    pair_associations: dict[str, Any] = {}
    for scope in ("ALL", *components):
        selected_pairs = (
            pair_rows
            if scope == "ALL"
            else [row for row in pair_rows if row["component_type"] == scope]
        )
        pair_associations[scope] = {
            feature: _spearman_interval(
                selected_pairs,
                x_field=feature,
                y_field="overall_accuracy",
                seed=seed,
                resamples=resamples,
                confidence_level=confidence,
                label=f"pair-association|{scope}|{feature}",
            )
            for feature in association_features
        }

    condition_features = (
        "critical_pixel_area",
        "critical_bbox_width",
        "critical_bbox_height",
    )
    condition_associations: dict[str, Any] = {}
    for scope in ("ALL", *components):
        selected_conditions = (
            condition_rows
            if scope == "ALL"
            else [row for row in condition_rows if row["component_type"] == scope]
        )
        condition_associations[scope] = {
            feature: _spearman_interval(
                selected_conditions,
                x_field=feature,
                y_field="accuracy",
                seed=seed,
                resamples=resamples,
                confidence_level=confidence,
                label=f"condition-association|{scope}|{feature}",
            )
            for feature in condition_features
        }

    reproducibility = compare_reproducibility(first, second)
    git_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    git_status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "schema_version": 1,
        "checkpoint": "CHECKPOINT_D_CALIBRATION_ONLY_DIAGNOSTICS",
        "scope": "ALREADY_EXPOSED_CALIBRATION_PAIRS_ONLY",
        "gate_0_status": "NOT_RUN",
        "locked_validation_status": "BLOCKED_UNEXPOSED",
        "stage_1a_status": "BLOCKED",
        "compression_status": "NOT_RUN",
        "source_identity": {
            "run_id": source["run_id"],
            "analysis_exact_run": "exact_run_1_only",
            "reproducibility_exact_run": "exact_run_2_only_not_pooled",
            "analysis_full_information_observations": len(full),
            "analysis_blank_observations": len(blank),
            "analysis_pair_count": len(calibration_ids),
            "analysis_code_git_sha": git_sha,
            "analysis_tracked_tree_clean": not bool(git_status),
            "source_sha256": {
                "analysis_config": sha256_file(config_path),
                "analysis_module": sha256_file(Path(__file__)),
                "analysis_predictions": sha256_file(first_path),
                "reproducibility_predictions": sha256_file(second_path),
                "calibration_design": sha256_file(design_path),
                "candidate_inventory": sha256_file(inventory_path),
                "frozen_render_bundle": sha256_file(bundle_path),
            },
        },
        "exact_rerun_accounting_audit": {
            "passed": all(
                value == 1.0 for value in reproducibility["agreement_rates"].values()
            )
            and reproducibility["same_observation_ids"],
            "reproducibility": reproducibility,
            "runs_pooled_for_estimation": False,
            "independent_statistical_units_added_by_rerun": 0,
            "effective_pair_count_for_analysis": len(calibration_ids),
        },
        "member_identity_asymmetry": member_identity,
        "blank_prior_alignment": prior_alignment,
        "rendering_condition_effects": {
            "component_by_font_by_size": component_conditions,
            "size_effect_96_minus_72": size_effects,
            "font_effect_serif_minus_sans": font_effects,
            "effect_interpretation": "descriptive calibration association; not causal",
        },
        "lexical_status_diagnostics": lexical_status,
        "critical_region_associations": {
            "pair_level_mean_geometry_vs_pair_accuracy": pair_associations,
            "pair_condition_geometry_vs_pair_condition_accuracy": condition_associations,
            "measure": "Spearman rho with pair-cluster bootstrap interval",
            "causal_interpretation_allowed": False,
        },
        "pair_diagnostics": pair_rows,
        "pair_condition_diagnostics": condition_rows,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty diagnostic table: {path}")
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_checkpoint_d_artifacts(
    root: Path, config_path: Path, output_dir: Path
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {output_dir}")
    report = build_checkpoint_d_diagnostics(root, config_path)
    output_dir.mkdir(parents=True)
    json_path = output_dir / "diagnostics.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pair_path = output_dir / "pair_diagnostics.csv"
    condition_path = output_dir / "pair_condition_diagnostics.csv"
    _write_csv(pair_path, report["pair_diagnostics"])
    _write_csv(condition_path, report["pair_condition_diagnostics"])
    manifest = {
        "schema_version": 1,
        "checkpoint": report["checkpoint"],
        "files": {
            path.name: sha256_file(path)
            for path in (json_path, pair_path, condition_path)
        },
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
