"""MODEL_SURVEY_M2: arms change decoding only; seeds per item; T5b's stop; arm loading; worker units."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from labbs2026.model_survey.m2 import arm_kwargs, cost, item_seed, load_arm, stop_at_loop, validate
from labbs2026.model_survey.plan import m1_commands, validate as validate_m1

ROOT = Path(__file__).resolve().parents[1]
M2 = yaml.safe_load((ROOT / "configs/model_survey/m2.yaml").read_text("utf-8"))
M1 = yaml.safe_load((ROOT / "configs/model_survey/m1.yaml").read_text("utf-8"))
BASE = M2["runtime"]["generation"]


def test_registered_config_is_valid():
    assert validate(M2) == [["R105"], ["CARD"]]


def test_everything_but_decoding_is_m1s():
    assert M2["models"]["wayu"]["model_id"] == M1["models"]["wayu"]["model_id"]
    assert M2["models"]["wayu"]["revision"] == M1["models"]["wayu"]["revision"]
    assert M2["prompt_kind"] == M1["models"]["wayu"]["primary_prompt"]
    assert M2["prompts"]["OCR_NATIVE"] == M1["prompts"]["OCR_NATIVE"]
    assert M2["benchmark"] == M1["benchmark"] and M2["split"] == M1["split"]
    assert {k: v for k, v in M2["runtime"].items()} == {k: v for k, v in M1["runtime"].items()}
    assert M2["scoring"] == M1["scoring"] and M2["comparison"] == M1["comparison"]


def test_arm_kwargs():
    r105 = arm_kwargs(BASE, M2["arms"]["R105"], 3072)
    assert r105 == {**BASE, "max_new_tokens": 3072, "repetition_penalty": 1.05}
    card = arm_kwargs(BASE, M2["arms"]["CARD"], 3072)
    assert card["do_sample"] is True and card["temperature"] == 0.1 and card["top_p"] == 0.7
    assert card["repetition_penalty"] == 1.05 and card["num_beams"] == 1


@pytest.mark.parametrize("arm", [
    {"do_sample": False, "repetition_penalty": 0.9},
    {"do_sample": False, "repetition_penalty": 1.05, "temperature": 0.1},
    {"do_sample": True, "temperature": 0.1, "repetition_penalty": 1.05},
    {"do_sample": True, "temperature": 0.0, "top_p": 0.7, "repetition_penalty": 1.05},
    {"do_sample": True, "temperature": 0.1, "top_p": 1.5, "repetition_penalty": 1.05},
])
def test_arm_kwargs_rejects(arm):
    with pytest.raises(ValueError):
        arm_kwargs(BASE, arm, 3072)


def test_validate_rejects_bad_queues_and_budget():
    bad = copy.deepcopy(M2)
    bad["gpu_queues"] = [["R105"], ["R105"]]
    with pytest.raises(ValueError, match="exactly once"):
        validate(bad)
    bad = copy.deepcopy(M2)
    bad["unit_deadline_hours"] = 4
    with pytest.raises(ValueError, match="budget"):
        validate(bad)


def test_item_seed_is_fixed_per_item():
    assert item_seed(20261010, "0159AF30") == item_seed(20261010, "0159AF30")
    seeds = {item_seed(20261010, f"{k:08X}") for k in range(500)}
    assert len(seeds) == 500 and all(0 <= s < 2 ** 32 for s in seeds)
    assert item_seed(1, "0159AF30") != item_seed(2, "0159AF30")


UNIT = "ยอดรวมทั้งสิ้น 58 บาท "


def _record(output, reached, tokens=3072, seconds=60.0):
    return {"id": "a", "task": "Full-page OCR", "raw_output": output, "reached_max_new_tokens": reached,
            "generated_tokens": tokens, "seconds_generate": seconds}


def test_stop_at_loop_cuts_only_loops():
    looped = _record("หัวเรื่อง " + UNIT * 12, True)
    cut = stop_at_loop(looped)
    assert cut["t5b_cut"] and not cut["reached_max_new_tokens"]
    # T5b keeps one copy of the earliest repeating unit (here it starts at the space before it)
    assert cut["raw_output"].startswith("หัวเรื่อง") and cut["raw_output"].count("ยอดรวม") == 1
    assert cut["generated_tokens"] < 3072 and cut["seconds_generate"] < 60.0
    plain = _record("ข้อความปกติที่จบเอง", False, 20, 1.0)
    assert stop_at_loop(plain) == {**plain, "t5b_cut": False}


def test_load_arm_and_cost(tmp_path):
    leg = tmp_path / "m2" / "R105"
    leg.mkdir(parents=True)
    rows = [_record("x", False, 10, 1.0) | {"id": i} for i in ("a", "b")]
    (leg / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), "utf-8")
    (leg / "manifest.json").write_text(json.dumps({"items": 2, "failures": []}), "utf-8")
    records, manifest = load_arm(tmp_path, "R105")
    assert [r["id"] for r in records] == ["a", "b"]
    assert cost(records) == {"n": 2, "generated_tokens": 20, "seconds_generate": 2.0,
                             "reached_max_new_tokens": 0, "t5b_cut": 0}
    (leg / "manifest.json").write_text(json.dumps({"items": 3, "failures": []}), "utf-8")
    with pytest.raises(ValueError, match="manifest implies"):
        load_arm(tmp_path, "R105")
    with pytest.raises(FileNotFoundError):
        load_arm(tmp_path, "CARD")


def test_m1_commands_are_the_commands_m1_ran():
    commands = m1_commands(validate_m1(M1))
    assert commands[0][0] == {"name": "m1_qwen3vl4b_shard-0-of-2", "module": "labbs2026.model_survey.remote",
                              "args": ["--role", "qwen3vl4b", "--shard", "0", "--shards", "2"]}
    assert [u["name"] for u in commands[1]] == ["m1_qwen3vl4b_shard-1-of-2", "m1_wayu_shard-0-of-1"]


def test_m2_script_hashes_existing_files_and_worker_runs_units():
    import importlib.util

    spec = importlib.util.spec_from_file_location("m2k", ROOT / "scripts/model_survey_m2_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert all((ROOT / p).is_file() for p in module.HASHED)
    worker = (ROOT / "infra/kaggle/model_survey_worker.py").read_text("utf-8")
    assert 'unit["module"]' in worker and "__LABBS_RUN_SPEC_B64__" in worker
