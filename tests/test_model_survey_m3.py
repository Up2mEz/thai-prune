"""MODEL_SURVEY_M3: config is M1's decoding plus the escape; shards; stop-only twin; built-in control."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from labbs2026.model_survey import escape
from labbs2026.model_survey.m3 import control, escape_summary, load_shards, m3_commands, stop_only, validate
from labbs2026.thai_marks.loop_cut import variant_b

ROOT = Path(__file__).resolve().parents[1]
M3 = yaml.safe_load((ROOT / "configs/model_survey/m3.yaml").read_text("utf-8"))
M1 = yaml.safe_load((ROOT / "configs/model_survey/m1.yaml").read_text("utf-8"))
M2 = yaml.safe_load((ROOT / "configs/model_survey/m2.yaml").read_text("utf-8"))


def test_registered_config_is_valid_and_sharded():
    assert validate(M3) == [[("E", 0, 2)], [("E", 1, 2)]]
    commands = m3_commands(validate(M3))
    assert commands[1][0] == {"name": "m3_E_shard-1-of-2", "module": "labbs2026.model_survey.remote_m3",
                              "args": ["--shard", "1", "--shards", "2"]}


def test_everything_but_the_escape_is_m1s():
    assert M3["models"]["wayu"] == {k: M1["models"]["wayu"][k] for k in ("model_id", "revision")}
    assert M3["prompt_kind"] == M1["models"]["wayu"]["primary_prompt"]
    assert M3["prompts"]["OCR_NATIVE"] == M1["prompts"]["OCR_NATIVE"]
    assert M3["benchmark"] == M1["benchmark"] and M3["split"] == M1["split"]
    assert M3["runtime"] == M1["runtime"]
    assert M3["reference_arm"] == M2["reference_arm"] and M3["comparison"] == M2["comparison"]
    assert M3["scoring"]["order_free"] == M2["scoring"]["order_free"]
    assert M3["scoring"]["null_seed"] == M2["scoring"]["null_seed"]


def test_the_watch_is_t5bs_variant_b():
    assert (escape.STOP_K, escape.STOP_K_LONG) == (8, 6)
    for text in ("หัว " + "ยอดรวม 58 บาท " * 8, "หัว " + "ยอดรวม 58 บาท " * 7, "x" + "ข" * 60 * 6):
        record = {"raw_output": text, "reached_max_new_tokens": True}
        assert escape.watch_fires(text) == (variant_b(record) != text)


@pytest.mark.parametrize("change", [
    {"runtime": {"generation": {"do_sample": False, "num_beams": 1, "repetition_penalty": 1.05,
                                "no_repeat_ngram_size": 0}}},
    {"escape": {"every": 0}}, {"escape": {"max_total_steps": 100}}, {"shards": 0},
    {"unit_deadline_hours": 4},
])
def test_validate_rejects(change):
    bad = copy.deepcopy(M3)
    for key, value in change.items():
        if isinstance(value, dict) and isinstance(bad.get(key), dict):
            bad[key] = {**bad[key], **value}
        else:
            bad[key] = value
    with pytest.raises(ValueError):
        validate(bad)


def _record(item, output, *, escapes=(), final_cut=False, prefix=None, tokens=10, task="Full-page OCR"):
    return {"id": item, "task": task, "raw_output": output, "generated_tokens": tokens,
            "reached_max_new_tokens": False, "escapes": list(escapes), "final_cut": final_cut,
            "step_cap_hit": False, "total_steps": tokens * 2, "seconds_generate": 1.0,
            "greedy_prefix_chars": len(output) if prefix is None else prefix,
            "greedy_prefix_tokens": tokens if prefix is None else 3}


def test_stop_only_cuts_escaped_outputs_to_their_greedy_prefix():
    plain = _record("a", "อ่านจบ")
    assert stop_only(plain) == {**plain, "escaped": False}
    escaped = _record("b", "หัว ยอด อ่านต่อ", escapes=[{"rollback_tokens": 3}], prefix=7)
    cut = stop_only(escaped)
    assert cut["raw_output"] == "หัว ยอด" and cut["generated_tokens"] == 3 and cut["escaped"]
    assert not cut["reached_max_new_tokens"]


def test_control_checks_identity_and_greedy_prefix():
    greedy = {"a": {"raw_output": "อ่านจบ", "generated_tokens": 10},
              "b": {"raw_output": "หัว ยอด ยอด ยอด", "generated_tokens": 3072}}
    ok = control([_record("a", "อ่านจบ"), _record("b", "หัว ยอด อ่านต่อ", escapes=[{}], prefix=7)], greedy)
    assert ok["all_ok"] and (ok["no_escape"], ok["no_escape_identical"], ok["escaped"]) == (1, 1, 1)
    bad = control([_record("a", "อ่านจบ!"), _record("b", "หัว ยอX อ่านต่อ", escapes=[{}], prefix=7)], greedy)
    assert not bad["all_ok"] and bad["failed"] == ["a", "b"]
    assert not control([_record("z", "x")], greedy)["all_ok"]


def test_escape_summary():
    rows = [_record("a", "x"), _record("b", "y", escapes=[{}, {}], prefix=0), _record("c", "z", final_cut=True)]
    out = escape_summary(rows)
    assert (out["n"], out["escaped"], out["escapes"], out["final_cut"]) == (3, 2, 2, 1)
    assert out["kept_tokens"] == 30 and out["decoded_tokens"] == 60


def test_load_shards(tmp_path):
    for k, items in enumerate((["a", "c"], ["b"])):
        leg = tmp_path / "m3" / "E" / f"shard-{k}-of-2"
        leg.mkdir(parents=True)
        (leg / "records.jsonl").write_text("".join(json.dumps(_record(i, i)) + "\n" for i in items), "utf-8")
        (leg / "manifest.json").write_text(json.dumps({"items": len(items), "failures": []}), "utf-8")
    records, manifests = load_shards(tmp_path, "E", 2)
    assert sorted(r["id"] for r in records) == ["a", "b", "c"] and len(manifests) == 2
    (tmp_path / "m3" / "E" / "shard-1-of-2" / "manifest.json").write_text(
        json.dumps({"items": 2, "failures": []}), "utf-8")
    with pytest.raises(ValueError, match="manifest implies"):
        load_shards(tmp_path, "E", 2)
    with pytest.raises(FileNotFoundError):
        load_shards(tmp_path, "E", 3)


def test_m3_script_hashes_existing_files():
    spec = importlib.util.spec_from_file_location("m3k", ROOT / "scripts/model_survey_m3_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert all((ROOT / p).is_file() for p in module.HASHED)
    assert "src/labbs2026/model_survey/escape.py" in module.HASHED
