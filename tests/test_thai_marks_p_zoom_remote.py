"""P-ZOOM (`t4`) in the Kaggle remote entrypoint: resume keys and the frozen page list."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from labbs2026.thai_marks.remote import completed_keys, t4_page_ids

ROOT = Path(__file__).resolve().parents[1]


def _source(tmp_path: Path, ids: list[str]) -> tuple[Path, dict]:
    pages = tmp_path / "pages.json"
    pages.write_text(json.dumps({"pages": [{"id": i} for i in ids]}), encoding="utf-8")
    spec = {"t4": {"pages_file": "pages.json",
                   "pages_sha256": hashlib.sha256(pages.read_bytes()).hexdigest()}}
    return tmp_path, spec


def test_t4_resume_keys_are_page_and_tile(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in (
        {"id": "A1", "tile": 0}, {"id": "A1", "tile": 3}, {"id": "B2", "tile": 1})), encoding="utf-8")
    assert completed_keys(path, "t4") == {("A1", 0), ("A1", 3), ("B2", 1)}


def test_t4_pages_are_read_from_the_hashed_list(tmp_path: Path) -> None:
    source, spec = _source(tmp_path, ["A1", "B2"])
    assert t4_page_ids(spec, source, {"A1", "B2", "C3"}) == ["A1", "B2"]


def test_t4_refuses_a_page_list_that_does_not_match_its_hash(tmp_path: Path) -> None:
    source, spec = _source(tmp_path, ["A1"])
    (source / "pages.json").write_text(json.dumps({"pages": [{"id": "A1"}, {"id": "B2"}]}),
                                       encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        t4_page_ids(spec, source, {"A1", "B2"})


def test_t4_refuses_a_page_outside_the_calibration_split(tmp_path: Path) -> None:
    source, spec = _source(tmp_path, ["A1", "LOCKED9"])
    with pytest.raises(RuntimeError, match="outside the calibration split.*LOCKED9"):
        t4_page_ids(spec, source, {"A1"})


def test_the_committed_page_list_matches_its_hash_in_the_config() -> None:
    config = yaml.safe_load((ROOT / "configs/thai_marks/p_zoom.yaml").read_text(encoding="utf-8"))
    data = (ROOT / config["pages"]["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == config["pages"]["sha256"]
    payload = json.loads(data.decode("utf-8"))
    assert payload["totals"] == {"pages": 21, "absent_lines": 71, "absent_marks": 387,
                                 "control_lines": 42}  # P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md §2
    assert len({p["id"] for p in payload["pages"]}) == 21
    assert "reference" not in json.dumps(payload["pages"])  # indices only, no reference text


def test_the_probe_is_a_draft_until_authorized() -> None:
    config = yaml.safe_load((ROOT / "configs/thai_marks/p_zoom.yaml").read_text(encoding="utf-8"))
    assert config["roles"] == ["typhoon"] and config["prompt"] == "TYPHOON_CARD"
    assert config["tiling"] == {"rows": 2, "cols": 2, "overlap": 0.15}
    assert config["status"] in {"DRAFT", "APPROVED"}


def test_t6_resume_keys_include_the_view() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "records.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in (
            {"id": "A1", "view": "pad", "tile": 0}, {"id": "A1", "view": "bands", "tile": 2})),
            encoding="utf-8")
        assert completed_keys(path, "t6") == {("A1", "pad", 0), ("A1", "bands", 2)}


def test_t6_reads_its_page_list_under_its_own_spec_key(tmp_path: Path) -> None:
    source, spec = _source(tmp_path, ["A1"])
    assert t4_page_ids({"t6": spec["t4"]}, source, {"A1"}, "t6") == ["A1"]


def test_p_zoom2_config_shares_the_probes_frozen_pages_and_defines_three_views() -> None:
    one = yaml.safe_load((ROOT / "configs/thai_marks/p_zoom.yaml").read_text(encoding="utf-8"))
    two = yaml.safe_load((ROOT / "configs/thai_marks/p_zoom2.yaml").read_text(encoding="utf-8"))
    assert two["pages"] == one["pages"]
    assert [v["name"] for v in two["views"]] == ["pad", "scale90", "bands"]
    assert two["roles"] == ["typhoon"] and two["prompt"] == "TYPHOON_CARD"
    assert two["status"] in {"DRAFT", "APPROVED"}


def test_p_band_config_is_a_disjoint_complement_of_the_p_zoom_pages() -> None:
    band = yaml.safe_load((ROOT / "configs/thai_marks/p_band.yaml").read_text(encoding="utf-8"))
    data = (ROOT / band["pages"]["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == band["pages"]["sha256"]
    ids = {p["id"] for p in json.loads(data.decode("utf-8"))["pages"]}
    zoom = json.loads((ROOT / "configs/thai_marks/p_zoom_pages.json").read_text(encoding="utf-8"))
    zoom_ids = {p["id"] for p in zoom["pages"]}
    assert len(ids) == 48 and not ids & zoom_ids  # 48 + 21 = the 69 Full-page calibration items
    assert [v["name"] for v in band["views"]] == ["bands100"]
    one = yaml.safe_load((ROOT / "configs/thai_marks/p_zoom3.yaml").read_text(encoding="utf-8"))
    assert band["views"][0] == next(v for v in one["views"] if v["name"] == "bands100")
    assert band["roles"] == ["typhoon"] and band["prompt"] == "TYPHOON_CARD"
    assert band["status"] in {"DRAFT", "APPROVED"}
