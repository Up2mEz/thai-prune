"""The post hoc rescoring rule for a <figure> that is never closed (scripts/model_survey_w4_figure_fix.py)."""

import importlib.util
from pathlib import Path

from labbs2026.thai_marks.extract import extract_text

_spec = importlib.util.spec_from_file_location(
    "figure_fix", Path(__file__).resolve().parents[1] / "scripts/model_survey_w4_figure_fix.py")
figure_fix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(figure_fix)


def test_text_after_an_unclosed_figure_is_kept():
    raw = "หัวข้อ\n<figure id='x'>\nข้อความของหน้า"
    assert "ข้อความของหน้า" not in extract_text(raw)  # extraction v2 swallows it
    assert "ข้อความของหน้า" in extract_text(figure_fix.fix_unclosed_figure(raw))


def test_a_closed_figure_is_left_alone():
    raw = "ก่อน <figure>คำอธิบายภาพ</figure> หลัง"
    assert figure_fix.fix_unclosed_figure(raw) == raw
    assert "คำอธิบายภาพ" not in extract_text(raw)


def test_text_without_a_figure_is_unchanged():
    raw = "ข่าว ข้าว"
    assert figure_fix.fix_unclosed_figure(raw) == raw
