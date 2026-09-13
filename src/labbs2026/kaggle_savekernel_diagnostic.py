"""Fail-closed Kaggle SaveKernel request diagnostics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


_REQUEST_ID_HEADERS = (
    "request-id",
    "x-request-id",
    "x-cloud-trace-context",
    "traceparent",
)


class _CaptureApiClient:
    def __init__(self) -> None:
        self.request: Any | None = None

    def save_kernel(self, request: Any) -> SimpleNamespace:
        self.request = request
        return SimpleNamespace(error=None)


class _NoNetworkClient:
    def __init__(self, capture: _CaptureApiClient) -> None:
        self.kernels = SimpleNamespace(
            kernels_api_client=SimpleNamespace(save_kernel=capture.save_kernel)
        )

    def __enter__(self) -> _NoNetworkClient:
        return self

    def __exit__(self, *_: Any) -> None:
        return None


def capture_request(folder: Path) -> dict[str, Any]:
    """Construct the SaveKernel request with a transport that cannot use network."""
    from kaggle.api.kaggle_api_extended import KaggleApi

    capture = _CaptureApiClient()
    api = KaggleApi()
    api.build_kaggle_client = lambda: _NoNetworkClient(capture)  # type: ignore[method-assign]
    api.kernels_push(str(folder))
    if capture.request is None:
        raise RuntimeError("Kaggle client did not construct a SaveKernel request")
    request = capture.request
    fields = request.to_dict()
    text = fields.pop("text")
    encoded = text.encode("utf-8")
    return {
        "folder": str(folder.resolve()),
        "network_calls": 0,
        "client_exception_type": None,
        "request_class": type(request).__name__,
        "endpoint": request.endpoint(),
        "endpoint_path": request.endpoint_path(),
        "http_method": request.method(),
        "request_fields_except_text": fields,
        "text": {
            "bytes_utf8": len(encoded),
            "characters": len(text),
            "line_count": text.count("\n") + 1,
            "sha256": hashlib.sha256(encoded).hexdigest(),
        },
    }


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    """Preserve evidence without replacing an existing artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        handle.write("\n")


def http_error_record(
    error: Exception, request_metadata: dict[str, Any]
) -> dict[str, Any]:
    """Extract the complete available response without request credentials."""
    response = getattr(error, "response", None)
    response_body = response.text if response is not None else None
    parsed_body: Any | None = None
    if response_body:
        try:
            parsed_body = json.loads(response_body)
        except json.JSONDecodeError:
            parsed_body = None
    headers = response.headers if response is not None else {}
    request_ids = {
        name: headers[name]
        for name in _REQUEST_ID_HEADERS
        if name in headers
    }
    return {
        "schema_version": 1,
        "diagnostic_scope": "SAVEKERNEL_HTTP_ERROR_NO_RETRY",
        "client_exception_type": f"{type(error).__module__}.{type(error).__name__}",
        "exception_message": str(error),
        "http_status": response.status_code if response is not None else None,
        "response_body": response_body,
        "response_json": parsed_body,
        "request_ids": request_ids,
        "sanitized_request_metadata": request_metadata,
        "credentials_recorded": False,
        "retry_performed": False,
    }


def submit_once_with_failure_capture(folder: Path, failure_output: Path) -> None:
    """Submit once and preserve a structured HTTP failure; never retry."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    from requests.exceptions import HTTPError

    request_metadata = capture_request(folder)
    api = KaggleApi()
    api.authenticate()
    try:
        api.kernels_push(str(folder))
    except HTTPError as error:
        write_json_exclusive(
            failure_output,
            http_error_record(error, request_metadata),
        )
        raise
