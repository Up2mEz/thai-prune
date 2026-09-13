from labbs2026.stage0.paddle_wayu_locked_panel import build_workload


def test_locked_panel_workload_is_exactly_6400_unique_calls() -> None:
    locked = [f"p{i:03d}" for i in range(100)]
    conditions = ["c1", "c2", "c3", "c4"]
    design = {
        "models": [
            {"role": "BASE", "model_id": "base", "revision": "r1"},
            {"role": "SPECIALIZED", "model_id": "specialized", "revision": "r2"},
        ],
        "dataset": {"members": ["a", "b"], "render_conditions": conditions},
        "intervention": {
            "budgets": [
                {"budget_id": "B256_FULL", "input_resolution": [448, 448], "min_pixels": 448**2, "max_pixels": 448**2, "image_grid_thw": [1, 32, 32], "pre_merge_patches": 1024, "llm_image_placeholders": 256},
                {"budget_id": "B196", "input_resolution": [392, 392], "min_pixels": 392**2, "max_pixels": 392**2, "image_grid_thw": [1, 28, 28], "pre_merge_patches": 784, "llm_image_placeholders": 196},
                {"budget_id": "B121", "input_resolution": [308, 308], "min_pixels": 308**2, "max_pixels": 308**2, "image_grid_thw": [1, 22, 22], "pre_merge_patches": 484, "llm_image_placeholders": 121},
                {"budget_id": "B64", "input_resolution": [224, 224], "min_pixels": 224**2, "max_pixels": 224**2, "image_grid_thw": [1, 16, 16], "pre_merge_patches": 256, "llm_image_placeholders": 64},
            ]
        },
        "prompt": "OCR:",
    }
    allocation = {"allocation": {"locked_validation_pair_ids": locked}}
    components = [
        "BASE_CHARACTER",
        "TONE_MARK",
        "UPPER_VOWEL_VARIANT",
        "LOWER_VOWEL_VARIANT",
        "STACKED_TONE_MARK",
    ]
    pairs = [
        {"pair_id": pair_id, "component_type": components[index // 20], "text_a": "ก", "text_b": "ข"}
        for index, pair_id in enumerate(locked)
    ]
    renders = []
    for pair_id in locked:
        for condition in conditions:
            renders.append({
                "pair_id": pair_id,
                "condition_id": condition,
                "font_id": condition,
                "font_size": 72,
                "image_a_path": f"{pair_id}/a.png",
                "image_a_sha256": "a" * 64,
                "image_b_path": f"{pair_id}/b.png",
                "image_b_sha256": "b" * 64,
            })
    workload = build_workload(design, allocation, pairs, renders)
    assert len(workload) == 6400
    assert len({row["call_id"] for row in workload}) == 6400
    assert sum(row["model_role"] == "BASE" for row in workload) == 3200
    assert sum(row["budget_id"] == "B64" for row in workload) == 1600
