import hashlib
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zerog_py_sdk.exceptions import ConfigurationError, ContractError
from zerog_py_sdk.fine_tuning.binaries import (
    STORAGE_CLIENT,
    TOKEN_COUNTER,
    BinaryConfig,
    BinaryResolver,
)
from zerog_py_sdk.fine_tuning.broker.dataset import DatasetProcessor
from zerog_py_sdk.fine_tuning.constants import (
    TOKEN_COUNTER_FILE_HASH,
    TOKEN_COUNTER_MERKLE_ROOT,
)
from zerog_py_sdk.fine_tuning.storage import StorageClient


@pytest.fixture(autouse=True)
def _clear_binary_environment(monkeypatch):
    monkeypatch.delenv("ZG_STORAGE_CLIENT_PATH", raising=False)
    monkeypatch.delenv("ZG_TOKEN_COUNTER_PATH", raising=False)
    monkeypatch.delenv("ZG_BINARY_CACHE_DIR", raising=False)


def _executable(path: Path, content: bytes = b"binary") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(0o700)
    return path


def test_explicit_path_wins_over_environment_and_cache(tmp_path, monkeypatch):
    explicit = _executable(tmp_path / "explicit")
    environment = _executable(tmp_path / "environment")
    cache = tmp_path / "cache"
    _executable(cache / STORAGE_CLIENT)
    monkeypatch.setenv("ZG_STORAGE_CLIENT_PATH", str(environment))
    resolver = BinaryResolver(
        BinaryConfig(
            storage_client_path=str(explicit),
            cache_dir=str(cache),
        )
    )

    assert resolver.resolve(STORAGE_CLIENT) == str(explicit.resolve())


def test_invalid_explicit_path_does_not_silently_fall_back(
    tmp_path, monkeypatch
):
    environment = _executable(tmp_path / "environment")
    monkeypatch.setenv("ZG_STORAGE_CLIENT_PATH", str(environment))
    resolver = BinaryResolver(
        BinaryConfig(storage_client_path=str(tmp_path / "missing"))
    )

    with pytest.raises(ConfigurationError, match="not a regular file"):
        resolver.resolve(STORAGE_CLIENT)


def test_environment_path_wins_over_user_cache(tmp_path, monkeypatch):
    environment = _executable(tmp_path / "environment")
    cache = tmp_path / "cache"
    _executable(cache / TOKEN_COUNTER)
    monkeypatch.setenv("ZG_TOKEN_COUNTER_PATH", str(environment))
    resolver = BinaryResolver(BinaryConfig(cache_dir=str(cache)))

    assert resolver.resolve(TOKEN_COUNTER) == str(environment.resolve())
    assert resolver.has_override(TOKEN_COUNTER) is True


def test_verified_install_is_atomic_and_executable(tmp_path):
    source = tmp_path / "download"
    source.write_bytes(b"verified tool")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    resolver = BinaryResolver(
        BinaryConfig(cache_dir=str(tmp_path / "cache"))
    )

    installed = Path(
        resolver.install_verified(TOKEN_COUNTER, str(source), expected)
    )

    assert installed.read_bytes() == b"verified tool"
    assert os.access(str(installed), os.X_OK)
    assert list(installed.parent.glob(".*.part")) == []


def test_hash_failure_preserves_existing_cached_binary(tmp_path):
    cache = tmp_path / "cache"
    existing = _executable(cache / TOKEN_COUNTER, b"existing")
    source = tmp_path / "download"
    source.write_bytes(b"tampered")
    resolver = BinaryResolver(BinaryConfig(cache_dir=str(cache)))

    with pytest.raises(ConfigurationError, match="SHA-256"):
        resolver.install_verified(
            TOKEN_COUNTER,
            str(source),
            hashlib.sha256(b"expected").hexdigest(),
        )

    assert existing.read_bytes() == b"existing"


def _storage_client(binary_path="/resolved/0g-storage-client"):
    resolver = MagicMock()
    resolver.resolve.return_value = binary_path
    return StorageClient(resolver), resolver


def test_storage_upload_uses_official_flags_and_parses_stderr(tmp_path):
    data = tmp_path / "dataset.jsonl"
    data.write_text('{"text":"hello"}\n')
    client, resolver = _storage_client()
    completed = subprocess.CompletedProcess(
        [],
        0,
        stdout="",
        stderr="file uploaded, root = 0xabc123",
    )

    with patch(
        "zerog_py_sdk.fine_tuning.storage.subprocess.run",
        return_value=completed,
    ) as run:
        root = client.upload(
            private_key="0xsecret",
            data_path=str(data),
            rpc_url="https://rpc.example",
            indexer_url="https://indexer.example",
            gas_price=7,
            max_gas_price=9,
        )

    assert root == "0xabc123"
    command = run.call_args.args[0]
    assert command[0] == "/resolved/0g-storage-client"
    assert "--skip-tx=false" in command
    assert "--log-level=debug" in command
    assert command[command.index("--gas-price") + 1] == "7"
    assert command[command.index("--max-gas-price") + 1] == "9"
    assert run.call_args.kwargs["timeout"] == 600
    assert run.call_args.kwargs["check"] is False
    resolver.resolve.assert_called_once_with(STORAGE_CLIENT)


def test_failed_storage_download_preserves_destination(tmp_path):
    destination = tmp_path / "dataset.bin"
    destination.write_bytes(b"existing")
    client, _ = _storage_client()

    def fail_after_partial_write(command, **_kwargs):
        output = Path(command[command.index("--file") + 1])
        output.write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, "", "failed")

    with patch(
        "zerog_py_sdk.fine_tuning.storage.subprocess.run",
        side_effect=fail_after_partial_write,
    ):
        with pytest.raises(ContractError, match="exited with code 1"):
            client.download(
                str(destination),
                "0xroot",
                "https://indexer.example",
            )

    assert destination.read_bytes() == b"existing"
    assert list(tmp_path.glob(".dataset.bin.*.part")) == []


def test_successful_storage_download_replaces_destination_atomically(tmp_path):
    destination = tmp_path / "dataset.bin"
    destination.write_bytes(b"existing")
    client, _ = _storage_client()

    def write_download(command, **_kwargs):
        output = Path(command[command.index("--file") + 1])
        output.write_bytes(b"downloaded")
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch(
        "zerog_py_sdk.fine_tuning.storage.subprocess.run",
        side_effect=write_download,
    ):
        client.download(
            str(destination),
            "0xroot",
            "https://indexer.example",
        )

    assert destination.read_bytes() == b"downloaded"
    assert list(tmp_path.glob(".dataset.bin.*.part")) == []


def test_missing_token_counter_is_downloaded_and_verified():
    resolver = MagicMock()
    resolver.resolve.side_effect = ConfigurationError("missing")
    resolver.has_override.return_value = False
    resolver.install_verified.return_value = "/cache/token_counter"
    storage = MagicMock()
    storage.binary_resolver = resolver
    contract = MagicMock()
    contract.get_chain_id.return_value = 16602
    processor = DatasetProcessor(contract, MagicMock(), storage)

    assert processor._resolve_token_counter() == "/cache/token_counter"

    download = storage.download.call_args.kwargs
    assert download["data_root"] == TOKEN_COUNTER_MERKLE_ROOT
    assert download["operation"] == "downloadTokenCounter"
    install = resolver.install_verified.call_args.args
    assert install[0] == TOKEN_COUNTER
    assert install[2] == TOKEN_COUNTER_FILE_HASH


def test_invalid_token_counter_override_never_triggers_download():
    resolver = MagicMock()
    resolver.resolve.side_effect = ConfigurationError("invalid override")
    resolver.has_override.return_value = True
    storage = MagicMock()
    storage.binary_resolver = resolver
    processor = DatasetProcessor(MagicMock(), MagicMock(), storage)

    with pytest.raises(ContractError, match="invalid override"):
        processor._resolve_token_counter()

    storage.download.assert_not_called()
