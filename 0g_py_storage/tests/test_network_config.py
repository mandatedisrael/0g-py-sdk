"""
Typed network config — TS-parity tests.

Verifies the Python ``get_network`` / ``get_config`` surface matches
``.cache/storage_ts_starter_kit/src/config.ts`` byte-for-byte where it
matters (indexer URLs per network/mode, chain IDs, RPC URLs, validation
errors).
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    INDEXER_URLS,
    NETWORK_PRESETS,
    AppConfig,
    ConfigOverrides,
    DecryptionConfig,
    EncryptionConfig,
    NetworkConfig,
    get_config,
    get_network,
)


# ── INDEXER_URLS / NETWORK_PRESETS — exact TS values ───────────────────────


def test_indexer_urls_match_ts():
    assert INDEXER_URLS == {
        "testnet": {
            "turbo": "https://indexer-storage-testnet-turbo.0g.ai",
            "standard": "https://indexer-storage-testnet-standard.0g.ai",
        },
        "mainnet": {
            "turbo": "https://indexer-storage-turbo.0g.ai",
            "standard": "https://indexer-storage.0g.ai",
        },
    }


def test_network_presets_match_ts():
    # testnet
    p = NETWORK_PRESETS["testnet"]
    assert p["rpc_url"] == "https://evmrpc-testnet.0g.ai"
    assert p["chain_id"] == 16602
    assert p["explorer_url"] == "https://chainscan-galileo.0g.ai"
    # mainnet
    p = NETWORK_PRESETS["mainnet"]
    assert p["rpc_url"] == "https://evmrpc.0g.ai"
    assert p["chain_id"] == 16661
    assert p["explorer_url"] == "https://chainscan.0g.ai"


# ── get_network ─────────────────────────────────────────────────────────────


def test_get_network_defaults_to_testnet_turbo(monkeypatch):
    monkeypatch.delenv("NETWORK", raising=False)
    monkeypatch.delenv("STORAGE_MODE", raising=False)
    cfg = get_network()
    assert cfg.name == "testnet"
    assert cfg.mode == "turbo"
    assert cfg.indexer_rpc == "https://indexer-storage-testnet-turbo.0g.ai"
    assert cfg.chain_id == 16602


def test_get_network_explicit_mainnet_standard():
    cfg = get_network("mainnet", "standard")
    assert cfg.name == "mainnet"
    assert cfg.mode == "standard"
    assert cfg.indexer_rpc == "https://indexer-storage.0g.ai"
    assert cfg.chain_id == 16661


def test_get_network_env_fallback(monkeypatch):
    monkeypatch.setenv("NETWORK", "mainnet")
    monkeypatch.setenv("STORAGE_MODE", "standard")
    cfg = get_network()
    assert cfg.name == "mainnet"
    assert cfg.mode == "standard"


def test_get_network_explicit_args_beat_env(monkeypatch):
    monkeypatch.setenv("NETWORK", "mainnet")
    monkeypatch.setenv("STORAGE_MODE", "standard")
    cfg = get_network("testnet", "turbo")
    assert cfg.name == "testnet"
    assert cfg.mode == "turbo"


def test_get_network_rejects_bad_network():
    with pytest.raises(ValueError, match="Invalid network"):
        get_network("hardhat", "turbo")


def test_get_network_rejects_bad_mode():
    with pytest.raises(ValueError, match="Invalid storage mode"):
        get_network("testnet", "express")


# ── EncryptionConfig validation ────────────────────────────────────────────


def test_encryption_config_aes256_requires_key():
    with pytest.raises(ValueError, match="requires 'key'"):
        EncryptionConfig(type="aes256")


def test_encryption_config_aes256_validates_key_length():
    with pytest.raises(ValueError, match="32 bytes"):
        EncryptionConfig(type="aes256", key=b"\x00" * 31)


def test_encryption_config_ecies_requires_recipient():
    with pytest.raises(ValueError, match="requires 'recipient_pub_key'"):
        EncryptionConfig(type="ecies")


def test_encryption_config_rejects_unknown_type():
    with pytest.raises(ValueError, match="unsupported"):
        EncryptionConfig(type="rot13", key=b"\x00" * 32)


def test_encryption_config_to_upload_opt_aes256():
    key = b"\x42" * 32
    cfg = EncryptionConfig(type="aes256", key=key)
    assert cfg.to_upload_opt() == {"type": "aes256", "key": key}


def test_encryption_config_to_upload_opt_ecies():
    pub = "0x" + "01" * 33
    cfg = EncryptionConfig(type="ecies", recipient_pub_key=pub)
    assert cfg.to_upload_opt() == {"type": "ecies", "recipient_pub_key": pub}


# ── get_config end-to-end ──────────────────────────────────────────────────


def test_get_config_assembles_app_config(monkeypatch):
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("GAS_PRICE", raising=False)
    monkeypatch.delenv("MAX_RETRIES", raising=False)
    cfg = get_config(ConfigOverrides(network="mainnet", mode="standard"))
    assert isinstance(cfg, AppConfig)
    assert cfg.network.name == "mainnet"
    assert cfg.network.mode == "standard"
    assert cfg.private_key is None
    assert cfg.gas_price is None


def test_get_config_picks_up_env_private_key(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "ab" * 32)
    cfg = get_config()
    assert cfg.private_key == "0x" + "ab" * 32


def test_get_config_override_beats_env(monkeypatch):
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "ab" * 32)
    cfg = get_config(ConfigOverrides(private_key="0xdeadbeef"))
    assert cfg.private_key == "0xdeadbeef"


def test_get_config_parses_int_env_vars(monkeypatch):
    monkeypatch.setenv("GAS_PRICE", "1000000")
    monkeypatch.setenv("MAX_RETRIES", "5")
    cfg = get_config()
    assert cfg.gas_price == 1000000
    assert cfg.max_retries == 5


def test_get_config_ignores_malformed_int_env_vars(monkeypatch):
    monkeypatch.setenv("GAS_PRICE", "definitely-not-a-number")
    cfg = get_config()
    assert cfg.gas_price is None
