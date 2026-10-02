"""Parallel sessions get distinct Kaggle kernel and dataset slugs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "thai_marks_kaggle", Path(__file__).resolve().parents[1] / "scripts" / "thai_marks_kaggle.py")
thai_marks_kaggle = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(thai_marks_kaggle)


def test_default_slugs_are_unchanged() -> None:
    assert thai_marks_kaggle.KERNEL_SLUG == "labbs2026-thai-marks-t1-t2"
    assert thai_marks_kaggle.dataset_slugs(thai_marks_kaggle.KERNEL_SLUG) == (
        "labbs2026-thai-marks-t1-t2-resume", "labbs2026-thai-marks-t1-t2-t3-cases")


def test_another_kernel_slug_owns_its_own_datasets() -> None:
    a = thai_marks_kaggle.dataset_slugs("labbs2026-thai-marks-t1-t2")
    b = thai_marks_kaggle.dataset_slugs("labbs2026-thai-marks-pzoom")
    assert not set(a) & set(b)


def _kaggle_slugify(title: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def test_the_title_resolves_to_the_kernel_slug() -> None:
    for slug in ("labbs2026-thai-marks-t1-t2", "labbs2026-thai-marks-pzoom",
                 "labbs2026-thai-marks-t5-smoke"):
        assert _kaggle_slugify(thai_marks_kaggle.kernel_title(slug)) == slug
