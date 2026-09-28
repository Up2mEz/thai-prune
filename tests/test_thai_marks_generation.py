"""The T1 decoding settings are pinned, greedy, and read from config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from labbs2026.thai_marks.generation import describe_resolved, generation_kwargs

ROOT = Path(__file__).resolve().parents[1]
PINNED = {"do_sample": False, "num_beams": 1, "repetition_penalty": 1.0, "no_repeat_ngram_size": 0}


def test_registered_config_pins_greedy_decoding() -> None:
    config = yaml.safe_load((ROOT / "configs/thai_marks/t1_t2.yaml").read_text("utf-8"))
    assert config["t1"]["generation"] == PINNED
    kwargs = generation_kwargs(config["t1"]["generation"], config["t1"]["max_new_tokens"])
    assert kwargs == {**PINNED, "max_new_tokens": 3072}


@pytest.mark.parametrize("change", [{"do_sample": True}, {"num_beams": 4}])
def test_anything_but_greedy_is_refused(change: dict) -> None:
    with pytest.raises(ValueError, match="greedy"):
        generation_kwargs({**PINNED, **change}, 3072)


def test_every_setting_must_be_pinned_explicitly() -> None:
    settings = dict(PINNED)
    del settings["repetition_penalty"]
    with pytest.raises(ValueError, match="missing"):
        generation_kwargs(settings, 3072)


def test_sampling_settings_are_refused_rather_than_silently_ignored() -> None:
    with pytest.raises(ValueError, match="unregistered"):
        generation_kwargs({**PINNED, "temperature": 0.0}, 3072)


def test_resolved_config_separates_active_from_inactive_fields() -> None:
    resolved = {"do_sample": False, "num_beams": 1, "max_new_tokens": 3072,
                "repetition_penalty": 1.0, "temperature": 0.7, "top_p": 0.8, "top_k": 20}
    described = describe_resolved(resolved)
    assert described["active"]["do_sample"] is False
    assert described["inactive_because_greedy"]["temperature"] == 0.7
