import importlib.util
from pathlib import Path

import pytest
import torch
import yaml

from labbs2026.spec_decode.design import (
    drop_arm,
    estimated_t4_hours,
    hash_order,
    schedule,
    top2_margin,
)

ROOT = Path(__file__).resolve().parents[1]
ROTATION = [["REF", "PLD5", "PLD10"], ["PLD5", "PLD10", "REF"], ["PLD10", "REF", "PLD5"]]


def _script():
    spec = importlib.util.spec_from_file_location("spec_decode_kaggle", ROOT / "scripts/spec_decode_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hash_order_is_deterministic_and_input_order_free():
    ids = ["a", "b", "c", "d"]
    assert hash_order(ids, 20260927) == hash_order(list(reversed(ids)), 20260927)
    assert sorted(hash_order(ids, 20260927)) == ids
    assert hash_order(ids, 1) != hash_order(ids, 20260927) or len(ids) < 2


def test_hash_order_rejects_duplicates():
    with pytest.raises(ValueError):
        hash_order(["a", "a"], 1)


def test_schedule_warmup_rotation_and_limit():
    ids = [f"id{i}" for i in range(8)]
    warmup, timed = schedule(ids, 20260927, ROTATION, 1)
    ordered = hash_order(ids, 20260927)
    assert warmup == ordered[:1]
    assert [t[0] for t in timed] == ordered[1:]
    assert [t[1] for t in timed[:4]] == [ROTATION[0], ROTATION[1], ROTATION[2], ROTATION[0]]
    _, limited = schedule(ids, 20260927, ROTATION, 1, limit=2)
    assert limited == timed[:2]


def test_schedule_rejects_inconsistent_rotation():
    with pytest.raises(ValueError):
        schedule(["a"], 1, [["REF", "PLD5"], ["REF", "PLD10"]], 0)


def test_rotation_balances_arm_positions():
    # over one full cycle, every arm occupies every position exactly once
    for position in range(3):
        assert sorted(order[position] for order in ROTATION) == ["PLD10", "PLD5", "REF"]


def test_drop_arm_keeps_order_of_others():
    assert drop_arm(ROTATION, "PLD10") == [["REF", "PLD5"], ["PLD5", "REF"], ["REF", "PLD5"]]


def test_estimated_t4_hours():
    assert estimated_t4_hours(120, 60.0, 3) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        estimated_t4_hours(1, 1.0, 0)


def test_top2_margin():
    assert top2_margin(torch.tensor([0.5, 3.0, 2.75, -1.0])) == pytest.approx(0.25)
    assert top2_margin(torch.tensor([1.0, 1.0])) == 0.0


def test_config_matches_registration():
    config = yaml.safe_load((ROOT / "configs/spec_decode/s1.yaml").read_text("utf-8"))
    assert config["status"] == "APPROVED"
    assert config["arm_rotation"] == ROTATION
    assert config["arms"]["REF"] == {}
    assert config["arms"]["PLD5"]["prompt_lookup_num_tokens"] == 5
    assert config["arms"]["PLD10"]["prompt_lookup_num_tokens"] == 10
    assert config["runtime"]["max_new_tokens"] == 3072
    assert config["budget"] == {"max_t4_hours": 12, "drop_if_over": "PLD10"}
    assert config["prompt"]["sha256"] == (
        "0e6c57af282f83f3dfdfa30e33bb8e74e0e1addd974f6ee111c1c22b3d47594d")


def test_budget_rule_smoke_exempt_full_requires_timing_and_drops_pld10():
    script = _script()
    config = yaml.safe_load((ROOT / "configs/spec_decode/s1.yaml").read_text("utf-8"))
    record, rotation = script.budget(config, 2, None, None)
    assert record["rule"] == "smoke_exempt" and rotation == ROTATION
    with pytest.raises(SystemExit):
        script.budget(config, 0, None, None)
    record, rotation = script.budget(config, 0, 160, 60.0)
    assert record["dropped"] is None and rotation == ROTATION  # 4 h
    record, rotation = script.budget(config, 0, 160, 200.0)
    assert record["dropped"] == "PLD10"                        # 13.3 h > 12
    assert rotation == drop_arm(ROTATION, "PLD10")


def test_hashed_files_exist():
    for path in _script().HASHED:
        assert (ROOT / path).is_file(), path
