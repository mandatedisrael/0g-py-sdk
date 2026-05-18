"""Tests for async inference helpers."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.exceptions import NetworkError
from zerog_py_sdk.models import AsyncInferenceJob, AsyncInferenceSubmission


PROVIDER = "0xprovider"
PROXY_ENDPOINT = "https://broker.example.com/v1/proxy"
ASYNC_ENDPOINT = "https://broker.example.com/v1/async"


def _resp(
    status: int, body: Any, headers: Optional[Dict[str, str]] = None
) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.content = b"x"
    response.headers = headers or {}
    response.json.return_value = body
    response.raise_for_status = MagicMock()
    if status >= 400:
        from requests import HTTPError

        response.raise_for_status.side_effect = HTTPError(f"HTTP {status}")
    return response


@pytest.fixture
def manager() -> InferenceManager:
    manager = object.__new__(InferenceManager)
    manager.get_service_metadata = MagicMock(
        return_value={"endpoint": PROXY_ENDPOINT, "model": "flux-dev"}
    )
    manager.get_request_headers = MagicMock(
        return_value={"Authorization": "Bearer test"}
    )
    return manager


def test_get_async_service_metadata(manager: InferenceManager):
    metadata = manager.get_async_service_metadata(PROVIDER)

    assert metadata.endpoint == ASYNC_ENDPOINT
    assert metadata.model == "flux-dev"


def test_submit_async_image_generation_posts_json(manager: InferenceManager):
    request_body = {"model": "flux-dev", "prompt": "A sea otter"}
    with patch(
        "zerog_py_sdk.inference.requests.post",
        return_value=_resp(202, {"jobId": "job-123", "status": "pending"}),
    ) as post:
        result = manager.submit_async_image_generation(PROVIDER, request_body)

    assert isinstance(result, AsyncInferenceSubmission)
    assert result.job_id == "job-123"
    assert result.status == "pending"
    assert post.call_args.args[0] == f"{ASYNC_ENDPOINT}/images/generations"
    assert post.call_args.kwargs["headers"]["Content-Type"] == "application/json"
    assert post.call_args.kwargs["json"] == request_body
    manager.get_request_headers.assert_called_once()


def test_submit_async_image_edit_posts_multipart(manager: InferenceManager):
    with patch(
        "zerog_py_sdk.inference.requests.post",
        return_value=_resp(202, {"jobId": "job-999", "status": "pending"}),
    ) as post:
        result = manager.submit_async_image_edit(
            PROVIDER,
            data={"model": "flux-dev", "prompt": "Add sunglasses"},
            files={"image": ("otter.png", b"png-bytes", "image/png")},
        )

    assert result.job_id == "job-999"
    assert post.call_args.args[0] == f"{ASYNC_ENDPOINT}/images/edits"
    assert "Content-Type" not in post.call_args.kwargs["headers"]
    assert post.call_args.kwargs["files"]["image"][0] == "otter.png"


def test_get_async_job_parses_retry_after(manager: InferenceManager):
    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_resp(
            200,
            {"status": "processing", "data": None},
            headers={"Retry-After": "7"},
        ),
    ) as get:
        result = manager.get_async_job(PROVIDER, "job-42")

    assert isinstance(result, AsyncInferenceJob)
    assert result.job_id == "job-42"
    assert result.status == "processing"
    assert result.retry_after == 7.0
    assert get.call_args.args[0] == f"{ASYNC_ENDPOINT}/jobs/job-42"


def test_wait_for_async_job_uses_retry_after(manager: InferenceManager, monkeypatch):
    jobs = [
        AsyncInferenceJob(job_id="job-1", status="pending", retry_after=2.0),
        AsyncInferenceJob(job_id="job-1", status="processing", retry_after=3.0),
        AsyncInferenceJob(
            job_id="job-1",
            status="completed",
            data={"data": [{"b64_json": "abc"}]},
        ),
    ]
    sleeps = []

    def fake_sleep(value: float):
        sleeps.append(value)

    monkeypatch.setattr("zerog_py_sdk.inference.time.sleep", fake_sleep)
    manager.get_async_job = MagicMock(side_effect=jobs)

    result = manager.wait_for_async_job(PROVIDER, "job-1", timeout_seconds=30)

    assert result.status == "completed"
    assert sleeps == [2.0, 3.0]


def test_submit_async_request_wraps_network_errors(manager: InferenceManager):
    with patch(
        "zerog_py_sdk.inference.requests.post",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(NetworkError) as exc_info:
            manager.submit_async_image_generation(
                PROVIDER, {"model": "flux-dev", "prompt": "hello"}
            )
    assert "Failed to submit async request" in str(exc_info.value)
