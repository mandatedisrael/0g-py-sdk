import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.exceptions import ContractError
from zerog_py_sdk.fine_tuning.broker.broker import FineTuningBroker
from zerog_py_sdk.fine_tuning.broker.dataset import DatasetProcessor
from zerog_py_sdk.fine_tuning.broker.model import ModelProcessor
from zerog_py_sdk.fine_tuning.contract.types import (
    CustomizedModel,
    Deliverable,
    TdxQuoteResponse,
)
from zerog_py_sdk.fine_tuning.provider import provider as provider_mod
from zerog_py_sdk.fine_tuning.provider.provider import FineTuningProvider

PROVIDER = "0xprovider"
TASK_ID = "task-abc-123"
ROOT = bytes.fromhex("12" * 32)


def deliverable(*, acknowledged=False, root=ROOT):
    return Deliverable(
        id=TASK_ID,
        model_root_hash=root,
        encrypted_secret=b"",
        acknowledged=acknowledged,
        timestamp=0,
        settled=False,
    )


class FakeContract:
    def __init__(self, item=None):
        self.item = item or deliverable()
        self.ack_calls = []

    def get_deliverable(self, provider_address, task_id):
        assert provider_address == PROVIDER
        assert task_id == TASK_ID
        return self.item

    def acknowledge_deliverable(self, provider_address, task_id, gas_price=None):
        self.ack_calls.append((provider_address, task_id, gas_price))
        return {"status": "acknowledged"}

    def get_chain_id(self):
        return 16602


class FakeProvider:
    def __init__(self):
        self.tee_calls = []

    def download_lora_from_tee(
        self,
        provider_address,
        task_id,
        output_path,
        idle_timeout_ms=None,
        max_retries=None,
    ):
        self.tee_calls.append(
            (provider_address, task_id, output_path, idle_timeout_ms, max_retries)
        )


def test_acknowledge_model_auto_uses_storage_then_acknowledges(tmp_path):
    contract = FakeContract()
    provider = FakeProvider()
    processor = ModelProcessor(contract, provider)

    with patch.object(processor, "_download_from_0g_storage") as storage, patch.object(
        processor, "_verify_model_hash"
    ) as verify:
        result = processor.acknowledge_model(
            PROVIDER, TASK_ID, str(tmp_path), gas_price=7
        )

    assert result == {"status": "acknowledged"}
    storage.assert_called_once()
    assert provider.tee_calls == []
    verify.assert_not_called()
    assert contract.ack_calls == [(PROVIDER, TASK_ID, 7)]


def test_acknowledge_model_auto_falls_back_to_tee(tmp_path):
    contract = FakeContract()
    provider = FakeProvider()
    processor = ModelProcessor(contract, provider)

    with patch.object(
        processor,
        "_download_from_0g_storage",
        side_effect=ContractError("downloadModelFrom0GStorage", "missing"),
    ), patch.object(processor, "_verify_model_hash") as verify:
        result = processor.acknowledge_model(
            PROVIDER,
            TASK_ID,
            str(tmp_path / "model.bin"),
            download_method="auto",
            tee_idle_timeout_ms=12_000,
            tee_max_retries=4,
        )

    assert result == {"status": "acknowledged"}
    assert provider.tee_calls == [
        (PROVIDER, TASK_ID, str(tmp_path / "model.bin"), 12_000, 4)
    ]
    verify.assert_called_once()
    assert contract.ack_calls == [(PROVIDER, TASK_ID, None)]


def test_acknowledge_model_storage_method_does_not_fallback(tmp_path):
    contract = FakeContract()
    provider = FakeProvider()
    processor = ModelProcessor(contract, provider)

    with patch.object(
        processor,
        "_download_from_0g_storage",
        side_effect=ContractError("downloadModelFrom0GStorage", "missing"),
    ):
        with pytest.raises(ContractError):
            processor.acknowledge_model(
                PROVIDER,
                TASK_ID,
                str(tmp_path / "model.bin"),
                download_method="0g-storage",
            )

    assert provider.tee_calls == []
    assert contract.ack_calls == []


def test_acknowledge_deliverable_is_noop_when_already_acknowledged():
    contract = FakeContract(deliverable(acknowledged=True))
    processor = ModelProcessor(contract, FakeProvider())

    assert processor.acknowledge_deliverable(PROVIDER, TASK_ID) == {
        "status": "already_acknowledged"
    }
    assert contract.ack_calls == []


class FakeAccount:
    address = "0xuser"

    def sign_message(self, _message):
        return SimpleNamespace(signature=b"\xab" * 65)


class FakeProviderContract:
    account = FakeAccount()

    def get_service(self, provider_address):
        assert provider_address == PROVIDER
        return SimpleNamespace(url="https://ft.example.com")


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield b"model"


def test_download_lora_from_tee_retries_and_writes_inside_directory(
    tmp_path, monkeypatch
):
    provider = FineTuningProvider(FakeProviderContract(), FakeAccount())
    monkeypatch.setattr(provider_mod.time, "sleep", lambda *_: None)

    calls = [
        requests.ConnectionError("temporary network failure"),
        FakeResponse(),
    ]

    def fake_post(*_args, **_kwargs):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch.object(provider_mod.requests, "post", side_effect=fake_post) as post:
        provider.download_lora_from_tee(
            PROVIDER,
            TASK_ID,
            str(tmp_path),
            idle_timeout_ms=1_000,
            max_retries=1,
        )

    output = tmp_path / f"lora_model_{TASK_ID}.zip"
    assert output.read_bytes() == b"model"
    assert post.call_count == 2
    assert post.call_args.kwargs["timeout"] == (30, 1)


def test_download_model_usage_writes_module_zip_inside_directory(tmp_path):
    provider = FineTuningProvider(FakeProviderContract(), FakeAccount())
    destination = tmp_path / "custom-a.zip"
    destination.write_bytes(b"stale")

    with patch.object(
        provider_mod.requests, "get", return_value=FakeResponse()
    ) as get:
        provider.download_model_usage(
            PROVIDER, "custom-a", str(tmp_path)
        )

    assert destination.read_bytes() == b"model"
    get.assert_called_once_with(
        "https://ft.example.com/v1/model/desc/custom-a",
        timeout=provider_mod.DOWNLOAD_TIMEOUT,
        stream=True,
    )


def test_upload_dataset_to_tee_honors_timeout_override(tmp_path):
    provider = FineTuningProvider(FakeProviderContract(), FakeAccount())
    dataset = tmp_path / "train.jsonl"
    dataset.write_text('{"messages":[]}\n')
    response = MagicMock()
    response.json.return_value = {"datasetHash": "0xhash", "message": "ok"}

    with patch.object(
        provider_mod.requests, "post", return_value=response
    ) as post:
        result = provider.upload_dataset_to_tee(
            PROVIDER,
            str(dataset),
            max_file_size_mb=1,
            timeout_ms=125_000,
        )

    assert result == {"datasetHash": "0xhash", "message": "ok"}
    assert post.call_args.kwargs["timeout"] == 125
    assert post.call_args.kwargs["files"]["file"].name == str(dataset)


def test_upload_dataset_to_tee_rejects_oversized_file(tmp_path):
    provider = FineTuningProvider(FakeProviderContract(), FakeAccount())
    dataset = tmp_path / "train.jsonl"
    dataset.write_bytes(b"x")

    with patch.object(provider_mod.requests, "post") as post:
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            provider.upload_dataset_to_tee(
                PROVIDER,
                str(dataset),
                max_file_size_mb=0,
            )

    post.assert_not_called()


def test_dataset_upload_options_flow_through_processor_and_broker():
    provider = MagicMock()
    processor = DatasetProcessor(MagicMock(), provider)
    provider.upload_dataset_to_tee.return_value = {"datasetHash": "0xhash"}

    result = processor.upload_dataset_to_tee(
        PROVIDER,
        "/tmp/train.jsonl",
        max_file_size_mb=25,
        timeout_ms=180_000,
    )

    assert result == {"datasetHash": "0xhash"}
    provider.upload_dataset_to_tee.assert_called_once_with(
        PROVIDER,
        "/tmp/train.jsonl",
        max_file_size_mb=25,
        timeout_ms=180_000,
    )

    broker = object.__new__(FineTuningBroker)
    broker._dataset = MagicMock()
    broker._dataset.upload_dataset_to_tee.return_value = result
    assert broker.upload_dataset_to_tee(
        PROVIDER,
        "/tmp/train.jsonl",
        max_file_size_mb=25,
        timeout_ms=180_000,
    ) == result
    broker._dataset.upload_dataset_to_tee.assert_called_once_with(
        PROVIDER,
        "/tmp/train.jsonl",
        max_file_size_mb=25,
        timeout_ms=180_000,
    )


def test_fine_tuning_broker_exposes_provider_helpers():
    broker = object.__new__(FineTuningBroker)
    broker._provider = MagicMock()
    quote = TdxQuoteResponse(raw_report="{}", signing_address="0xsigner")
    model = CustomizedModel(name="custom-a", hash="0xhash")

    broker._provider.get_provider_url.return_value = "https://ft.example.com"
    broker._provider.get_quote.return_value = quote
    broker._provider.get_pending_task_counter.return_value = 3
    broker._provider.get_customized_models.return_value = [model]
    broker._provider.get_customized_model.return_value = model

    assert broker.get_provider_url(PROVIDER) == "https://ft.example.com"
    assert broker.get_quote(PROVIDER) is quote
    assert broker.get_pending_task_counter(PROVIDER) == 3
    assert broker.get_customized_models(PROVIDER) == [model]
    assert broker.get_customized_model(PROVIDER, "custom-a") is model

    broker.download_model_usage(PROVIDER, "custom-a", "/tmp/model.zip")

    broker._provider.get_provider_url.assert_called_once_with(PROVIDER)
    broker._provider.get_quote.assert_called_once_with(PROVIDER)
    broker._provider.get_pending_task_counter.assert_called_once_with(PROVIDER)
    broker._provider.get_customized_models.assert_called_once_with(PROVIDER)
    broker._provider.get_customized_model.assert_called_once_with(
        PROVIDER, "custom-a"
    )
    broker._provider.download_model_usage.assert_called_once_with(
        PROVIDER, "custom-a", "/tmp/model.zip"
    )
