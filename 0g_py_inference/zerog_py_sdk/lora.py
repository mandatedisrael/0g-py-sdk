"""
LoRA adapter management for the 0G Compute Network SDK.

Ports the TS SDK's `LoRAProcessor` (src.ts/sdk/inference/broker/lora.ts) and
`makeAdapterName` helper (src.ts/sdk/common/utils/adapter-name.ts).

Lets users deploy a fine-tuned LoRA adapter to a provider's inference GPU and
chat with it via the standard inference endpoint. Used after fine-tuning's
`acknowledge_model` to actually serve the trained adapter.

The broker exposes three HTTP endpoints (under the broker base URL, which is
the inference endpoint with the `/v1/proxy` suffix removed):

    GET  /v1/lora/adapters
    GET  /v1/lora/adapters/{name}
    POST /v1/lora/adapters/deploy
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import requests

from .exceptions import NetworkError


logger = logging.getLogger(__name__)


# Polling cadence and timeout — match TS SDK constants.
# TS uses milliseconds; Python time.sleep takes seconds.
ADAPTER_POLL_INTERVAL_S: float = 3.0   # TS: ADAPTER_POLL_INTERVAL_MS = 3000
DEPLOY_POLL_INTERVAL_S: float = 2.0    # TS: DEPLOY_POLL_INTERVAL_MS = 2000
DEFAULT_DEPLOY_TIMEOUT_SECONDS: int = 120

# All known adapter lifecycle states reported by the broker.
# Source: src.ts/sdk/inference/broker/lora.ts AdapterState union.
ADAPTER_STATES = (
    "init",
    "pending",
    "downloading",
    "ready",
    "active",
    "loading",
    "offloaded",
    "archived",
    "failed",
)


def make_adapter_name(base_model: str, task_id: str) -> str:
    """
    Build a deterministic LoRA adapter name from a base model and task ID.

    Must match the broker-side Go ``MakeAdapterName()`` byte-for-byte; the
    broker uses the resulting string as a registry key. Mirrors
    ``src.ts/sdk/common/utils/adapter-name.ts``.

    Replaces ``/``, ``.``, and whitespace with ``-``, strips leading/trailing
    dashes, then truncates the task ID to 12 characters.

    Examples:
        >>> make_adapter_name("Qwen2.5-0.5B-Instruct", "0xabc123def456789")
        'ft-Qwen2-5-0-5B-Instruct-0xabc123def4'
    """
    sanitized = re.sub(r"[/.\s]", "-", base_model).strip("-")
    short = task_id[:12]
    return f"ft-{sanitized}-{short}"


@dataclass
class AdapterInfo:
    """A LoRA adapter known to the provider's broker."""

    adapter_name: str
    task_id: str
    base_model: str
    user_address: str
    state: str
    storage_path: Optional[str] = None
    storage_root_hash: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdapterInfo":
        """Parse a broker JSON payload (camelCase) into a Python dataclass."""
        return cls(
            adapter_name=data.get("adapterName", ""),
            task_id=data.get("taskId", ""),
            base_model=data.get("baseModel", ""),
            user_address=data.get("userAddress", ""),
            state=data.get("state", ""),
            storage_path=data.get("storagePath"),
            storage_root_hash=data.get("storageRootHash"),
            error=data.get("error"),
        )


@dataclass
class AdapterStatusResponse:
    """Status payload returned by ``GET /v1/lora/adapters/{name}``."""

    adapter_name: str
    state: str
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdapterStatusResponse":
        return cls(
            adapter_name=data.get("adapterName", ""),
            state=data.get("state", ""),
            error=data.get("error"),
        )


@dataclass
class DeployResponse:
    """Result of a deploy call."""

    message: str
    adapter_name: Optional[str] = None


class LoRADependencies:
    """
    Minimal interface the LoRA processor needs from the inference manager.

    Mirrors the TS ``LoRADependencies`` interface. Defining this as a separate
    object keeps the processor decoupled from ``InferenceManager`` (easier to
    test in isolation).
    """

    def get_endpoint(self, provider_address: str) -> str:
        raise NotImplementedError

    def get_headers(
        self, provider_address: str, content: Optional[str] = None
    ) -> Dict[str, str]:
        raise NotImplementedError


class LoRAProcessor:
    """
    Manage LoRA adapters on a provider's inference GPU.

    Use ``deploy_adapter`` after fine-tuning to make a trained adapter
    servable, then ``chat`` (or your own request to the inference endpoint
    with ``model=adapter_name``) to use it.

    Example:
        >>> broker.inference.lora.deploy_adapter(
        ...     provider, base_model="Qwen2.5-0.5B-Instruct",
        ...     task_id=task_id, wait=True,
        ... )
        >>> result = broker.inference.lora.chat(provider, adapter_name, "hi")
    """

    def __init__(self, deps: LoRADependencies, timeout: int = 30):
        """
        Args:
            deps: Provider for endpoint URL and authenticated headers.
            timeout: Per-request HTTP timeout in seconds (default 30).
                Polling timeouts are separate (see ``deploy_adapter``).
        """
        self._deps = deps
        self._timeout = timeout

    # --- internals --------------------------------------------------------

    def _broker_base_url(self, provider_address: str) -> str:
        endpoint = self._deps.get_endpoint(provider_address)
        # Inference endpoints are advertised as ".../v1/proxy"; the LoRA admin
        # API lives at the broker root, so strip the proxy suffix if present.
        if endpoint.endswith("/v1/proxy"):
            return endpoint[: -len("/v1/proxy")]
        return endpoint

    def _get(self, url: str, headers: Dict[str, str]) -> Any:
        try:
            resp = requests.get(url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise NetworkError(f"GET {url} failed: {e}") from e

    def _post(self, url: str, headers: Dict[str, str], json_body: Any) -> Any:
        try:
            resp = requests.post(
                url, headers=headers, json=json_body, timeout=self._timeout
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.RequestException as e:
            raise NetworkError(f"POST {url} failed: {e}") from e

    # --- public API -------------------------------------------------------

    def list_adapters(self, provider_address: str) -> List[AdapterInfo]:
        """List all adapters known to the provider's broker."""
        base_url = self._broker_base_url(provider_address)
        headers = self._deps.get_headers(provider_address)
        data = self._get(f"{base_url}/v1/lora/adapters", headers)
        return [AdapterInfo.from_dict(a) for a in (data.get("adapters") or [])]

    def get_adapter_status(
        self, provider_address: str, adapter_name: str
    ) -> AdapterStatusResponse:
        """Fetch the current state of a single adapter."""
        base_url = self._broker_base_url(provider_address)
        headers = self._deps.get_headers(provider_address)
        data = self._get(f"{base_url}/v1/lora/adapters/{adapter_name}", headers)
        return AdapterStatusResponse.from_dict(data)

    def resolve_adapter_name(
        self, provider_address: str, task_id: str, base_model: str
    ) -> str:
        """
        Look up the broker-assigned adapter name for a task; fall back to the
        deterministic local name if the broker hasn't registered it yet.
        """
        local_name = make_adapter_name(base_model, task_id)
        try:
            adapters = self.list_adapters(provider_address)
            for a in adapters:
                if a.task_id == task_id and a.adapter_name:
                    return a.adapter_name
        except Exception:
            # Broker may not have processed the deliverable event yet —
            # caller will retry. Falling back is safe because the broker uses
            # the same naming function on its side.
            pass
        return local_name

    def deploy_adapter(
        self,
        provider_address: str,
        base_model: str,
        task_id: str,
        *,
        wait: bool = False,
        timeout_seconds: int = DEFAULT_DEPLOY_TIMEOUT_SECONDS,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> DeployResponse:
        """
        Deploy a LoRA adapter from storage onto the provider's inference GPU.

        Idempotent: if the adapter is already ``active``, no POST is sent.

        Args:
            provider_address: Provider whose GPU should serve the adapter.
            base_model: Base model the adapter was trained on (e.g. the
                ``pre_trained_model_name`` passed to ``create_task``).
            task_id: Fine-tuning task ID returned by ``create_task``.
            wait: Block until the adapter reaches ``active`` (or fails).
            timeout_seconds: Total budget across both wait phases.
            on_progress: Callback invoked with each new state string.

        Returns:
            ``DeployResponse`` with the broker's message and resolved name.

        Raises:
            TimeoutError: ``wait=True`` and the adapter didn't go active in time.
            RuntimeError: Adapter entered the ``failed`` state.
            NetworkError: Underlying HTTP call failed.
        """
        base_url = self._broker_base_url(provider_address)
        deadline = time.monotonic() + timeout_seconds if wait else 0.0

        adapter_name = self.resolve_adapter_name(
            provider_address, task_id, base_model
        )
        local_name = make_adapter_name(base_model, task_id)
        name_resolved = adapter_name != local_name

        # Phase 1: wait for the adapter to reach ready/active before deploying.
        # Skipped when wait=False so users can fire-and-forget.
        if wait:
            last_state = ""
            while time.monotonic() < deadline:
                if not name_resolved:
                    try:
                        resolved = self.resolve_adapter_name(
                            provider_address, task_id, base_model
                        )
                        if resolved != local_name:
                            adapter_name = resolved
                            name_resolved = True
                    except Exception:
                        pass

                try:
                    status = self.get_adapter_status(
                        provider_address, adapter_name
                    )
                    if status.state and status.state != last_state:
                        last_state = status.state
                        if on_progress:
                            on_progress(status.state)
                    if status.state in ("ready", "active"):
                        break
                    if status.state == "failed":
                        break
                except Exception:
                    # Adapter not registered yet — keep polling.
                    pass

                time.sleep(ADAPTER_POLL_INTERVAL_S)

            if last_state == "failed":
                raise RuntimeError(
                    "Adapter preparation failed. Check broker logs for details."
                )
            if (
                time.monotonic() >= deadline
                and last_state not in ("ready", "active")
            ):
                raise TimeoutError(
                    f"Timed out after {timeout_seconds}s waiting for adapter "
                    f"to be ready (last state: {last_state or 'not found'})"
                )

        # Phase 2: idempotent active-check. Avoid a redundant POST.
        try:
            current = self.get_adapter_status(provider_address, adapter_name)
            if current.state == "active":
                return DeployResponse(
                    message="Adapter is already deployed and active!",
                    adapter_name=adapter_name,
                )
        except Exception:
            # Status fetch failed (maybe not registered) — proceed to deploy.
            pass

        # Phase 3: trigger deployment.
        auth_headers = self._deps.get_headers(provider_address)
        deploy_data = self._post(
            f"{base_url}/v1/lora/adapters/deploy",
            auth_headers,
            {"taskId": task_id, "baseModel": base_model},
        )
        result = DeployResponse(
            message=deploy_data.get("message") or "Deploy request sent",
            adapter_name=adapter_name,
        )

        # Phase 4: optionally wait for active.
        if wait:
            while time.monotonic() < deadline:
                try:
                    status = self.get_adapter_status(
                        provider_address, adapter_name
                    )
                    if status.state == "active":
                        result.message = (
                            "Adapter deployed successfully! "
                            "You can now chat with it."
                        )
                        return result
                    if status.state == "failed":
                        raise RuntimeError("Adapter deployment failed.")
                    if on_progress:
                        on_progress(status.state)
                except RuntimeError:
                    raise
                except Exception:
                    pass
                time.sleep(DEPLOY_POLL_INTERVAL_S)

            raise TimeoutError(
                f"Timed out after {timeout_seconds}s waiting for "
                f"deployment to complete."
            )

        return result

    def deploy_adapter_by_name(
        self,
        provider_address: str,
        adapter_name: str,
        *,
        wait: bool = False,
        timeout_seconds: int = DEFAULT_DEPLOY_TIMEOUT_SECONDS,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> DeployResponse:
        """
        Deploy by adapter name (when the caller already knows it).

        Same semantics as ``deploy_adapter`` but skips name resolution.
        """
        base_url = self._broker_base_url(provider_address)
        deadline = time.monotonic() + timeout_seconds if wait else 0.0

        try:
            current = self.get_adapter_status(provider_address, adapter_name)
            if current.state == "active":
                return DeployResponse(
                    message="Adapter is already deployed and active!",
                    adapter_name=adapter_name,
                )
        except Exception:
            pass

        auth_headers = self._deps.get_headers(provider_address)
        deploy_data = self._post(
            f"{base_url}/v1/lora/adapters/deploy",
            auth_headers,
            {"adapterName": adapter_name},
        )
        result = DeployResponse(
            message=deploy_data.get("message") or "Deploy request sent",
            adapter_name=adapter_name,
        )

        if wait:
            while time.monotonic() < deadline:
                try:
                    status = self.get_adapter_status(
                        provider_address, adapter_name
                    )
                    if status.state == "active":
                        result.message = (
                            "Adapter deployed successfully! "
                            "You can now chat with it."
                        )
                        return result
                    if status.state == "failed":
                        raise RuntimeError("Adapter deployment failed.")
                    if on_progress:
                        on_progress(status.state)
                except RuntimeError:
                    raise
                except Exception:
                    pass
                time.sleep(DEPLOY_POLL_INTERVAL_S)

            raise TimeoutError(
                f"Timed out after {timeout_seconds}s waiting for "
                f"deployment to complete."
            )

        return result

    def chat(
        self,
        provider_address: str,
        adapter_name: str,
        message: str,
        *,
        system_prompt: str = "You are a helpful assistant.",
    ) -> Dict[str, Any]:
        """
        Convenience wrapper: send a chat message routed to a deployed adapter.

        Equivalent to calling the inference endpoint directly with
        ``model=adapter_name``. Returned dict is the raw OpenAI-style
        ``/chat/completions`` response.
        """
        import json

        endpoint = self._deps.get_endpoint(provider_address)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]
        body = {"model": adapter_name, "messages": messages}
        headers = self._deps.get_headers(provider_address, json.dumps(body))

        try:
            resp = requests.post(
                f"{endpoint}/chat/completions",
                headers={"Content-Type": "application/json", **headers},
                json=body,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise NetworkError(f"chat request failed: {e}") from e
