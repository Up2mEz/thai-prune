from labbs2026.stage0.checkpoint_c import component_headroom


def _metrics(accuracy: float, lower: float, upper: float) -> dict:
    return {
        "per_component": {
            "TEST": {"accuracy_all_scored_observations": accuracy}
        },
        "per_component_pair_clustered_accuracy_interval": {
            "TEST": {"estimate": accuracy, "lower": lower, "upper": upper}
        },
    }


def test_headroom_requires_point_and_interval_to_clear_planning_seoi() -> None:
    clear = component_headroom(
        _metrics(0.80, 0.70, 0.90), planning_seoi_absolute=0.10
    )["TEST"]
    uncertain = component_headroom(
        _metrics(0.64, 0.58, 0.69), planning_seoi_absolute=0.10
    )["TEST"]
    insufficient = component_headroom(
        _metrics(0.58, 0.53, 0.63), planning_seoi_absolute=0.10
    )["TEST"]

    assert clear["interpretation"] == "HEADROOM_CLEAR_AT_POINT_AND_INTERVAL_LOWER_BOUND"
    assert uncertain["interpretation"] == (
        "HEADROOM_PRESENT_AT_POINT_BUT_NOT_INTERVAL_LOWER_BOUND"
    )
    assert insufficient["interpretation"] == "POINT_HEADROOM_BELOW_PLANNING_SESOI"
