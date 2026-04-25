# 0G Storage — Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/0g-storage-sdk.svg)](https://pypi.org/project/0g-storage-sdk/)

Python SDK for the [0G Storage Network](https://docs.0g.ai/developer-hub/building-on-0g/storage/overview) — a decentralized storage layer that spreads files across sharded nodes and anchors integrity with on-chain merkle proofs.

A direct port of the official TypeScript SDK [`@0glabs/0g-ts-sdk`](https://github.com/0glabs/0g-ts-sdk). Files uploaded with either SDK produce **byte-exact identical merkle roots**.

> 📚 **Full developer documentation:** [og-py.vercel.app](https://og-py.vercel.app/)

## What you get

- **Merkle tree generation** — Keccak256, 256-byte chunks, 256 KB segments — output identical to the TS SDK
- **File upload** — Flow contract submission, parallel segment uploads, automatic shard routing, retry on transient failures
- **File download** — by root hash, with optional proof verification per segment
- **Splitable upload** — for files larger than 4 GB, with batched fragment processing
- **Fragment download** — reassemble multi-fragment files in order
- **KV storage** — append-only key-value streams with version-aware reads, batched writes, and per-key access control
- **Storage node RPC** — 14-method client for direct node interaction (get_status, upload/download segments, shard configs, sector proofs)

## Installation

```bash
pip install 0g-storage-sdk
```

Requires Python 3.8+.

The package name `0g-storage-sdk` isn't a valid Python identifier, so the SDK ships its top-level modules directly:

```python
from core.indexer import Indexer
from core.file import ZgFile
from core.merkle import MerkleTree
from core.kv import KvClient, StreamDataBuilder, Batcher
```

### Dependencies

Auto-installed:

- `pycryptodome` — Keccak256 hashing
- `web3` — blockchain RPC and contract calls
- `eth-account` — transaction signing
- `requests` — HTTP client

## Quickstart — upload & download

```python
from core.indexer import Indexer
from core.file import ZgFile
from eth_account import Account

INDEXER_RPC    = "https://indexer-storage-testnet-turbo.0g.ai"
BLOCKCHAIN_RPC = "https://evmrpc-testnet.0g.ai"
PRIVATE_KEY    = "0xYOUR_PRIVATE_KEY"

indexer = Indexer(INDEXER_RPC)
account = Account.from_key(PRIVATE_KEY)

# Upload
file = ZgFile.from_file_path("./data.txt")
result, err = indexer.upload(
    file,
    BLOCKCHAIN_RPC,
    account,
    {
        "tags": b"\x00",
        "finalityRequired": True,
        "expectedReplica": 1,
        "account": account,
    },
)
file.close()

if err is None:
    print(f"Uploaded: {result['rootHash']}")
    print(f"Tx:       {result['txHash']}")

# Download (wait 3–5 minutes for shard propagation first)
err = indexer.download(result["rootHash"], "./output.txt")
```

## Compute a merkle root locally

No network calls — pure local hashing:

```python
from core.file import ZgFile

file = ZgFile.from_bytes(b"hello, 0G Storage")
tree, err = file.merkle_tree()
print(tree.root_hash())
file.close()
```

## Large files (>4 GB)

```python
from core.uploader import Uploader

# After selecting nodes via indexer.select_nodes(...)
uploader = Uploader(clients, BLOCKCHAIN_RPC, flow)

result, err = uploader.splitable_upload(
    file,
    {
        "account":          account,
        "fragmentSize":     4 * 1024 * 1024 * 1024,   # 4 GB per fragment
        "finalityRequired": True,
    },
)

# result["rootHashes"] is a list — one hash per fragment, in order
```

Download with `Downloader.download_fragments(roots, filename)` — fragments are concatenated in the order you pass them.

## KV storage

```python
from core.kv import Batcher

batcher = Batcher(version=1, clients=clients, flow=flow, provider=BLOCKCHAIN_RPC)

stream_id = "0x" + "11" * 32
batcher.set(stream_id, b"user:42",  b'{"name": "Alice"}')
batcher.set(stream_id, b"user:101", b'{"name": "Bob"}')

result, err = batcher.exec({"account": account})
```

Read back via `KvClient`:

```python
from core.kv import KvClient

kv = KvClient("http://storage-node.example.com:5678")
value = kv.get_value(stream_id, b"user:42")
# value.data is base64-encoded
```

## Generate proofs

```python
proof = tree.proof_at(2)            # proof for the leaf at index 2

err = proof.validate(
    root_hash      = tree.root_hash(),
    content        = b"chunk 3 data",
    position       = 2,
    num_leaf_nodes = len(tree.leaves),
)

if err is None:
    print("Valid proof")
```

## Public API surface

Everything you need is exported at module level:

| Symbol | Purpose |
|--------|---------|
| `Indexer(url)` | Indexer RPC client — `upload`, `download`, `select_nodes`, `get_file_locations` |
| `ZgFile.from_file_path(path)` / `.from_bytes(data)` | File abstraction with merkle tree generation |
| `MerkleTree`, `Proof`, `LeafNode` | Direct merkle tree construction and verification |
| `Uploader`, `Downloader` | Lower-level upload/download with retry options |
| `StorageNode(url)` | Direct RPC to a storage node (14 methods) |
| `KvClient(rpc)` | KV reads — `get_value`, `get_first/last/next/prev`, iterators |
| `StreamDataBuilder(version)` | Build `StreamData` blobs (writes + access control) |
| `Batcher(version, clients, flow, provider)` | High-level batched KV writes |
| `KvIterator` | Cursor-style traversal over a stream |
| `select_nodes`, `check_replica`, `is_valid_config` | Node selection helpers |
| `RetryOpts`, `tx_with_gas_adjustment`, `submit_with_gas_adjustment` | Retry and gas utilities |
| Exceptions: `StorageError`, `UploadError`, `DownloadError`, `MerkleTreeError`, `ContractError`, `RetryableError`, ... | Structured exception hierarchy with `error_code`, `context`, `cause` |

For the full per-class API and worked examples, see the [Storage SDK docs](https://og-py.vercel.app/).

## Network configuration

| Network | Chain ID | Blockchain RPC | Indexer RPC |
|---------|----------|----------------|-------------|
| Mainnet | `16661` | `https://evmrpc.0g.ai` | `https://indexer-storage-turbo.0g.ai` |
| Testnet (Galileo) | `16602` | `https://evmrpc-testnet.0g.ai` | `https://indexer-storage-testnet-turbo.0g.ai` |

Get testnet tokens at [faucet.0g.ai](https://faucet.0g.ai).

### Contract addresses

The SDK reads the Flow contract address from each storage node's `networkIdentity` automatically — direct addressing is rarely needed.

| Contract | Testnet | Mainnet |
|----------|---------|---------|
| Flow | `0x22E03a6A89B950F1c82ec5e74F8eCa321a105296` | `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526` |

## Constants

```python
DEFAULT_CHUNK_SIZE = 256          # bytes per merkle leaf
DEFAULT_SEGMENT_SIZE = 262144     # 256 KB per segment (1024 chunks)
SMALL_FILE_SIZE_THRESHOLD = 256 * 1024
DEFAULT_FRAGMENT_SIZE = 4 * 1024 * 1024 * 1024   # 4 GB
```

## Testing

```bash
cd 0g_py_storage
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## Verifying parity with the TypeScript SDK

```python
from core.file import ZgFile

tree, _ = ZgFile.from_bytes(b"0G Storage parity check").merkle_tree()
print(tree.root_hash())
```

Run the equivalent in the TypeScript SDK — the printed hashes match byte-for-byte.

## Error handling

```python
from utils.error_handler import is_retryable

result, err = indexer.upload(file, BLOCKCHAIN_RPC, account, opts)
if err is not None:
    if is_retryable(err):
        # transient — retry with backoff
        ...
    else:
        raise err
```

For a tour of the full exception hierarchy and `ErrorContext` / `wrap_with_context` helpers, see the [Error Handling docs](https://og-py.vercel.app/storage/error-handling).

## Contributing

Contributions should preserve TypeScript SDK parity. Each PR should:

1. Match the TS SDK behavior — verify outputs match byte-for-byte
2. Include tests for new functionality
3. Update the README and docs as needed
4. Reference TS SDK line numbers in code comments where applicable

## License

MIT

## Links

- 📚 **Documentation:** [og-py.vercel.app](https://og-py.vercel.app/)
- 🌐 0G Labs: [0g.ai](https://0g.ai)
- 📖 Official docs: [docs.0g.ai](https://docs.0g.ai)
- 📦 TypeScript SDK: [@0glabs/0g-ts-sdk](https://github.com/0glabs/0g-ts-sdk)
- 🚰 Testnet faucet: [faucet.0g.ai](https://faucet.0g.ai)
- 🔍 Block explorer: [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai)
