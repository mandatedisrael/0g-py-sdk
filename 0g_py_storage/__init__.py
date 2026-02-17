"""
0G Storage Python SDK

Official Python SDK for 0G Storage - decentralized storage with merkle proofs.
Ported from @0glabs/0g-ts-sdk

Features:
- File merkle tree generation (cryptographically verified)
- File upload to 0G Storage network
- File download with proof verification
- Smart contract integration (Flow contract)
- Sharded node selection
- Automatic retry logic
- KV Storage support

Quick Start:
    from core.file import ZgFile
    from core.indexer import Indexer

    # Generate merkle tree
    file = ZgFile.from_file_path("./data.txt")
    tree, err = file.merkle_tree()
    print(f"Root Hash: {tree.root_hash()}")

    # Upload file
    indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")
    result, err = indexer.upload(file, blockchain_rpc, account, opts)
    
KV Storage:
    from core.kv import KvClient, Batcher, StreamDataBuilder
    from core.storage_kv import StorageKv
    
    # Create KV client
    kv = StorageKv("http://node-url")
    client = KvClient(indexer, kv)
"""

__version__ = "0.3.0"

# Core exports
from core import (
    # Merkle Tree
    LeafNode,
    MerkleTree,
    Proof,
    ProofErrors,
    # File handling
    ZgFile,
    AbstractFile,
    # Storage nodes
    StorageNode,
    StorageKv,
    # Indexer
    Indexer,
    # Transfer
    Uploader,
    Downloader,
    # Node selection
    select_nodes,
    check_replica,
    is_valid_config,
    # KV Storage
    KvClient,
    Batcher,
    StreamDataBuilder,
    KvIterator,
    AccessControlType,
    StreamRead,
    StreamWrite,
    AccessControl,
    StreamData,
    MAX_SET_SIZE,
    MAX_KEY_SIZE,
    MAX_QUERY_SIZE,
    STREAM_DOMAIN,
)

# Utility exports
from utils import (
    RetryOpts,
    tx_with_gas_adjustment,
    submit_with_gas_adjustment,
)

__all__ = [
    # Version
    "__version__",
    # Merkle Tree
    "LeafNode",
    "MerkleTree",
    "Proof",
    "ProofErrors",
    # File handling
    "ZgFile",
    "AbstractFile",
    # Storage nodes
    "StorageNode",
    "StorageKv",
    # Indexer
    "Indexer",
    # Transfer
    "Uploader",
    "Downloader",
    # Node selection
    "select_nodes",
    "check_replica",
    "is_valid_config",
    # KV Storage
    "KvClient",
    "Batcher",
    "StreamDataBuilder",
    "KvIterator",
    "AccessControlType",
    "StreamRead",
    "StreamWrite",
    "AccessControl",
    "StreamData",
    "MAX_SET_SIZE",
    "MAX_KEY_SIZE",
    "MAX_QUERY_SIZE",
    "STREAM_DOMAIN",
    # Utilities
    "RetryOpts",
    "tx_with_gas_adjustment",
    "submit_with_gas_adjustment",
]
