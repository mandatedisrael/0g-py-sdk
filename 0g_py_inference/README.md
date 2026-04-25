# 0G Compute Network — Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/0g-inference-sdk.svg)](https://pypi.org/project/0g-inference-sdk/)

Python SDK for the [0G Compute Network](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/overview) — a decentralized marketplace for AI inference and fine-tuning.

> 📚 **Full developer documentation:** [og-py.vercel.app](https://og-py.vercel.app/)

## What you get

- **Decentralized AI inference** — chatbot, text-to-image, image-editing, speech-to-text providers, all OpenAI-compatible
- **Fine-tuning** — upload datasets to TEEs, train LoRA adapters, deploy to inference GPUs
- **Pay-per-request billing** — on-chain ledger with provider sub-accounts; no signups, no credit cards
- **TEE attestation** — every response is cryptographically signed; verify on-chain
- **API keys** — persistent, individually revocable tokens for server applications
- **Auto-funding** — background top-ups keep long-running services alive
- **Read-only mode** — list providers without connecting a wallet
- **Native Python crypto** — Baby JubJub, EdDSA, Pedersen — no Node.js dependency

## Installation

```bash
pip install 0g-inference-sdk
```

Requires Python 3.8+. The SDK automatically installs `web3`, `eth-account`, `requests`.

### Configure

```bash
# .env
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
RPC_URL=https://evmrpc-testnet.0g.ai
NETWORK=testnet
```

> ⚠️ Never commit your `.env` file.

## Quickstart

```python
import os, requests
from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei

# 1. Connect
broker = create_broker(
    private_key=os.environ["PRIVATE_KEY"],
    network="testnet",          # or "mainnet"
)

# 2. Discover providers
services = broker.inference.list_service()
provider = next(s.provider for s in services if s.service_type == "chatbot")

# 3. Fund (one-time setup)
try:
    broker.ledger.get_ledger()
except Exception:
    broker.ledger.add_ledger("3")               # contract minimum is 3 OG

broker.inference.acknowledge_provider_signer(provider)
broker.ledger.transfer_fund(provider, "inference", og_to_wei("1"))

# 4. Make an inference request
metadata = broker.inference.get_service_metadata(provider)
headers  = broker.inference.get_request_headers(provider)

response = requests.post(
    f"{metadata['endpoint']}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={
        "model":    metadata["model"],
        "messages": [{"role": "user", "content": "What is 2+2?"}],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

## Browse without a wallet

```python
from zerog_py_sdk import create_read_only_broker

browser = create_read_only_broker(network="testnet")
for s in browser.list_service():
    print(f"{s.model} — {s.provider}")
```

`list_service_with_detail()` adds health metrics (uptime, response time) from the network's monitoring API.

## Use with the OpenAI Python SDK

Issue a persistent API key once, then use it like any OpenAI key:

```python
from openai import OpenAI

secret   = broker.inference.get_secret(provider)
metadata = broker.inference.get_service_metadata(provider)

client = OpenAI(base_url=metadata["endpoint"], api_key=secret)

response = client.chat.completions.create(
    model    = metadata["model"],
    messages = [{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

## Fine-tuning

```python
PROVIDER = "0xFineTuningProvider..."
MODEL    = "Qwen2.5-0.5B-Instruct"

broker.fine_tuning.acknowledge_provider_signer(PROVIDER)
broker.ledger.transfer_fund(PROVIDER, "fine-tuning", og_to_wei("1"))

# Upload dataset and create task
upload  = broker.fine_tuning.upload_dataset_to_tee(PROVIDER, "./train.jsonl")
task_id = broker.fine_tuning.create_task(
    provider_address       = PROVIDER,
    pre_trained_model_name = MODEL,
    dataset_hash           = upload["datasetHash"],
    training_path          = "./training_params.json",
)

# After training completes, acknowledge the model and deploy LoRA
broker.fine_tuning.acknowledge_model(PROVIDER, task_id, "./lora.bin")

deploy = broker.inference.lora.deploy_adapter(
    provider_address = PROVIDER,
    base_model       = MODEL,
    task_id          = task_id,
    wait             = True,
)

# Chat with the fine-tuned adapter
response = broker.inference.lora.chat(PROVIDER, deploy.adapter_name, "Who are you?")
```

See [examples/fine_tuning/fine_tuning_example.py](./examples/fine_tuning/fine_tuning_example.py) for a complete end-to-end script.

## Verify TEE-signed responses

```python
chat_id = response.json()["id"]
content = response.json()["choices"][0]["message"]["content"]

is_valid = broker.inference.process_response(
    provider_address = provider,
    content          = content,
    chat_id          = chat_id,
)
```

For a full attestation check (TEE signer extraction, optional Automata contract verification, signed report):

```python
result = broker.inference.verify_service(provider, output_dir="./reports")
```

## SDK reference

The SDK exposes everything from the top-level `zerog_py_sdk` package:

| Symbol | Purpose |
|--------|---------|
| `create_broker(private_key, network=None, rpc_url=None)` | Main factory — returns `ZGServingBroker` |
| `create_broker_from_env(env_file=".env")` | Load credentials from a `.env` file |
| `create_read_only_broker(network=None)` | No wallet required — for browsing services |
| `broker.ledger` | `LedgerManager` — deposits, transfers, refunds |
| `broker.inference` | `InferenceManager` — service discovery, requests, API keys |
| `broker.inference.lora` | `LoRAProcessor` — deploy LoRA adapters, chat |
| `broker.fine_tuning` | `FineTuningBroker` — datasets, tasks, model delivery |
| `og_to_wei`, `wei_to_og` | OG ↔ wei conversion helpers (`zerog_py_sdk.utils`) |
| `ServiceMetadata`, `LedgerAccount`, `Account`, `ApiKeyInfo` | Data classes |
| `ZGServingBrokerError`, `InsufficientBalanceError`, `ContractError`, ... | Exception hierarchy |

For the full per-class API, browse the [Compute reference docs](https://og-py.vercel.app/) or read the source — every public method has a docstring.

## Network configuration

| Network | Chain ID | RPC |
|---------|----------|-----|
| Mainnet | `16661` | `https://evmrpc.0g.ai` |
| Testnet (Galileo) | `16602` | `https://evmrpc-testnet.0g.ai` |

Contract addresses are bundled with the SDK and resolved automatically from the chain ID. Override with `create_broker(..., ledger_address=..., inference_address=...)` if needed.

Get testnet tokens at [faucet.0g.ai](https://faucet.0g.ai).

## Examples

Runnable scripts in [`examples/`](./examples/):

- `examples/inference/inference_example.py` — end-to-end inference flow
- `examples/inference/setup_account.py` — create and fund a ledger
- `examples/inference/diagnose_account.py` — inspect your account state
- `examples/fine_tuning/fine_tuning_example.py` — full fine-tuning + deploy + chat

## Troubleshooting

- **403 Forbidden** — endpoint URL must include `/v1/proxy`. Use `broker.inference.get_service_metadata(provider)["endpoint"]`, which appends it automatically.
- **401 Unauthorized** — session token expired (24h) or revoked. Headers refresh on the next `get_request_headers()` call.
- **Insufficient balance** — top up with `broker.ledger.deposit_fund("1")` and transfer to the provider with `broker.ledger.transfer_fund(...)`.
- **Provider not acknowledged** — call `broker.inference.acknowledge_provider_signer(provider)` once per provider.
- **Empty service list** — check chain ID matches the network you intended (`broker.web3.eth.chain_id`).

## Contributing

PRs welcome. Please add tests and run them locally before opening a PR.

## License

MIT

## Links

- 📚 **Documentation:** [og-py.vercel.app](https://og-py.vercel.app/)
- 🌐 0G Labs: [0g.ai](https://0g.ai)
- 📖 Official docs: [docs.0g.ai](https://docs.0g.ai)
- 🚰 Testnet faucet: [faucet.0g.ai](https://faucet.0g.ai)
- 🔍 Block explorer: [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai)
