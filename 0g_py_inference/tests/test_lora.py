"""Tests for LoRA adapter management.

Covers TS PR #191 semantics: name resolution, idempotent deploy,
wait/no-wait paths, failed/timeout, and the convenience chat wrapper.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk import lora as lora_mod
from zerog_py_sdk.lora import (
    AdapterInfo,
    AdapterStatusResponse,
    DeployResponse,
    LoRADependencies,
    LoRAProcessor,
    make_adapter_name,
)


PROVIDER = "0xprovider"
TASK_ID = "task-abc-123"
BASE_MODEL = "Qwen2.5-0.5B-Instruct"
EXPECTED_NAME = "ft-Qwen2-5-0-5B-Instruct-task-abc-123"
ENDPOINT = "https://broker.example.com/v1/proxy"
BASE_URL = "https://broker.example.com"


class FakeDeps(LoRADependencies):
    def __init__(self, endpoint: str = ENDPOINT):
        self._endpoint = endpoint
        self.headers_calls: List[Optional[str]] = []

    def get_endpoint(self, provider_address: str) -> str:
        return self._endpoint

    def get_headers(
        self, provider_address: str, content: Optional[str] = None
    ) -> Dict[str, str]:
        self.headers_calls.append(content)
        return {"Authorization": "Bearer test"}


@pytest.fixture
def deps() -> FakeDeps:
    return FakeDeps()


@pytest.fixture
def processor(deps: FakeDeps) -> LoRAProcessor:
    return LoRAProcessor(deps, timeout=5)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """Make polling loops instant so tests don't wait on the wall clock."""
    monkeypatch.setattr(lora_mod.time, "sleep", lambda *_: None)


# ---------------------------------------------------------------------------
# make_adapter_name


class TestMakeAdapterName:
    def test_replaces_slashes_dots_spaces(self):
        assert make_adapter_name("a/b.c d", "task1") == "ft-a-b-c-d-task1"

    def test_strips_leading_trailing_dashes(self):
        # "/a." → "-a-" → trim → "a"
        assert make_adapter_name("/a.", "task1") == "ft-a-task1"

    def test_truncates_long_task_id(self):
        long_id = "abcdef0123456789xyz"
        assert make_adapter_name("model", long_id).endswith("-abcdef012345")

    def test_short_task_id_kept_intact(self):
        assert make_adapter_name(BASE_MODEL, TASK_ID) == EXPECTED_NAME


# ---------------------------------------------------------------------------
# Helpers — mock requests responses


def _resp(status: int, body: Any) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.content = b"x"
    r.json.return_value = body
    r.raise_for_status = MagicMock()
    if status >= 400:
        from requests import HTTPError

        r.raise_for_status.side_effect = HTTPError(f"HTTP {status}")
    return r


# ---------------------------------------------------------------------------
# list_adapters / get_adapter_status


class TestListAndStatus:
    def test_list_adapters_parses_payload(self, processor: LoRAProcessor):
        payload = {
            "adapters": [
                {
                    "adapterName": "ft-x-1",
                    "taskId": "1",
                    "baseModel": "x",
                    "userAddress": "0xu",
                    "state": "active",
                }
            ]
        }
        with patch.object(lora_mod.requests, "get", return_value=_resp(200, payload)) as g:
            result = processor.list_adapters(PROVIDER)
        assert g.call_args.args[0] == f"{BASE_URL}/v1/lora/adapters"
        assert len(result) == 1
        assert isinstance(result[0], AdapterInfo)
        assert result[0].adapter_name == "ft-x-1"
        assert result[0].state == "active"

    def test_list_adapters_handles_empty(self, processor: LoRAProcessor):
        with patch.object(lora_mod.requests, "get", return_value=_resp(200, {})):
            assert processor.list_adapters(PROVIDER) == []

    def test_get_adapter_status_parses(self, processor: LoRAProcessor):
        with patch.object(
            lora_mod.requests, "get",
            return_value=_resp(200, {"adapterName": "n", "state": "ready"}),
        ):
            s = processor.get_adapter_status(PROVIDER, "n")
        assert isinstance(s, AdapterStatusResponse)
        assert s.state == "ready"

    def test_endpoint_without_proxy_suffix(self):
        deps = FakeDeps(endpoint="https://broker.example.com")
        proc = LoRAProcessor(deps)
        with patch.object(
            lora_mod.requests, "get", return_value=_resp(200, {"adapters": []})
        ) as g:
            proc.list_adapters(PROVIDER)
        # No /v1/proxy to strip — base URL stays as-is.
        assert g.call_args.args[0] == "https://broker.example.com/v1/lora/adapters"


# ---------------------------------------------------------------------------
# resolve_adapter_name


class TestResolveAdapterName:
    def test_uses_broker_name_when_task_matches(self, processor: LoRAProcessor):
        payload = {
            "adapters": [
                {
                    "adapterName": "broker-assigned-name",
                    "taskId": TASK_ID,
                    "baseModel": BASE_MODEL,
                    "userAddress": "0xu",
                    "state": "ready",
                }
            ]
        }
        with patch.object(lora_mod.requests, "get", return_value=_resp(200, payload)):
            name = processor.resolve_adapter_name(PROVIDER, TASK_ID, BASE_MODEL)
        assert name == "broker-assigned-name"

    def test_falls_back_to_local_when_no_match(self, processor: LoRAProcessor):
        with patch.object(
            lora_mod.requests, "get", return_value=_resp(200, {"adapters": []})
        ):
            name = processor.resolve_adapter_name(PROVIDER, TASK_ID, BASE_MODEL)
        assert name == EXPECTED_NAME

    def test_falls_back_when_list_throws(self, processor: LoRAProcessor):
        with patch.object(
            lora_mod.requests, "get", side_effect=Exception("network")
        ):
            name = processor.resolve_adapter_name(PROVIDER, TASK_ID, BASE_MODEL)
        assert name == EXPECTED_NAME


# ---------------------------------------------------------------------------
# deploy_adapter


class TestDeployAdapter:
    def test_no_wait_posts_and_returns(self, processor, deps):
        # Status check (used for idempotent active-check) returns "pending",
        # then POST succeeds.
        get_resp = _resp(200, {"adapterName": EXPECTED_NAME, "state": "pending"})
        post_resp = _resp(200, {"message": "Deploy queued"})

        with patch.object(lora_mod.requests, "get") as g, \
             patch.object(lora_mod.requests, "post", return_value=post_resp) as p:
            # First .get is resolve_adapter_name (list_adapters); second is the
            # idempotent active-check.
            g.side_effect = [
                _resp(200, {"adapters": []}),
                get_resp,
            ]
            result = processor.deploy_adapter(PROVIDER, BASE_MODEL, TASK_ID)

        assert isinstance(result, DeployResponse)
        assert result.adapter_name == EXPECTED_NAME
        assert "Deploy queued" in result.message
        body = p.call_args.kwargs["json"]
        assert body == {"taskId": TASK_ID, "baseModel": BASE_MODEL}

    def test_already_active_skips_post(self, processor):
        with patch.object(lora_mod.requests, "get") as g, \
             patch.object(lora_mod.requests, "post") as p:
            g.side_effect = [
                _resp(200, {"adapters": []}),  # resolve
                _resp(200, {"adapterName": EXPECTED_NAME, "state": "active"}),
            ]
            result = processor.deploy_adapter(PROVIDER, BASE_MODEL, TASK_ID)

        assert "already deployed" in result.message
        p.assert_not_called()

    def test_wait_polls_until_active(self, processor):
        # GET sequence:
        #   1. initial resolve (list_adapters → empty, fall back to local)
        #   Phase-1 iter 1: 2. resolve again (still empty), 3. status=pending
        #   Phase-1 iter 2: 4. resolve again,               5. status=ready (break)
        #   Phase 2:       6. idempotent active-check (state=ready → POST)
        #   Phase 4 iter 1: 7. status=loading
        #   Phase 4 iter 2: 8. status=active (return)
        get_responses = [
            _resp(200, {"adapters": []}),                                  # 1
            _resp(200, {"adapters": []}),                                  # 2
            _resp(200, {"state": "pending", "adapterName": EXPECTED_NAME}),# 3
            _resp(200, {"adapters": []}),                                  # 4
            _resp(200, {"state": "ready",   "adapterName": EXPECTED_NAME}),# 5
            _resp(200, {"state": "ready",   "adapterName": EXPECTED_NAME}),# 6
            _resp(200, {"state": "loading", "adapterName": EXPECTED_NAME}),# 7
            _resp(200, {"state": "active",  "adapterName": EXPECTED_NAME}),# 8
        ]
        with patch.object(lora_mod.requests, "get", side_effect=get_responses), \
             patch.object(lora_mod.requests, "post",
                          return_value=_resp(200, {"message": "ok"})):
            states: List[str] = []
            result = processor.deploy_adapter(
                PROVIDER, BASE_MODEL, TASK_ID,
                wait=True, timeout_seconds=10,
                on_progress=states.append,
            )

        assert "deployed successfully" in result.message
        assert "pending" in states and "ready" in states

    def test_failed_state_raises(self, processor):
        get_responses = [
            _resp(200, {"adapters": []}),
            _resp(200, {"state": "pending", "adapterName": EXPECTED_NAME}),
            _resp(200, {"state": "failed",  "adapterName": EXPECTED_NAME}),
        ]
        with patch.object(lora_mod.requests, "get", side_effect=get_responses), \
             patch.object(lora_mod.requests, "post"):
            with pytest.raises(RuntimeError, match="preparation failed"):
                processor.deploy_adapter(
                    PROVIDER, BASE_MODEL, TASK_ID, wait=True, timeout_seconds=10,
                )

    def test_timeout_raises(self, processor, monkeypatch):
        # Force monotonic to leap past the deadline after the first status check.
        ticks = iter([0.0, 0.0, 999.0, 999.0, 999.0])
        monkeypatch.setattr(
            lora_mod.time, "monotonic", lambda: next(ticks, 999.0)
        )
        get_responses = [
            _resp(200, {"adapters": []}),
            _resp(200, {"state": "pending", "adapterName": EXPECTED_NAME}),
        ]
        with patch.object(lora_mod.requests, "get", side_effect=get_responses):
            with pytest.raises(TimeoutError, match="waiting for adapter"):
                processor.deploy_adapter(
                    PROVIDER, BASE_MODEL, TASK_ID, wait=True, timeout_seconds=1,
                )


# ---------------------------------------------------------------------------
# deploy_adapter_by_name


class TestDeployAdapterByName:
    def test_posts_with_adapter_name_body(self, processor):
        with patch.object(lora_mod.requests, "get",
                          return_value=_resp(200, {"state": "pending"})) as g, \
             patch.object(lora_mod.requests, "post",
                          return_value=_resp(200, {"message": "queued"})) as p:
            result = processor.deploy_adapter_by_name(PROVIDER, "my-name")
        assert result.adapter_name == "my-name"
        assert p.call_args.kwargs["json"] == {"adapterName": "my-name"}

    def test_already_active_skips_post(self, processor):
        with patch.object(lora_mod.requests, "get",
                          return_value=_resp(200, {"state": "active"})), \
             patch.object(lora_mod.requests, "post") as p:
            result = processor.deploy_adapter_by_name(PROVIDER, "my-name")
        assert "already deployed" in result.message
        p.assert_not_called()


# ---------------------------------------------------------------------------
# chat


class TestChat:
    def test_sends_adapter_as_model(self, processor, deps):
        chat_payload = {
            "id": "x",
            "choices": [{"message": {"role": "assistant", "content": "hi"}}],
        }
        with patch.object(lora_mod.requests, "post",
                          return_value=_resp(200, chat_payload)) as p:
            result = processor.chat(PROVIDER, "my-adapter", "hello")
        assert result == chat_payload
        url = p.call_args.args[0]
        body = p.call_args.kwargs["json"]
        assert url == f"{ENDPOINT}/chat/completions"
        assert body["model"] == "my-adapter"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["content"] == "hello"
        # Headers were generated with body content (signed payload).
        assert deps.headers_calls[-1] is not None
