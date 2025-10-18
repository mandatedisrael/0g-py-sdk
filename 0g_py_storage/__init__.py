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
"""

__version__ = "0.1.0"
