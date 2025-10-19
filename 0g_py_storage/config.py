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
