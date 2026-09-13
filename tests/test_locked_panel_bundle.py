import json
from pathlib import Path

import yaml
from PIL import Image

from labbs2026.stage0.locked_panel_bundle import (
    build_locked_source_bundle,
    verify_locked_source_bundle,
)
from labbs2026.step3 import sha256_file


def test_locked_bundle_is_exact_and_deterministic(tmp_path: Path) -> None:
    review = tmp_path / "review"
    review.mkdir()
    pairs = []
    renders = []
    locked = [f"p{i:03d}" for i in range(100)]
    conditions = ["c1", "c2", "c3", "c4"]
    for pair_id in locked:
        pairs.append({"pair_id": pair_id, "text_a": "ก", "text_b": "ข"})
        for condition in conditions:
            row = {"pair_id": pair_id, "condition_id": condition}
            for member in ("a", "b"):
                relative = f"renders/{condition}/{pair_id}__{member}.png"
                path = review / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (448, 448), "white").save(path)
                row[f"image_{member}_path"] = relative
                row[f"image_{member}_sha256"] = sha256_file(path)
            renders.append(row)
    (review / "resolved_pairs.json").write_text(json.dumps(pairs), "utf-8")
    (review / "render_manifest.json").write_text(json.dumps(renders), "utf-8")
    (review / "review_packet.json").write_text("{}", "utf-8")
    design = {
        "source_review_packet_sha256": sha256_file(review / "review_packet.json"),
        "allocation": {
            "sha256": "allocation",
            "calibration_pair_ids": [],
            "locked_validation_pair_ids": locked,
        },
        "render_condition_selection": {"selected_condition_ids": conditions},
    }
    design_path = tmp_path / "design.yaml"
    design_path.write_text(yaml.safe_dump(design), "utf-8")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    one = build_locked_source_bundle(review, design_path, first)
    two = build_locked_source_bundle(review, design_path, second)
    assert one["bundle_sha256"] == two["bundle_sha256"]
    assert verify_locked_source_bundle(first, one["bundle_sha256"])["source_png_count"] == 800
