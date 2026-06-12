"""Authenticated broker parity tests for multi-model inference."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.models import ServiceMetadata
from zerog_py_sdk.read_only import ProviderModels


PROVIDER = "0x00000000000000000000000000000000000000aa"


def _service() -> ServiceMetadata:
    return ServiceMetadata(
        provider=PROVIDER,
        service_type="chatbot",
        url="https://provider.example.com",
        input_price=1,
        output_price=2,
        updated_at=0,
        model="default-model",
        verifiability="",
        additional_info='{"MultiModel":true}',
    )


def _manager() -> InferenceManager:
    manager = object.__new__(InferenceManager)
    manager.web3 = MagicMock()
    manager.web3.eth.chain_id = 16602
    manager.get_service = MagicMock(return_value=_service())
    return manager


def test_get_service_metadata_uses_on_chain_default_model():
    manager = _manager()

    metadata = manager.get_service_metadata(PROVIDER)

    assert metadata == {
        "endpoint": "https://provider.example.com/v1/proxy",
        "model": "default-model",
    }


def test_get_service_metadata_forwards_requested_model_without_validation():
    manager = _manager()

    metadata = manager.get_service_metadata(PROVIDER, "selected-model")

    assert metadata == {
        "endpoint": "https://provider.example.com/v1/proxy",
        "model": "selected-model",
    }


def test_get_provider_models_uses_shared_typescript_parity_path():
    manager = _manager()
    expected = ProviderModels(
        provider=PROVIDER,
        url="https://provider.example.com",
        multi_model=True,
        default_model="default-model",
        models=[],
    )

    with patch(
        "zerog_py_sdk.inference._fetch_provider_models",
        return_value=expected,
    ) as fetch:
        result = manager.get_provider_models(PROVIDER)

    assert result is expected
    fetch.assert_called_once_with(
        manager.get_service.return_value,
        "https://compute-status-testnet.0g.ai",
    )
