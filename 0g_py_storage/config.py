"""
Configuration and constants for 0G Storage SDK.

Constants directly ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/constant.js
"""

try:
    from .utils.crypto import keccak256_hash
except ImportError:
    from utils.crypto import keccak256_hash

# Storage constants (from TS SDK)
DEFAULT_CHUNK_SIZE = 256  # bytes
DEFAULT_SEGMENT_MAX_CHUNKS = 1024
DEFAULT_SEGMENT_SIZE = DEFAULT_CHUNK_SIZE * DEFAULT_SEGMENT_MAX_CHUNKS  # 262,144 bytes

# Empty chunk and its hash
EMPTY_CHUNK = bytes(DEFAULT_CHUNK_SIZE)
EMPTY_CHUNK_HASH = keccak256_hash(EMPTY_CHUNK)

# File size threshold
SMALL_FILE_SIZE_THRESHOLD = 256 * 1024  # 256 KB

# Timeout
TIMEOUT_MS = 3000000  # 3000 seconds (from TS SDK)

# Zero hash
ZERO_HASH = '0x0000000000000000000000000000000000000000000000000000000000000000'

# Default batch size for fragment uploads
DEFAULT_BATCH_SIZE = 10

# Default fragment size for splitable uploads (4GB)
DEFAULT_FRAGMENT_SIZE = 4 * 1024 * 1024 * 1024  # 4GB

# Network configurations
# Official network details from https://docs.0g.ai
NETWORKS = {
    "testnet": {
        "name": "0G-Galileo-Testnet",
        "rpc_url": "https://evmrpc-testnet.0g.ai",
        "indexer_url": "https://indexer-storage-testnet-turbo.0g.ai",
        "chain_id": 16602,  # Official Galileo testnet chain ID
        "explorer": "https://chainscan-galileo.0g.ai",
        "faucet": "https://faucet.0g.ai"
    },
    "mainnet": {
        "name": "0G Mainnet",
        "rpc_url": "https://evmrpc.0g.ai",
        "indexer_url": "https://indexer-storage-turbo.0g.ai",
        "chain_id": 16661,  # Official mainnet chain ID
        "explorer": "https://chainscan.0g.ai"
    }
}

# Additional Python-specific configs
MIN_REPLICAS = 1
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Typed network configuration — TS-parity surface
#
# Mirrors `.cache/storage_ts_starter_kit/src/config.ts` field-for-field:
# `NetworkName`, `StorageMode`, `NetworkConfig`, `EncryptionConfig`,
# `DecryptionConfig`, `AppConfig`, `ConfigOverrides`, `INDEXER_URLS`,
# `get_network`, `get_config`. The existing flat ``NETWORKS`` dict above
# is preserved for backward compatibility with code that already uses it.
# ---------------------------------------------------------------------------

import os
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, Union

NetworkName = Literal["testnet", "mainnet"]
StorageMode = Literal["turbo", "standard"]


# Indexer URLs per (network, mode). Source: TS starter kit config.ts:40-48.
INDEXER_URLS: Dict[str, Dict[str, str]] = {
    "testnet": {
        "turbo": "https://indexer-storage-testnet-turbo.0g.ai",
        "standard": "https://indexer-storage-testnet-standard.0g.ai",
    },
    "mainnet": {
        "turbo": "https://indexer-storage-turbo.0g.ai",
        "standard": "https://indexer-storage.0g.ai",
    },
}


@dataclass
class NetworkConfig:
    """Resolved network configuration for a given (name, mode) combination."""

    name: str  # NetworkName
    mode: str  # StorageMode
    rpc_url: str
    indexer_rpc: str
    chain_id: int
    explorer_url: str


# Network presets — same shape as TS ``NETWORKS`` but without mode/indexer
# (those are filled in by ``get_network``). Source: starter kit config.ts:51-64.
NETWORK_PRESETS: Dict[str, Dict[str, Union[str, int]]] = {
    "testnet": {
        "name": "testnet",
        "rpc_url": "https://evmrpc-testnet.0g.ai",
        "chain_id": 16602,
        "explorer_url": "https://chainscan-galileo.0g.ai",
    },
    "mainnet": {
        "name": "mainnet",
        "rpc_url": "https://evmrpc.0g.ai",
        "chain_id": 16661,
        "explorer_url": "https://chainscan.0g.ai",
    },
}


@dataclass
class EncryptionConfig:
    """Tagged-union shape: either symmetric AES-256 or ECIES."""

    type: str  # 'aes256' | 'ecies'
    key: Optional[bytes] = None  # AES-256: 32 bytes
    recipient_pub_key: Optional[Union[bytes, str]] = None  # ECIES: compressed pub or hex

    def __post_init__(self) -> None:
        if self.type == "aes256":
            if self.key is None:
                raise ValueError("EncryptionConfig type=aes256 requires 'key'")
            if len(self.key) != 32:
                raise ValueError(
                    f"aes256 key must be 32 bytes, got {len(self.key)}"
                )
        elif self.type == "ecies":
            if self.recipient_pub_key is None:
                raise ValueError(
                    "EncryptionConfig type=ecies requires 'recipient_pub_key'"
                )
        else:
            raise ValueError(f"unsupported EncryptionConfig type: {self.type!r}")

    def to_upload_opt(self) -> Dict[str, object]:
        """Render as the ``opts['encryption']`` shape ``Uploader`` expects."""
        if self.type == "aes256":
            return {"type": "aes256", "key": self.key}
        return {"type": "ecies", "recipient_pub_key": self.recipient_pub_key}


@dataclass
class DecryptionConfig:
    """Optional materials for ``Downloader`` / ``Indexer.download`` decryption."""

    symmetric_key: Optional[Union[bytes, str]] = None
    private_key: Optional[Union[bytes, str]] = None


@dataclass
class AppConfig:
    """Top-level config bundle, mirrors TS ``AppConfig``."""

    network: NetworkConfig
    private_key: Optional[str] = None
    gas_price: Optional[int] = None
    gas_limit: Optional[int] = None
    max_retries: Optional[int] = None
    max_gas_price: Optional[int] = None
    encryption: Optional[EncryptionConfig] = None
    decryption: Optional[DecryptionConfig] = None


@dataclass
class ConfigOverrides:
    """Optional overrides accepted by ``get_config``."""

    network: Optional[str] = None
    mode: Optional[str] = None
    private_key: Optional[str] = None
    encryption: Optional[EncryptionConfig] = None
    decryption: Optional[DecryptionConfig] = None


def get_network(
    name: Optional[str] = None, mode: Optional[str] = None
) -> NetworkConfig:
    """
    Resolve a ``NetworkConfig`` from (name, mode) or environment defaults.

    Mirrors TS ``getNetwork(name?, mode?)``. Falls back to ``NETWORK`` /
    ``STORAGE_MODE`` env vars, then to ``("testnet", "turbo")``. Raises
    ``ValueError`` for any unknown network or mode.
    """
    network_name = name or os.environ.get("NETWORK") or "testnet"
    storage_mode = mode or os.environ.get("STORAGE_MODE") or "turbo"

    if network_name not in NETWORK_PRESETS:
        raise ValueError(
            f'Invalid network: "{network_name}". Use "testnet" or "mainnet".'
        )
    if storage_mode not in ("turbo", "standard"):
        raise ValueError(
            f'Invalid storage mode: "{storage_mode}". Use "turbo" or "standard".'
        )

    base = NETWORK_PRESETS[network_name]
    return NetworkConfig(
        name=str(base["name"]),
        mode=storage_mode,
        rpc_url=str(base["rpc_url"]),
        indexer_rpc=INDEXER_URLS[network_name][storage_mode],
        chain_id=int(base["chain_id"]),
        explorer_url=str(base["explorer_url"]),
    )


def get_config(overrides: Optional[ConfigOverrides] = None) -> AppConfig:
    """
    Build an ``AppConfig`` from optional overrides + environment.

    Mirrors TS ``getConfig(overrides?)``. ``PRIVATE_KEY``, ``GAS_PRICE``,
    ``GAS_LIMIT``, ``MAX_RETRIES`` and ``MAX_GAS_PRICE`` env vars are
    honored when no override is supplied.
    """
    ov = overrides or ConfigOverrides()
    network = get_network(ov.network, ov.mode)

    def _int_env(name: str) -> Optional[int]:
        v = os.environ.get(name)
        if v is None:
            return None
        try:
            return int(v)
        except ValueError:
            return None

    private_key = ov.private_key or os.environ.get("PRIVATE_KEY") or None

    return AppConfig(
        network=network,
        private_key=private_key,
        gas_price=_int_env("GAS_PRICE"),
        gas_limit=_int_env("GAS_LIMIT"),
        max_retries=_int_env("MAX_RETRIES"),
        max_gas_price=_int_env("MAX_GAS_PRICE"),
        encryption=ov.encryption,
        decryption=ov.decryption,
    )
