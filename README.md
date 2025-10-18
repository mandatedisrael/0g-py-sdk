# 0G Labs Python SDKs

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-66%2F66%20passing-success.svg)]()
[![Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen.svg)]()

Official Python SDKs for building on [0G Labs](https://0g.ai) - The first modular AI chain with infinite scalability.

This repository contains two production-ready Python SDKs:
- **`0g_py_storage`** - 0G Storage Network SDK (decentralized storage with merkle proofs)
- **`0g_py_inference`** - 0G Compute Network SDK (decentralized AI inference)

Built for developers integrating decentralized AI inference and storage into Python applications.

## 📚 Documentation

[![Website](https://img.shields.io/badge/🌐_Website-0g.ai-blue?style=for-the-badge)](https://0g.ai)
[![Docs](https://img.shields.io/badge/📖_Documentation-docs.0g.ai-green?style=for-the-badge)](https://docs.0g.ai)
[![Explorer](https://img.shields.io/badge/🔍_Explorer-Testnet-orange?style=for-the-badge)](https://chainscan-galileo.0g.ai)

**Key Resources:**
- **0G Labs Website:** https://0g.ai
- **Official Documentation:** https://docs.0g.ai
- **Compute Network SDK Docs:** https://docs.0g.ai/developer-hub/building-on-0g/compute-network/sdk
- **Storage SDK Docs:** https://docs.0g.ai/developer-hub/building-on-0g/storage/sdk
- **Testnet Explorer:** https://chainscan-galileo.0g.ai

## Prerequisites

- Python `3.8+`
- For inference (compute):
  - Node.js `16+` (used for cryptographic operations)
  - `circomlibjs` installed globally
- For storage:
  - `web3` and `eth-account` for signing and RPC interactions

## 📦 SDKs Overview

### 📦 0G Storage SDK (`0g_py_storage/`)

![Storage SDK](https://img.shields.io/badge/SDK-Storage-blue?style=flat-square)
![Tests](https://img.shields.io/badge/tests-66%2F66-success?style=flat-square)
![TypeScript Parity](https://img.shields.io/badge/TS%20parity-100%25-blue?style=flat-square)

Production-ready Python SDK for 0G Labs Storage Network - decentralized storage with cryptographic merkle proofs.

**Features:**
- ✅ Merkle tree generation (100% parity with TypeScript SDK)
- ✅ File upload/download with shard routing
- ✅ Flow contract integration for on-chain settlement
- ✅ Automatic node selection using segment tree algorithm
- ✅ 66/66 tests passing

**Key Classes:** `Indexer`, `Uploader`, `Downloader`, `ZgFile`, `StorageNode`, `MerkleTree`

**See:** [`0g_py_storage/README.md`](./0g_py_storage/README.md) for detailed documentation.

### 🤖 0G Compute SDK (`0g_py_inference/`)

![Compute SDK](https://img.shields.io/badge/SDK-Compute-purple?style=flat-square)
![AI Inference](https://img.shields.io/badge/AI-Inference-green?style=flat-square)
![TEE Verified](https://img.shields.io/badge/TEE-Verified-orange?style=flat-square)

Python SDK for 0G Labs Compute Network - decentralized AI inference with verifiable providers.

**Features:**
- ✅ Provider service discovery
- ✅ Authenticated request headers for secure inference
- ✅ Response verification for TEE-backed services
- ✅ Billing integration with prepaid accounts
- ✅ Broker pattern for managing providers

**Key Classes:** `ZGServingBroker` (via `create_broker`)

**See:** [`0g_py_inference/README.md`](./0g_py_inference/README.md) for detailed documentation.

## 🌐 Network Configuration

### Testnet (Galileo)

```python
BLOCKCHAIN_RPC = "https://evmrpc-testnet.0g.ai"
INDEXER_RPC = "https://indexer-storage-testnet-turbo.0g.ai"
CHAIN_ID = 16602
```

**Faucet:** https://faucet.0g.ai - Get test 0G tokens for your wallet

### Mainnet

```python
BLOCKCHAIN_RPC = "https://evmrpc.0g.ai"
INDEXER_RPC = "https://indexer-storage-turbo.0g.ai"
```

⚠️ **Security:** Never commit private keys or `.env` files to version control.

---

## 🚀 Quick Start

### Storage SDK - Upload & Download Files

```python
from core.indexer import Indexer
from core.file import ZgFile
from eth_account import Account

# Setup
INDEXER_RPC = "https://indexer-storage-testnet-turbo.0g.ai"
BLOCKCHAIN_RPC = "https://evmrpc-testnet.0g.ai"
PRIVATE_KEY = "0x..."

indexer = Indexer(INDEXER_RPC)
account = Account.from_key(PRIVATE_KEY)
file = ZgFile.from_file_path("./data.txt")

# Upload
result, err = indexer.upload(
    file,
    BLOCKCHAIN_RPC,
    account,
    {'expectedReplica': 1, 'finalityRequired': True}
)

if err is None:
    print(f"✅ Uploaded: {result['rootHash']}")

    # Download (wait 3-5 min for propagation)
    indexer.download(result['rootHash'], "./output.txt")
```

### Compute SDK - AI Inference

```python
import os, json, requests
from dotenv import load_dotenv
from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei

load_dotenv()  # loads PRIVATE_KEY and RPC_URL from .env

broker = create_broker(os.getenv("PRIVATE_KEY"), os.getenv("RPC_URL"))

# Discover available services (providers and their models)
services = broker.inference.list_service()
if not services:
    raise RuntimeError("No services found")

provider_address = services[0].provider
print(f"Using provider: {provider_address}, model={services[0].model}")

# One-time: acknowledge provider’s signer (TEE verification if applicable)
broker.inference.acknowledge_provider_signer(provider_address)

# Manage funds in your prepaid inference account
broker.ledger.add_ledger("0.1")  # create account or add initial funds
broker.ledger.deposit_fund("2")  # add more funds
broker.ledger.transfer_fund(provider_address, "inference", og_to_wei("0.5"))

# Generate single-use authenticated headers and send a chat request
metadata = broker.inference.get_service_metadata(provider_address)  # {'endpoint', 'model'}
messages = [{"role": "user", "content": "What is 2 + 2?"}]
headers = broker.inference.get_request_headers(provider_address, json.dumps(messages))

resp = requests.post(
    f"{metadata['endpoint']}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": messages, "model": metadata["model"]},
)

data = resp.json()
answer = data["choices"][0]["message"]["content"]
chat_id = data.get("id")
print("Answer:", answer)

# Verify response if service is verifiable (TEE)
is_valid = broker.inference.process_response(provider_address, answer, chat_id)
print("Response valid:", is_valid)
```

---

## 📖 Detailed Setup

Each SDK has its own detailed installation guide:
- **Storage:** See [`0g_py_storage/README.md`](./0g_py_storage/README.md)
- **Compute:** See [`0g_py_inference/README.md`](./0g_py_inference/README.md)

---

## 🧪 Testing

### Storage SDK Tests
```bash
cd 0g_py_storage
source venv/bin/activate
pytest tests/ -v
# ✅ 66/66 tests passing
```

### Compute SDK
See `0g_py_inference/README.md` for inference testing examples.

---

## 🔗 Resources

[![Website](https://img.shields.io/badge/Website-0g.ai-blue)](https://0g.ai)
[![Docs](https://img.shields.io/badge/Docs-docs.0g.ai-green)](https://docs.0g.ai)
[![Faucet](https://img.shields.io/badge/Faucet-Get%20Testnet%20Tokens-yellow)](https://faucet.0g.ai)
[![Explorer](https://img.shields.io/badge/Explorer-Testnet-orange)](https://chainscan-galileo.0g.ai)
[![TypeScript SDK](https://img.shields.io/badge/TypeScript%20SDK-GitHub-blue)](https://github.com/0glabs/0g-ts-sdk)
[![0G Labs GitHub](https://img.shields.io/badge/0G%20Labs-GitHub-black)](https://github.com/0glabs)

**Quick Links:**
- **0G Labs:** https://0g.ai
- **Documentation:** https://docs.0g.ai
- **Testnet Faucet:** https://faucet.0g.ai
- **Block Explorer:** https://chainscan-galileo.0g.ai
- **TypeScript SDK:** https://github.com/0glabs/0g-ts-sdk
- **Official GitHub:** https://github.com/0glabs

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for your changes
4. Ensure all tests pass (`pytest tests/ -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Code Structure:**
- Storage SDK: `0g_py_storage/core/` and `0g_py_storage/utils/`
- Compute SDK: `0g_py_inference/zerog_py_sdk/`
- Tests: `0g_py_storage/tests/`

---

## 📄 License

MIT

---

**Built with ❤️ for [0G Labs](https://0g.ai) - The first modular AI chain**