"""P-ZOOM-2: the registered reading and its building blocks."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks import p_zoom2_analysis as pz2

VIEWS = [{"name": "pad", "kind": "pad"}, {"name": "scale90", "kind": "scale"},
         {"name": "bands", "kind": "grid", "rows": 3, "cols": 1}]


def _page(*outcomes, control=("text",)):
    lines = [{"line": i, "group": "absent", "marks": 10, "outcome": o, "marks_correct": 10}
             for i, o in enumerate(outcomes)]
    lines += [{"line": 100 + i, "group": "control", "marks": 10, "outcome": o, "marks_correct": 10}
              for i, o in enumerate(control)]
    return {"lines": lines}


def test_the_reading_follows_the_registered_thresholds() -> None:
    assert pz2.reading(0.30, 0.05, 0.9) == "zoom_adds_beyond_perturbation"
    assert pz2.reading(0.30, 0.25, 0.9) == "perturbation_explains_gain"  # zoom gains, but so do controls
    assert pz2.reading(0.05, 0.12, 0.9) == "perturbation_explains_gain"
    assert pz2.reading(0.08, 0.04, 0.9) == "no_gain_from_views"
    assert pz2.reading(0.40, 0.00, 0.79) == "instrument_fails_control"  # control checked first
    assert pz2.reading(0.10, 0.00, 0.80) == "zoom_adds_beyond_perturbation"  # boundaries inclusive


def test_page_gains_count_only_absent_lines_and_both_directions() -> None:
    base = [_page("text", "not_found", "text")]
    view = [_page("not_found", "text", "text")]
    (row,) = pz2.page_gains(view, base)
    assert row == {"absent": 30, "text": 20, "gain": 10, "loss": 10}
    with pytest.raises(ValueError):
        pz2.page_gains([_page("text")], [_page("text", "text")])
    with pytest.raises(ValueError):
        pz2.page_gains([_page("text")], [_page("text"), _page("text")])


def test_union_counts_a_mark_once_if_any_read_recovers_it() -> None:
    a = [_page("text", "not_found", "not_found")]
    b = [_page("not_found", "figure_only", "text")]
    assert pz2.union_share([a]) == 10 / 30
    assert pz2.union_share([a, b]) == 20 / 30


def test_control_share_uses_control_lines_only() -> None:
    assert pz2.control_text_share([_page("text", control=("text", "not_found"))]) == 0.5


def test_assemble_views_requires_every_tile_of_every_view() -> None:
    page = {"id": "P1", "absent_lines": [0], "control_lines": [1]}

    def rec(view, tile):
        return {"id": "P1", "view": view, "tile": tile, "reference": "R", "raw_output": f"{view}{tile}"}

    full = [rec("pad", 0), rec("scale90", 0), rec("bands", 0), rec("bands", 1), rec("bands", 2)]
    got = pz2.assemble_views(full, [page], VIEWS)
    assert got["bands"][0]["tile_outputs"] == ["bands0", "bands1", "bands2"]
    assert got["pad"][0]["absent"] == [0] and got["pad"][0]["control"] == [1]
    with pytest.raises(ValueError, match="missing tiles"):
        pz2.assemble_views(full[:-1], [page], VIEWS)
    with pytest.raises(ValueError, match="duplicate"):
        pz2.assemble_views(full + [rec("pad", 0)], [page], VIEWS)
    with pytest.raises(ValueError, match="outside"):
        pz2.assemble_views(full + [{**rec("pad", 0), "id": "LOCKED"}], [page], VIEWS)


def test_analyze_ties_the_pieces_together_and_is_deterministic() -> None:
    base = [_page("text", "not_found", "not_found", "not_found") for _ in range(6)]
    scores = {"pad": [_page("text", "text", "not_found", "not_found") for _ in range(6)],
              "scale90": [_page("text", "not_found", "text", "not_found") for _ in range(6)],
              "bands": [_page("text", "text", "text", "text") for _ in range(6)]}
    out = pz2.analyze(base, scores)
    assert out["perturbation_gain_N"] == pytest.approx(0.25)  # one of four lines each
    assert out["zoom_gain_Z"] == pytest.approx(0.75)
    assert out["Z_minus_N"] == pytest.approx(0.50)
    assert out["reading"] == "zoom_adds_beyond_perturbation"
    low, high = out["Z_minus_N_ci95"]
    assert low <= out["Z_minus_N"] <= high
    assert out["union_absent_text_share"]["baseline"] == 0.25
    assert out["union_absent_text_share"]["all"] == 1.0
    assert pz2.analyze(base, scores) == out


def test_controlled_reading_follows_the_registered_thresholds() -> None:
    assert pz2.controlled_reading(0.15, [0.03, 0.27], 0.9) == "zoom_helps"
    assert pz2.controlled_reading(0.15, [-0.02, 0.30], 0.9) == "zoom_not_distinguishable"  # CI spans 0
    assert pz2.controlled_reading(0.05, [0.01, 0.09], 0.9) == "zoom_not_distinguishable"  # too small
    assert pz2.controlled_reading(-0.12, [-0.20, -0.04], 0.9) == "zoom_hurts"
    assert pz2.controlled_reading(-0.12, [-0.20, 0.01], 0.9) == "zoom_not_distinguishable"
    assert pz2.controlled_reading(0.30, [0.20, 0.40], 0.79) == "instrument_fails_control"


def test_churn_counts_marks_that_change_side_in_either_direction() -> None:
    base = [_page("text", "not_found", "text", "not_found")]
    view = [_page("not_found", "text", "text", "not_found")]
    assert pz2.churn_share(view, base) == 20 / 40
    assert pz2.churn_share(base, base) == 0.0


def test_identical_pages_compares_outputs_byte_for_byte() -> None:
    assert pz2.identical_pages({"a": "x", "b": "y"}, {"a": "x", "b": "z"}) == (1, 2)
    with pytest.raises(ValueError):
        pz2.identical_pages({"a": "x"}, {"b": "x"})


def test_analyze_controlled_isolates_zoom_from_cropping_and_flags_drift() -> None:
    base = [_page("text", "not_found", "not_found", "not_found") for _ in range(8)]
    scores = {"repeat": base,
              "pad": base, "scale90": base,
              "bands100": [_page("text", "text", "not_found", "not_found") for _ in range(8)],
              "bands": [_page("text", "text", "text", "text") for _ in range(8)]}
    out = pz2.analyze_controlled(base, scores, (20, 21))
    assert out["zoom_effect_D"] == pytest.approx(0.5)  # 100% vs 50%
    assert out["crop_effect_bands100_minus_baseline"] == pytest.approx(0.25)
    assert out["per_view"]["repeat"]["churn_vs_baseline"] == 0.0
    assert out["controlled_reading"] == "zoom_helps"
    assert out["stack"] == "baseline_reproduced"
    assert pz2.analyze_controlled(base, scores, (17, 21))["stack"] == "stack_drift"
    assert pz2.analyze_controlled(base, scores, (20, 21)) == out  # deterministic
