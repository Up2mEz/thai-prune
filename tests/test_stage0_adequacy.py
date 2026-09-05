from labbs2026.stage0.adequacy import assess_pair_inventory


def _pairs(per_component: int) -> list[dict[str, str]]:
    return [
        {"pair_id": f"{component}_{index}", "component_type": component}
        for component in ("BASE_CHARACTER", "TONE_MARK")
        for index in range(per_component)
    ]


def test_six_pairs_per_component_require_expansion_for_ten_pp_seoi() -> None:
    report = assess_pair_inventory(_pairs(6), seoi_absolute_pp=10, seed=7)

    assert report["status"] == "EXPANSION_REQUIRED"
    assert report["minimum_inventory_per_component"] == 40
    assert report["repeated_renderings_count_as_independent"] is False


def test_forty_pairs_produce_disjoint_twenty_twenty_proposal() -> None:
    report = assess_pair_inventory(_pairs(40), seoi_absolute_pp=10, seed=7)
    allocation = report["proposed_allocation"]

    assert report["status"] == "MEETS_PROVISIONAL_GRANULARITY_FLOOR_NOT_POWER_GUARANTEE"
    assert report["calibration_counts"] == {"BASE_CHARACTER": 20, "TONE_MARK": 20}
    assert report["locked_validation_counts"] == {"BASE_CHARACTER": 20, "TONE_MARK": 20}
    assert not set(allocation["calibration_pair_ids"]) & set(
        allocation["locked_validation_pair_ids"]
    )
