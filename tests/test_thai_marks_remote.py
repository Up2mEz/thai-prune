"""Tests for the resume/checkpoint logic in the Kaggle remote worker entrypoint.

`labbs2026.thai_marks.remote` imports torch/transformers/datasets lazily inside
`main()`, so `completed_keys` (a pure function over `records.jsonl`) is safe to
import and test without those heavy, GPU-oriented dependencies installed.
"""

from __future__ import annotations

import json
from pathlib import Path

from labbs2026.thai_marks.remote import completed_keys


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def test_completed_keys_is_empty_for_a_missing_file(tmp_path: Path) -> None:
    assert completed_keys(tmp_path / "records.jsonl", "t1") == set()


def test_completed_keys_is_empty_for_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text("", encoding="utf-8")
    assert completed_keys(path, "t2") == set()


def test_t1_keys_are_id_and_prompt_kind_pairs(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    _write_jsonl(path, [
        {"id": "A1", "prompt_kind": "TYPHOON_CARD", "raw_output": "x"},
        {"id": "A1", "prompt_kind": "BENCHMARK_QUESTION", "raw_output": "y"},
        {"id": "A2", "prompt_kind": "TYPHOON_CARD", "raw_output": "z"},
    ])
    assert completed_keys(path, "t1") == {
        ("A1", "TYPHOON_CARD"), ("A1", "BENCHMARK_QUESTION"), ("A2", "TYPHOON_CARD"),
    }


def test_t2_keys_are_ids_only(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    _write_jsonl(path, [
        {"id": "A1", "sites": []},
        {"id": "A2", "sites": []},
    ])
    assert completed_keys(path, "t2") == {"A1", "A2"}


def test_completed_keys_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"id": "A1", "sites": []}\n\n\n', encoding="utf-8")
    assert completed_keys(path, "t2") == {"A1"}


def test_shards_partition_the_items_exactly_and_stay_balanced() -> None:
    from labbs2026.thai_marks.remote import shard_items
    items = list(range(178))
    parts = [shard_items(items, s, 2) for s in range(2)]
    assert sorted(parts[0] + parts[1]) == items
    assert not set(parts[0]) & set(parts[1])
    assert abs(len(parts[0]) - len(parts[1])) <= 1
    assert shard_items(items, 0, 1) == items


def test_t5_keys_include_the_arm(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    _write_jsonl(path, [
        {"id": "A1", "prompt_kind": "TYPHOON_CARD", "arm": "greedy", "raw_output": "x"},
        {"id": "A1", "prompt_kind": "TYPHOON_CARD", "arm": "ngram_block", "raw_output": "x"},
    ])
    assert completed_keys(path, "t5") == {
        ("A1", "TYPHOON_CARD", "greedy"), ("A1", "TYPHOON_CARD", "ngram_block")}


class _Tok:
    def encode(self, text, add_special_tokens=False):
        return {"<td>": [11, 29], "</td>": [60, 61, 29]}[text]


def test_t5_processors_are_fresh_per_call_and_report_the_whitelist() -> None:
    from labbs2026.thai_marks.remote import t5_processors

    arm = {"name": "ngram_block", "repetition_penalty": 1.0,
           "ngram_block": {"ngram_size": 30, "window_size": 90,
                           "whitelist_texts": ["<td>", "</td>"]}}
    first, built = t5_processors(arm, _Tok())
    second, _ = t5_processors(arm, _Tok())
    assert first[0] is not second[0]
    assert (first[0].ngram_size, first[0].window_size) == (30, 90)
    assert first[0].whitelist == {11, 29, 60, 61}
    assert built == {"whitelist_ids": [11, 29, 60, 61]}
    assert t5_processors({"name": "greedy", "repetition_penalty": 1.0, "ngram_block": None},
                         _Tok()) == ([], {})


def test_every_test_choice_has_its_own_item_branch() -> None:
    # 2026-10-03: a silent edit failure sent t5 into T2's `else:` branch.
    import re
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "src/labbs2026/thai_marks/remote.py"
              ).read_text(encoding="utf-8")
    choices = re.search(r'"--test", choices=\(([^)]*)\)', source).group(1)
    for test in re.findall(r'"(t\d)"', choices):
        if test == "t3":  # T3 runs through _run_t3 before the item loop
            continue
        assert f'args.test == "{test}":' in source, test
    assert "no item loop for test" in source


def test_load_cases_finds_and_checks_the_named_file(tmp_path: Path) -> None:
    import hashlib

    import pytest

    from labbs2026.thai_marks.remote import load_cases

    folder = tmp_path / "ds"
    folder.mkdir()
    path = folder / "t6_cases.json"
    path.write_text('{"cases": [{"case": "a"}]}', encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert load_cases({"t6_cases_sha256": digest}, "t6", root=tmp_path) == [{"case": "a"}]
    with pytest.raises(RuntimeError):
        load_cases({"t6_cases_sha256": "0" * 64}, "t6", root=tmp_path)
    with pytest.raises(RuntimeError):
        load_cases({}, "t3", root=tmp_path)
