"""MODEL_SURVEY_M1: config rules, GPU queues, T1-identical conditions, leg loading and scoring."""

import copy
import gzip
import json
from pathlib import Path

import pytest
import yaml

from labbs2026.model_survey.analysis import (
    UnfinishedLeg,
    comparison_records,
    load_role,
    paired_f1_difference,
    references_by_id,
    score_role,
)
from labbs2026.model_survey.plan import resolve_prompt, select, validate

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / "configs/model_survey/m1.yaml").read_text("utf-8"))


def test_registered_config_is_valid_and_every_unit_runs_once():
    queues = validate(CONFIG)
    assert queues == [[("qwen3vl4b", 0, 2), ("paddle", 0, 1)], [("qwen3vl4b", 1, 2), ("wayu", 0, 1)]]


def test_conditions_are_t1s():
    t1 = yaml.safe_load((ROOT / "configs/thai_marks/t1_t2.yaml").read_text("utf-8"))
    assert CONFIG["benchmark"] == t1["benchmark"]
    assert {k: CONFIG["split"][k] for k in ("seed", "calibration_fraction", "run_on")} == \
        {k: t1["split"][k] for k in ("seed", "calibration_fraction", "run_on")}
    for key in ("dtype_preferred", "dtype_fallback", "attention", "image_policy"):
        assert CONFIG["runtime"][key] == t1["runtime"][key]
    assert CONFIG["runtime"]["max_new_tokens"] == t1["t1"]["max_new_tokens"]
    assert CONFIG["runtime"]["generation"] == t1["t1"]["generation"]
    assert CONFIG["runtime"]["use_cache"] is True                  # registration §8
    assert CONFIG["scoring"]["null_seed"] == t1["scoring"]["null_seed"]
    assert not set(CONFIG["models"]) & set(t1["models"])          # no model already in T1


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c["models"]["paddle"].update(revision="main"), "full commit"),
    (lambda c: c["models"]["wayu"].update(prompts=["TYPHOON_CARD"], primary_prompt="TYPHOON_CARD"),
     "unregistered"),
    (lambda c: c["models"]["wayu"].update(primary_prompt="BENCHMARK_QUESTION", prompts=["OCR_NATIVE"]),
     "primary"),
    (lambda c: c["gpu_queues"][1].remove("wayu/0"), "exactly once"),
    (lambda c: c["gpu_queues"][0].append("wayu/0"), "exactly once"),
    (lambda c: c["gpu_queues"][0].append("qwen3vl4b/2"), "exactly once"),
    (lambda c: c["models"]["paddle"].update(unit_deadline_hours=5.5), "budget cap"),
    (lambda c: c["models"]["wayu"].pop("unit_deadline_hours"), "budget cap"),
])
def test_validate_rejects(mutate, message):
    config = copy.deepcopy(CONFIG)
    mutate(config)
    with pytest.raises(ValueError, match=message):
        validate(config)


def test_select_keeps_each_unit_on_its_gpu():
    queues = select(validate(CONFIG), ["wayu", "paddle"])
    assert queues == [[("paddle", 0, 1)], [("wayu", 0, 1)]]
    with pytest.raises(ValueError):
        select(validate(CONFIG), ["typhoon"])


def test_resolve_prompt():
    prompts = CONFIG["prompts"]
    assert resolve_prompt("OCR_NATIVE", "อ่านข้อความ", prompts) == "OCR:"
    assert resolve_prompt("BENCHMARK_QUESTION", "อ่านข้อความ", prompts) == "อ่านข้อความ"
    with pytest.raises(ValueError):
        resolve_prompt("TYPHOON_CARD", "q", prompts)
    with pytest.raises(ValueError):
        resolve_prompt("BENCHMARK_QUESTION", "q", {**prompts, "BENCHMARK_QUESTION": "fixed text"})


def test_kaggle_script_hashes_only_existing_files():
    import importlib.util

    spec = importlib.util.spec_from_file_location("msk", ROOT / "scripts/model_survey_kaggle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert all((ROOT / p).is_file() for p in module.HASHED)
    assert "__LABBS_RUN_SPEC_B64__" in (ROOT / "infra/kaggle/model_survey_worker.py").read_text("utf-8")


REF = "ผู้ใหญ่ที่เป็นเบาหวานควรตรวจน้ำตาลก่อนอาหาร"
DROPPED = "ผูใหญทีเปนเบาหวานควรตรวจนำตาลกอนอาหาร"          # tone and upper marks lost


def _record(item, task, prompt, output, ref=REF):
    return {"id": item, "task": task, "category": "c", "reference": ref, "prompt_kind": prompt,
            "raw_output": output, "reached_max_new_tokens": False, "seconds_per_generated_token": 0.05,
            "generated_tokens": 10, "visual_tokens": 100, "prompt_tokens": 120, "seconds_generate": 0.5,
            "resized_size": [10, 10]}


def _leg(tmp_path, role, shards):
    for k, items in enumerate(shards):
        d = tmp_path / "m1" / role / (f"shard-{k}-of-{len(shards)}" if len(shards) > 1 else "")
        d.mkdir(parents=True)
        (d / "records.jsonl").write_text(
            "".join(json.dumps(_record(i, "Text recognition", "BENCHMARK_QUESTION", REF)) + "\n"
                    for i in items), encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps({"items": len(items), "failures": []}), "utf-8")
    return tmp_path


def test_load_role_merges_shards_and_checks_counts(tmp_path):
    records, manifests = load_role(_leg(tmp_path, "qwen3vl4b", [["a", "c"], ["b"]]), "qwen3vl4b",
                                   ["BENCHMARK_QUESTION"])
    assert sorted(r["id"] for r in records) == ["a", "b", "c"] and len(manifests) == 2
    with pytest.raises(ValueError, match="manifests imply"):
        load_role(tmp_path, "qwen3vl4b", ["BENCHMARK_QUESTION", "OCR_NATIVE"])


def test_load_role_refuses_unfinished_and_duplicates(tmp_path):
    _leg(tmp_path, "wayu", [["a", "b"]])
    (tmp_path / "m1" / "wayu" / "manifest.json").unlink()
    with pytest.raises(UnfinishedLeg):
        load_role(tmp_path, "wayu", ["BENCHMARK_QUESTION"])
    with pytest.raises(ValueError, match="twice"):
        load_role(_leg(tmp_path / "x", "paddle", [["a"], ["a"]]), "paddle", ["BENCHMARK_QUESTION"])


SENTENCES = (REF, "ความดันโลหิตสูงต้องวัดซ้ำอย่างน้อยสองครั้ง", "ไขมันในเลือดสูงเพิ่มความเสี่ยงโรคหัวใจ")


def _strip_marks(text):
    import re

    return re.sub("[ัิ-ฺ็-๎]", "", text)


def test_score_role_charges_lost_marks():
    # distinct references: T1's chance threshold pairs each reference with another item's output
    good = [_record(f"g{i}", "Text recognition", "OCR_NATIVE", s, ref=s) for i, s in enumerate(SENTENCES)]
    bad = [_record(f"g{i}", "Text recognition", "OCR_NATIVE", _strip_marks(s), ref=s)
           for i, s in enumerate(SENTENCES)]
    cell = "Text recognition / OCR_NATIVE"
    h_good = score_role(good, null_seed=1, max_cer=0.4, residual=True)["headline"][cell]
    h_bad = score_role(bad, null_seed=1, max_cer=0.4, residual=True)["headline"][cell]
    assert h_good["mark_f1"] == 1.0 and h_good["median_cer"] == 0.0 and h_good["located_rate"] == 1.0
    assert h_bad["mark_recall"] == 0.0 and h_bad["median_cer"] > 0


def test_paired_difference_sign_and_identity():
    from labbs2026.thai_marks.order_free import mark_counts

    a = {f"i{k}": mark_counts(REF, DROPPED if k % 2 else REF, residual=True) for k in range(8)}
    b = {f"i{k}": mark_counts(REF, REF, residual=True) for k in range(8)}
    same = paired_f1_difference(a, a, resamples=200, seed=1)
    assert same["difference"] == 0.0 and same["ci95"] == [0.0, 0.0]
    better = paired_f1_difference(a, b, resamples=200, seed=1)
    assert better["difference"] > 0 and better["ci95"][0] > 0 and better["n"] == 8


def test_comparison_records_take_this_runs_references(tmp_path):
    archive = tmp_path / "t1.json.gz"
    rows = [{"id": "a", "task": "Text recognition", "prompt_kind": "BENCHMARK_QUESTION", "raw_output": REF},
            {"id": "a", "task": "Text recognition", "prompt_kind": "TYPHOON_CARD", "raw_output": REF},
            {"id": "z", "task": "Text recognition", "prompt_kind": "BENCHMARK_QUESTION", "raw_output": REF}]
    with gzip.open(archive, "wt", encoding="utf-8") as handle:
        json.dump({"records": {"typhoon": rows}}, handle)
    refs = references_by_id([_record("a", "Text recognition", "OCR_NATIVE", REF)])
    out = comparison_records(archive, ["typhoon"], "BENCHMARK_QUESTION", refs)
    assert [(r["id"], r["reference"]) for r in out["typhoon"]] == [("a", REF)]
    with pytest.raises(ValueError, match="two references"):
        references_by_id([_record("a", "t", "p", REF), _record("a", "t", "p", REF, ref=DROPPED)])
