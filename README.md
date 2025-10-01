# 0G Compute Network Python SDK

Python SDK for interacting with the 0G Compute Network - a decentralized AI inference marketplace.

## Features

- **Account Management**: Fund and manage prepaid accounts for AI services
- **Service Discovery**: List and query available AI providers
- **Authenticated Requests**: Generate cryptographic proofs for billing
- **Provider Integration**: OpenAI-compatible API interface
- **Verifiable Computing**: Support for TEE (Trusted Execution Environment) services

## System Requirements

- **Python**: 3.8 or higher
- **Node.js**: 16.x or higher (required for cryptographic operations)

## Installation

### 1. Install Node.js

If you don't have Node.js installed:
- Download from [nodejs.org](https://nodejs.org/)
- Or use a package manager:
  ```bash
  # macOS
  brew install node
  
  # Ubuntu/Debian
  sudo apt install nodejs npm
  
  # Windows
  # Download installer from nodejs.org
  ```

### 2. Install circomlibjs

```bash
npm install -g circomlibjs
```

### 3. Install Python SDK

```bash
pip install og-compute-sdk
```

## Quick Start

```python
from zerog_py_sdk import create_broker
import requests

# Initialize broker
broker = create_broker(
    private_key="0x...",
    rpc_url="https://evmrpc-testnet.0g.ai"
)

# Get available services
services = broker.inference.list_service()
provider = services[0].provider

# Fund your account (0.1 OG ≈ 10,000 requests)
broker.ledger.add_ledger("0.1", provider)

# Check balance
account = broker.ledger.get_ledger(provider)
print(f"Balance: {account.balance} wei")

# Acknowledge provider (one-time setup)
broker.inference.acknowledge_provider_signer(provider)

# Get service metadata
metadata = broker.inference.get_service_metadata(provider)
endpoint = metadata['endpoint']
model = metadata['model']

# Generate authentication headers
content = "Hello, how are you?"
headers = broker.inference.get_request_headers(provider, content)

# Make request
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={
        "messages": [{"role": "user", "content": content}],
        "model": model
    }
)

print(response.json()['choices'][0]['message']['content'])
```

## Usage with Environment Variables

Create a `.env` file:
```bash
PRIVATE_KEY=0x...
RPC_URL=https://evmrpc-testnet.0g.ai
```

Then use:
```python
from zerog_py_sdk import create_broker_from_env

broker = create_broker_from_env()
```

## API Reference

### Broker Initialization

```python
from zerog_py_sdk import create_broker

broker = create_broker(
    private_key="0x...",
    rpc_url="https://evmrpc-testnet.0g.ai",
    contract_address=None  # Optional, uses default if not provided
)
```

### Ledger Operations

```python
# Add funds to account
receipt = broker.ledger.add_ledger("0.1", provider_address)

# Deposit more funds
receipt = broker.ledger.deposit_fund("0.5", provider_address)

# Check balance
account = broker.ledger.get_ledger(provider_address)
print(f"Balance: {account.balance}")
print(f"Available: {account.available}")

# Request refund
receipt = broker.ledger.retrieve_fund(provider_address)
```

### Service Discovery

```python
# List all services
services = broker.inference.list_service()

for service in services:
    print(f"Provider: {service.provider}")
    print(f"Model: {service.model}")
    print(f"Endpoint: {service.url}")
    print(f"Verifiable: {service.is_verifiable()}")

# Get specific service
service = broker.inference.get_service(provider_address)
```

### Making Requests

```python
# Acknowledge provider (once per provider)
broker.inference.acknowledge_provider_signer(provider_address)

# Get service info
metadata = broker.inference.get_service_metadata(provider_address)

# Generate headers
headers = broker.inference.get_request_headers(
    provider_address,
    content="Your prompt here"
)

# Make request (using requests library)
response = requests.post(
    f"{metadata['endpoint']}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={
        "messages": [{"role": "user", "content": "Hello"}],
        "model": metadata['model']
    }
)
```

### Using with OpenAI SDK

```python
from openai import OpenAI

# Get metadata and headers
metadata = broker.inference.get_service_metadata(provider_address)
headers = broker.inference.get_request_headers(provider_address, content)

# Create OpenAI client
client = OpenAI(
    base_url=metadata['endpoint'],
    api_key="",  # Empty string
    default_headers=headers
)

# Make request
completion = client.chat.completions.create(
    model=metadata['model'],
    messages=[{"role": "user", "content": "Hello!"}]
)

print(completion.choices[0].message.content)
```

## Official Providers

The 0G testnet has verified providers:

| Model | Description | Verification |
|-------|-------------|--------------|
| llama-3.3-70b-instruct | 70B parameter model for general AI tasks | TEE (TeeML) |
| deepseek-r1-70b | Advanced reasoning model | TEE (TeeML) |

Query them dynamically using `broker.inference.list_service()`

## Error Handling

```python
from zerog_py_sdk import (
    ZGServingBrokerError,
    InsufficientBalanceError,
    ProviderNotAcknowledgedError,
    ConfigurationError
)

try:
    broker.ledger.add_ledger("0.1", provider)
except InsufficientBalanceError as e:
    print(f"Not enough funds: {e}")
except ProviderNotAcknowledgedError as e:
    print(f"Provider not acknowledged: {e}")
except ZGServingBrokerError as e:
    print(f"Broker error: {e}")
```

## Architecture

This SDK uses a hybrid approach:
- **Python**: Main SDK interface, blockchain interactions, HTTP requests
- **Node.js (circomlibjs)**: Cryptographic operations (Baby JubJub, EdDSA, Pedersen hash)

The cryptographic operations use zero-knowledge friendly primitives for efficient on-chain verification.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Links

- [0G Documentation](https://docs.0g.ai/)
- [TypeScript SDK](https://github.com/0glabs/0g-serving-broker)
- [Author Twitter/X](https://x.com/damiclone)

## Support

For issues and questions:
- GitHub Issues: [Report a bug](https://github.com/0glabs/0g-compute-sdk-python/issues)
- Discord: [0G Labs Community](https://discord.gg/0glabs)