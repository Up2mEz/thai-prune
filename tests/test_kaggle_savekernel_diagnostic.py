from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from labbs2026.kaggle_savekernel_diagnostic import capture_request, http_error_record


def test_capture_request_never_uses_network(tmp_path: Path) -> None:
    pytest.importorskip("kaggle")
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "worker.py").write_text("print('ok')\n", encoding="utf-8")
    (staging / "kernel-metadata.json").write_text(
        json.dumps(
            {
                "id": "owner/slug",
                "title": "Title",
                "code_file": "worker.py",
                "language": "python",
                "kernel_type": "script",
                "is_private": True,
                "enable_gpu": True,
                "enable_internet": True,
                "enable_tpu": False,
                "machine_shape": "NvidiaTeslaT4",
            }
        ),
        encoding="utf-8",
    )

    result = capture_request(staging)

    assert result["network_calls"] == 0
    assert result["endpoint"] == "/api/v1/kernels/push"
    assert result["http_method"] == "POST"
    assert result["text"]["bytes_utf8"] == 12


def test_http_error_record_preserves_body_and_request_id() -> None:
    response = SimpleNamespace(
        status_code=400,
        text=(
            '{"code":400,"message":"validation failed",'
            '"errors":{"text":["too large"]}}'
        ),
        headers={"Content-Type": "application/json", "x-request-id": "request-test"},
    )
    error = RuntimeError("400 Client Error")
    error.response = response  # type: ignore[attr-defined]

    record = http_error_record(error, {"endpoint": "/api/v1/kernels/push"})

    assert record["http_status"] == 400
    assert record["response_json"]["errors"]["text"] == ["too large"]
    assert record["request_ids"] == {"x-request-id": "request-test"}
    assert record["credentials_recorded"] is False
    assert record["retry_performed"] is False
