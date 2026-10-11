"""MODEL_SURVEY_M5: Pathumma under M1's protocol, unchanged except the model and its card prompt."""

import json
from pathlib import Path

import yaml

from labbs2026.model_survey.plan import m1_commands, resolve_prompt, validate

ROOT = Path(__file__).resolve().parents[1]
M5 = yaml.safe_load((ROOT / "configs/model_survey/m5.yaml").read_text("utf-8"))
M1 = yaml.safe_load((ROOT / "configs/model_survey/m1.yaml").read_text("utf-8"))


def test_config_is_valid_and_pinned():
    queues = validate(M5)
    assert queues == [[("pathumma", 0, 2)], [("pathumma", 1, 2)]]
    assert M5["models"]["pathumma"]["revision"] == "08bb11dcabf509ac3fa3ac0014ecd44eadb9729b"
    assert [u["name"] for q in m1_commands(queues) for u in q] == ["m1_pathumma_shard-0-of-2",
                                                                   "m1_pathumma_shard-1-of-2"]


def test_everything_but_the_model_is_m1s():
    for key in ("benchmark", "split", "runtime", "comparison", "scoring", "claim_level"):
        assert M5[key] == M1[key], key
    assert M5["prompts"]["BENCHMARK_QUESTION"] == M1["prompts"]["BENCHMARK_QUESTION"]


def test_card_prompt():
    assert resolve_prompt("CARD_PROMPT", "q?", M5["prompts"]) == "อ่านข้อความในภาพนี้"
    assert resolve_prompt("BENCHMARK_QUESTION", "q?", M5["prompts"]) == "q?"


def test_not_runnable_until_authorized():
    assert M5["status"] != "APPROVED" or (ROOT / M5["registration"]).is_file()


def test_unwrap_natural_text():
    from labbs2026.model_survey.m5 import is_wrapped, unwrap_natural_text

    text = "ก่อน\nหลัง \"ก\" /nbs/"
    complete = json.dumps({"natural_text": text}, ensure_ascii=False)
    assert unwrap_natural_text(complete) == text
    escaped = json.dumps({"natural_text": text})                  # \uXXXX escapes
    assert unwrap_natural_text(escaped) == text
    for cut in (len(escaped) - 2, len(escaped) - 9, 30):        # truncated at the token limit
        assert text.startswith(unwrap_natural_text(escaped[:cut]))
    assert unwrap_natural_text(escaped[:len(escaped) - 2]) == text
    assert unwrap_natural_text('{"natural_text": "x" , "other": 1') == "x"
    assert unwrap_natural_text("ข้อความธรรมดา") == "ข้อความธรรมดา"
    assert is_wrapped(' {"natural_text": "a"}') and not is_wrapped('{"text": "a"}')


def test_remote_manifest_uses_the_runs_config():
    remote = (ROOT / "src/labbs2026/model_survey/remote.py").read_text("utf-8")
    kaggle = (ROOT / "scripts/model_survey_kaggle.py").read_text("utf-8")
    assert 'spec.get("config_path", "configs/model_survey/m1.yaml")' in remote
    assert '"config_path": args.config' in kaggle
