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
