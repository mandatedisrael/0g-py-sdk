# 0G Labs Python SDKs

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen.svg)]()

Official Python SDKs for [0G Labs](https://0g.ai) — the modular AI chain. This repository contains two complementary SDKs:

| Package | PyPI | Description |
|---------|------|-------------|
| [`0g-inference-sdk`](https://pypi.org/project/0g-inference-sdk/) | `pip install 0g-inference-sdk` | Decentralized AI inference, fine-tuning, and LoRA adapters |
| [`0g-storage-sdk`](https://pypi.org/project/0g-storage-sdk/) | `pip install 0g-storage-sdk` | Decentralized storage with merkle proofs and KV streams |

## 📚 Documentation

**Full developer documentation:** [og-py.vercel.app](https://og-py.vercel.app/)

The docs cover both SDKs end-to-end with copy-paste examples:

- **0G Compute** — installation, inference, account management, service discovery, API keys, response verification, fine-tuning, OpenAI-SDK integration
- **0G Storage** — installation, file upload/download, merkle trees, KV storage, large files, error handling
- **Networks** — testnet (Galileo) and mainnet reference, contract addresses, faucets

Other resources:

- 0G Labs website: [0g.ai](https://0g.ai)
- Official 0G docs: [docs.0g.ai](https://docs.0g.ai)
- Galileo testnet faucet: [faucet.0g.ai](https://faucet.0g.ai)
- Block explorer (testnet): [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai)

## Prerequisites

- Python 3.8 or higher
- A wallet with 0G tokens for testnet ([faucet.0g.ai](https://faucet.0g.ai)) or mainnet
- An EVM-compatible private key for signing transactions

> **Note:** Earlier versions of the inference SDK required Node.js for cryptography. As of `0g-inference-sdk` v0.2.0+, the SDK uses native Python crypto — **no Node.js required**.

## 🤖 Compute SDK — `0g_py_inference/`

Python SDK for the [0G Compute Network](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/overview) — a decentralized marketplace for AI inference and fine-tuning.

**Features:**
- Service discovery (chatbot, text-to-image, image-editing, speech-to-text)
- Pay-per-request billing via on-chain ledger and provider sub-accounts
- Session-token and persistent API-key authentication
- TEE attestation verification and TEE-signed response validation
- Fine-tuning workflow (dataset upload → training → LoRA delivery)
- LoRA adapter deployment to inference GPUs and chat with fine-tuned models
- Auto-funding for unattended services
- Read-only broker for wallet-less browsing
- Native Python crypto (Baby JubJub, EdDSA, Pedersen)

**Key entry points:** `create_broker()`, `create_read_only_broker()`, `create_broker_from_env()`

**Quickstart:**
```python
import os, requests
from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei

broker = create_broker(
    private_key=os.environ["PRIVATE_KEY"],
    network="testnet",          # or "mainnet"
)

# 1. Discover providers
services = broker.inference.list_service()
provider = next(s.provider for s in services if s.service_type == "chatbot")

# 2. Fund (one-time setup)
try:
    broker.ledger.get_ledger()
except Exception:
    broker.ledger.add_ledger("3")        # contract minimum is 3 OG

broker.inference.acknowledge_provider_signer(provider)
broker.ledger.transfer_fund(provider, "inference", og_to_wei("1"))

# 3. Make an inference request
metadata = broker.inference.get_service_metadata(provider)
headers  = broker.inference.get_request_headers(provider)

response = requests.post(
    f"{metadata['endpoint']}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={
        "model": metadata["model"],
        "messages": [{"role": "user", "content": "What is 2+2?"}],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

See [`0g_py_inference/README.md`](./0g_py_inference/README.md) for the full reference.

## 📦 Storage SDK — `0g_py_storage/`

Python SDK for the [0G Storage Network](https://docs.0g.ai/developer-hub/building-on-0g/storage/overview) — decentralized, sharded storage with cryptographic merkle proofs. Byte-exact parity with the [TypeScript SDK](https://github.com/0glabs/0g-ts-sdk).

**Features:**
- Merkle tree generation (Keccak256, 256-byte chunks, 256 KB segments)
- File upload via Flow contract submission and parallel segment uploads
- File download with shard routing and optional proof verification
- Splitable upload for files larger than 4 GB
- Fragment downloads with automatic reassembly
- KV storage layer (streams, batched writes, access control, cursor iteration)
- Storage node RPC client (14 methods)
- Comprehensive error handling with retry classification

**Key entry points:** `Indexer`, `ZgFile`, `MerkleTree`, `KvClient`, `StreamDataBuilder`, `Batcher`

**Quickstart:**
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
    # Wait 3–5 minutes for propagation, then download:
    # indexer.download(result["rootHash"], "./output.txt")
```

See [`0g_py_storage/README.md`](./0g_py_storage/README.md) for the full reference.

## 🌐 Network configuration

### Galileo Testnet
| Parameter | Value |
|-----------|-------|
| Chain ID | `16602` |
| Blockchain RPC | `https://evmrpc-testnet.0g.ai` |
| Storage Indexer | `https://indexer-storage-testnet-turbo.0g.ai` |
| Faucet | [faucet.0g.ai](https://faucet.0g.ai) |
| Explorer | [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai) |

### Mainnet
| Parameter | Value |
|-----------|-------|
| Chain ID | `16661` |
| Blockchain RPC | `https://evmrpc.0g.ai` |
| Storage Indexer | `https://indexer-storage-turbo.0g.ai` |
| Explorer | [chainscan.0g.ai](https://chainscan.0g.ai) |

The SDKs auto-detect the network from the chain ID — pass `network="testnet"` or `network="mainnet"` to `create_broker()` (Compute) or use the matching RPC URLs directly (Storage).

> ⚠️ **Security:** never commit private keys or `.env` files. Add them to `.gitignore`.

## 🧪 Testing

### Storage SDK
```bash
cd 0g_py_storage
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

### Compute SDK
See [`0g_py_inference/examples/`](./0g_py_inference/examples/) for runnable end-to-end scripts (inference and fine-tuning).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for your changes
4. Ensure existing tests pass (`pytest tests/ -v`)
5. Commit and open a pull request

**Code structure:**
- Compute SDK: `0g_py_inference/zerog_py_sdk/`
- Storage SDK: `0g_py_storage/core/`, `0g_py_storage/utils/`
- Tests: `0g_py_storage/tests/`
- Examples: `0g_py_inference/examples/`

## 📄 License

MIT

---

**Built for [0G Labs](https://0g.ai)**
