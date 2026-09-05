from labbs2026.stage0.metrics import (
    cluster_bootstrap_accuracy,
    compare_reproducibility,
    compute_stage0_metrics,
)


def _row(
    observation_id: str,
    pair_id: str,
    expected: str,
    parsed: str | None,
    *,
    control: str = "FULL_INFORMATION",
    component: str = "TONE_MARK",
) -> dict:
    return {
        "observation_id": observation_id,
        "pair_id": pair_id,
        "component_type": component,
        "control_type": control,
        "expected_label": expected,
        "raw_output": parsed or "invalid",
        "parsed_output": parsed,
        "parse_status": "PARSED" if parsed else "PARSER_FAILURE",
        "is_correct": parsed == expected if parsed else False,
        "generation_seconds": 1.0,
        "llm_visual_token_count": 256,
    }


def test_metrics_keep_parser_failures_and_blank_controls_separate() -> None:
    rows = [
        _row("1", "p1", "A", "A"),
        _row("2", "p1", "B", None),
        _row("3", "p2", "A", "B"),
        _row("4", "p2", "B", "B"),
        _row("5", "p1", "A", "B", control="LANGUAGE_PRIOR_BLANK"),
        _row("6", "p2", "B", "B", control="LANGUAGE_PRIOR_BLANK"),
    ]

    result = compute_stage0_metrics(
        rows, bootstrap_seed=3, bootstrap_resamples=100, confidence_level=0.95
    )

    assert result["full_information"]["observation_count"] == 4
    assert result["full_information"]["parser_failure_count"] == 1
    assert result["full_information"]["accuracy_all_observations"] == 0.5
    assert result["full_information"]["accuracy_conditional_parsed"] == 2 / 3
    assert result["language_prior_blank"]["observation_count"] == 2
    assert result["pair_clustered_accuracy_interval"]["pair_count"] == 2


def test_cluster_bootstrap_uses_pair_count_not_render_count() -> None:
    rows = [
        _row("1", "p1", "A", "A"),
        _row("2", "p1", "B", "B"),
        _row("3", "p2", "A", "B"),
        _row("4", "p2", "B", "A"),
    ]

    result = cluster_bootstrap_accuracy(
        rows, seed=1, resamples=200, confidence_level=0.95
    )

    assert result["pair_count"] == 2
    assert result["estimate"] == 0.5
    assert result["lower"] == 0.0
    assert result["upper"] == 1.0


def test_reproducibility_reports_field_level_agreement() -> None:
    first = [_row("1", "p1", "A", "A")]
    second = [_row("1", "p1", "A", "A")]

    result = compare_reproducibility(first, second)

    assert result["same_observation_ids"]
    assert result["agreement_rates"]["raw_output"] == 1.0
    assert result["agreement_rates"]["llm_visual_token_count"] == 1.0
