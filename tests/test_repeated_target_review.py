from labbs2026.stage0.repeated_target_review import review_repeated_targets


def _rows() -> list[dict]:
    rows = []
    for pair_index in range(5):
        for member in ("a", "b"):
            target_value = (pair_index + (member == "b")) % 2 == 0
            for model in ("BASE", "SPECIALIZED"):
                for font in ("sans", "serif"):
                    for size in (72, 96):
                        rows.append(
                            {
                                "pair_id": f"p{pair_index}",
                                "member": member,
                                "model_role": model,
                                "font_id": font,
                                "font_size": size,
                                "component_type": "TONE_MARK",
                                "primary_exact": target_value,
                            }
                        )
    return rows


def test_review_selects_target_aware_structure() -> None:
    review = review_repeated_targets(_rows(), resamples=100, seed=7)
    assert review["pair_count"] == 5
    assert review["target_count"] == 10
    assert review["observations_per_target"] == 8
    assert review["target_level_excess_covariance"] > 0
    assert (
        review["structure_comparison"]["B"]["assessment"]
        == "SELECTED_PRIMARY_TARGET_AWARE_STRUCTURE"
    )
