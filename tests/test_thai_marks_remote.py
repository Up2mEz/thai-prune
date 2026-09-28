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
