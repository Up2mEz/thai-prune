from pathlib import Path

from PIL import Image, ImageDraw

from labbs2026.stage0.measurement_diagnostic import (
    canonical_choice,
    classify_root_cause,
    rescue_image,
    swapped_observation,
)


CRITERIA = {
    "signal_present_if_point_at_least": 0.60,
    "signal_present_if_ci_low_above": 0.50,
    "position_following_interface_evidence_if_ci_low_at_least": 0.90,
    "rescue_gain_if_point_at_least": 0.10,
    "rescue_gain_if_ci_low_above": 0.0,
    "action_map": {
        "measurement/interface": "A",
        "visual representation": "B",
        "mixed": "B",
        "inconclusive": "C",
    },
}


def _ci(estimate: float, low: float, high: float) -> dict:
    return {"estimate": estimate, "ci_low": low, "ci_high": high, "pair_count": 100}


def test_position_swap_preserves_content_mapping_and_flips_expected_label() -> None:
    row = {
        "observation_id": "x", "candidate_a": "กา", "candidate_b": "ขา",
        "candidate_a_lexical_status": "REAL", "candidate_b_lexical_status": "UNCERTAIN",
        "orientation": "A_THEN_B", "expected_label": "A",
    }
    template = "A. {candidate_a}\nB. {candidate_b}"
    swapped = swapped_observation(row, template)
    assert swapped["orientation"] == "B_THEN_A"
    assert swapped["expected_label"] == "B"
    assert canonical_choice("A", row["orientation"]) == "a"
    assert canonical_choice("B", swapped["orientation"]) == "a"


def test_visual_rescue_keeps_canvas_and_enlarges_content(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.png", tmp_path / "rescued.png"
    image = Image.new("RGB", (448, 448), "white")
    ImageDraw.Draw(image).rectangle((210, 210, 229, 229), fill="black")
    image.save(source)
    record = rescue_image(source, destination)
    assert Image.open(destination).size == (448, 448)
    assert max(record["rescued_content_size"]) == 320


def test_root_cause_rules_are_deterministic() -> None:
    interface = _ci(0.96, 0.92, 0.99)
    signal = _ci(0.72, 0.65, 0.78)
    weak = _ci(0.54, 0.48, 0.60)
    rescue = _ci(0.15, 0.05, 0.24)
    no_rescue = _ci(0.02, -0.03, 0.07)
    assert classify_root_cause(interface, signal, weak, no_rescue, CRITERIA)["classification"] == "measurement/interface"
    assert classify_root_cause(interface, weak, weak, rescue, CRITERIA)["classification"] == "mixed"
    assert classify_root_cause(_ci(0.40, 0.30, 0.50), weak, weak, rescue, CRITERIA)["classification"] == "visual representation"
    assert classify_root_cause(_ci(0.40, 0.30, 0.50), weak, weak, no_rescue, CRITERIA)["classification"] == "inconclusive"
