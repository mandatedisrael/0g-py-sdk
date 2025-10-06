# 0G Compute Network Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 16+](https://img.shields.io/badge/node.js-16+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for interacting with the 0G Compute Network - a decentralized AI inference marketplace where you pay for AI model access using blockchain tokens.

> **⚠️ Note:** This SDK is not yet published to PyPI. Clone the repository to use it.

## What is 0G Compute Network?

0G Compute Network is a **blockchain-based marketplace** for AI inference services:
- **Providers** offer AI models (LLMs) with TEE-verified compute
- **Users** pay per request using 0G tokens (ERC-20)
- **Smart contracts** handle billing, accounts, and cryptographic verification
- **Decentralized** - no central authority, fully on-chain payment settlement

## Features

- ✅ **Account Management**: Fund and manage prepaid accounts for AI services
- ✅ **Service Discovery**: List and query available AI providers on-chain
- ✅ **Authenticated Requests**: Generate cryptographic signatures for pay-per-use billing
- ✅ **Provider Integration**: OpenAI-compatible API interface
- ✅ **Verifiable Computing**: TEE (Trusted Execution Environment) attestation support
- ✅ **Hybrid Architecture**: Python + Node.js for zero-knowledge cryptography

## How It Works

```
┌─────────────┐                  ┌──────────────┐                 ┌─────────────┐
│   Your App  │                  │  0G Network  │                 │  AI Provider│
│   (Python)  │                  │ (Blockchain) │                 │    (TEE)    │
└──────┬──────┘                  └──────┬───────┘                 └──────┬──────┘
       │                                │                                │
       │  1. Fund account               │                                │
       ├───────────────────────────────>│                                │
       │  (deposit 0G tokens)           │                                │
       │                                │                                │
       │  2. Acknowledge provider       │                                │
       ├───────────────────────────────>│<───────────────────────────────┤
       │  (verify TEE signer)           │  (get TEE attestation)         │
       │                                │                                │
       │  3. Generate auth headers      │                                │
       │  (cryptographic signature)     │                                │
       │                                │                                │
       │  4. Make inference request     │                                │
       ├────────────────────────────────┼───────────────────────────────>│
       │  (with signed headers)         │                                │
       │                                │                                │
       │  5. Get AI response            │                                │
       │<────────────────────────────────────────────────────────────────┤
       │                                │                                │
       │  6. Provider settles billing   │                                │
       │                                │<───────────────────────────────┤
       │                                │  (deduct tokens on-chain)      │
       └────────────────────────────────┴────────────────────────────────┘
```

## System Requirements

- **Python**: 3.8 or higher
- **Node.js**: 16.x or higher (required for cryptographic operations)

## Installation

> **Quick Start:** For a condensed setup guide, see [SETUP.md](SETUP.md)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/og-py-sdk.git
cd og-py-sdk
```

### 2. Install Node.js

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

### 3. Install circomlibjs

```bash
npm install -g circomlibjs
```

### 4. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```bash
PRIVATE_KEY=your_private_key_without_0x_prefix
RPC_URL=https://evmrpc-testnet.0g.ai
```

**⚠️ Important:** Never commit your `.env` file to version control!

## Quick Start

After following the installation steps, create a script or use the provided `test.py`:

```python
from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Initialize broker with your private key
broker = create_broker(
    private_key=os.getenv('PRIVATE_KEY'),
    rpc_url=os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')
)

# 2. Discover available AI services
services = broker.inference.list_service()
provider_address = services[0].provider

print(f"Provider: {provider_address}")
print(f"Model: {services[0].model}")

# 3. Fund your account (one-time setup)
# Skip if you already have funds
account = broker.ledger.get_ledger()
if account.balance < 0.1:
    broker.ledger.deposit_fund("2")  # Add 2 OG tokens
    print(f"✓ Added funds. New balance: {broker.ledger.get_ledger().balance} OG")

# 4. Acknowledge provider (one-time per provider)
broker.inference.acknowledge_provider_signer(provider_address)
print("✓ Provider acknowledged")

# 5. Transfer funds to provider sub-account
broker.ledger.transfer_fund(provider_address, "inference", og_to_wei("0.5"))
print("✓ Transferred 0.5 OG to provider")

# 6. Get service metadata
metadata = broker.inference.get_service_metadata(provider_address)
endpoint = metadata['endpoint']  # Automatically appends /v1/proxy
model = metadata['model']

# 7. Generate authentication headers
question = "What is 2+2?"
messages = [{"role": "user", "content": question}]
headers = broker.inference.get_request_headers(
    provider_address,
    json.dumps(messages)
)

# 8. Make inference request
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": messages, "model": model}
)

# 9. Get the answer
if response.status_code == 200:
    answer = response.json()['choices'][0]['message']['content']
    print(f"Answer: {answer}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

**Output:**
```
Provider: 0xf07240Efa67755B5311bc75784a061eDB47165Dd
Model: phala/gpt-oss-120b
✓ Added funds. New balance: 2.0 OG
✓ Provider acknowledged
✓ Transferred 0.5 OG to provider
Answer: 2 + 2 = 4.
```

## SDK Architecture

### High-Level Structure

```
zerog_py_sdk/
├── broker.py          # Main entry point - ZGServingBroker class
├── ledger.py          # Account & balance management (LedgerManager)
├── inference.py       # Service discovery & request signing (InferenceManager)
├── auth.py            # Cryptographic operations via Node.js subprocess
├── models.py          # Data structures (ServiceMetadata, LedgerAccount, etc.)
├── exceptions.py      # Custom error types
└── utils.py           # Helper functions (og_to_wei, parse receipts, etc.)
```

### Component Breakdown

#### 1. **Broker** (`broker.py`)

The main orchestrator that initializes and connects all components.

```python
class ZGServingBroker:
    """
    Main broker class that coordinates:
    - Blockchain connection (Web3)
    - Smart contract instances
    - Ledger operations
    - Inference operations
    """

    def __init__(self, private_key, rpc_url, contract_address):
        self.web3 = Web3(HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)

        # Initialize smart contracts
        self.ledger_contract = self._load_contract("LedgerManager")
        self.inference_contract = self._load_contract("InferenceServing")

        # Initialize managers
        self.ledger = LedgerManager(...)      # For payments
        self.inference = InferenceManager(...) # For AI requests
```

**Key methods:**
- `create_broker(private_key, rpc_url)` - Factory function
- `create_broker_from_env()` - Load from .env file
- `get_address()` - Get your wallet address

---

#### 2. **LedgerManager** (`ledger.py`)

Handles all on-chain account and payment operations.

```python
class LedgerManager:
    """
    Manages your prepaid account on the blockchain.
    Think of it as your "wallet" for AI services.
    """

    def add_ledger(amount: str):
        """
        Create account or add funds to main ledger.
        Sends 0G tokens to smart contract.

        Args:
            amount: OG tokens (e.g., "0.1")
        """

    def deposit_fund(amount: str):
        """
        Add more funds to existing account.
        """

    def transfer_fund(provider_address, service_type, amount_wei):
        """
        Allocate funds to specific provider's sub-account.
        Must be done before making inference requests.
        """

    def get_ledger() -> LedgerAccount:
        """
        Check your balance.
        Returns: balance, locked, total_balance (in OG)
        """

    def retrieve_fund(service_type):
        """
        Withdraw unused funds from provider sub-accounts.
        """
```

**Account Model:**
```
Main Ledger (Your Account)
├── Available Balance: 2.0 OG
├── Locked Balance: 0.5 OG (allocated to providers)
└── Total Balance: 2.5 OG

Provider Sub-Accounts
├── Provider A: 0.3 OG (for inference)
└── Provider B: 0.2 OG (for inference)
```

---

#### 3. **InferenceManager** (`inference.py`)

Discovers AI services and generates authenticated request headers.

```python
class InferenceManager:
    """
    Handles AI inference operations:
    - Finding available providers
    - Verifying TEE attestations
    - Generating cryptographic signatures
    """

    def list_service() -> List[ServiceMetadata]:
        """
        Query blockchain for all registered AI providers.
        Returns list of available models with pricing.
        """

    def get_service(provider_address) -> ServiceMetadata:
        """
        Get specific provider's service details.
        """

    def acknowledge_provider_signer(provider_address):
        """
        One-time setup per provider:
        1. Gets TEE attestation from provider
        2. Verifies quote (optional)
        3. Records TEE signer on-chain

        This links the provider's TEE to their blockchain address.
        """

    def get_service_metadata(provider_address) -> dict:
        """
        Get inference endpoint and model name.
        Automatically appends /v1/proxy to URL.

        Returns:
            {
                "endpoint": "http://provider.com:8080/v1/proxy",
                "model": "phala/gpt-oss-120b"
            }
        """

    def get_request_headers(provider_address, content) -> dict:
        """
        Generate cryptographic auth headers for request.

        Creates signature using:
        - Your private key
        - Request content hash
        - Nonce (request counter)
        - Fee estimation

        Returns headers like:
            {
                "X-Phala-Signature-Type": "StandaloneApi",
                "Address": "0xYourAddress",
                "Nonce": "123",
                "Request-Hash": "0xABC...",
                "Signature": [R, S] (EdDSA signature),
                "Fee": "1000000000",
                "Input-Fee": "500000000"
            }
        """
```

**Service Discovery Flow:**
```python
# 1. List all services
services = broker.inference.list_service()
# Returns: [ServiceMetadata, ServiceMetadata, ...]

# 2. ServiceMetadata object contains:
service = services[0]
service.provider         # "0xf07240..."
service.model           # "phala/gpt-oss-120b"
service.url             # "http://50.145.48.92:30081"
service.input_price     # 100000000000 (wei per token)
service.output_price    # 400000000000 (wei per token)
service.verifiability   # "TeeML"
service.is_verifiable() # True
```

---

#### 4. **AuthManager** (`auth.py`)

Bridges Python and Node.js for cryptographic operations.

```python
class AuthManager:
    """
    Executes Node.js subprocess for zero-knowledge cryptography.

    Uses circomlibjs for:
    - Baby JubJub elliptic curve
    - EdDSA signatures
    - Pedersen hash
    - Poseidon hash

    These are ZK-friendly primitives that can be
    efficiently verified on-chain or in ZK circuits.
    """

    def sign_message(private_key, message):
        """
        Generate EdDSA signature using Baby JubJub curve.
        This is NOT standard ECDSA - it's ZK-optimized.
        """
```

**Why Node.js?**
- Python lacks mature ZK crypto libraries
- circomlibjs is the reference implementation
- Matches TypeScript SDK exactly
- Ensures signature compatibility

---

#### 5. **Models** (`models.py`)

Data structures for type safety.

```python
@dataclass
class ServiceMetadata:
    provider: str           # Wallet address
    service_type: str       # "chatbot"
    url: str                # Provider endpoint
    input_price: int        # Wei per input token
    output_price: int       # Wei per output token
    updated_at: int         # Timestamp
    model: str              # Model identifier
    verifiability: str      # "TeeML"

@dataclass
class LedgerAccount:
    balance: float          # Available OG
    locked: float           # Locked in provider accounts
    total_balance: float    # balance + locked

@dataclass
class RequestHeaders:
    # Cryptographic auth headers for inference
    ...
```

---

#### 6. **Utilities** (`utils.py`)

Helper functions for common operations.

```python
def og_to_wei(amount: str) -> int:
    """Convert OG tokens to wei (10^18)"""
    return int(float(amount) * 10**18)

def wei_to_og(wei: int) -> float:
    """Convert wei to OG tokens"""
    return wei / 10**18

def parse_transaction_receipt(receipt):
    """Extract useful info from blockchain receipt"""
    return {
        "transaction_hash": receipt.transactionHash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "status": receipt.status
    }
```

---

### Request Flow (Detailed)

Here's what happens when you make an inference request:

```python
# Step 1: Generate headers
headers = broker.inference.get_request_headers(provider, content)

# Internally:
# 1.1: Hash the request content
content_hash = hash_content(content)

# 1.2: Get account nonce (request counter)
account = inference_contract.getAccount(provider)
nonce = account.nonce + 1

# 1.3: Estimate fees
service = get_service(provider)
estimated_tokens = estimate_input_tokens(content)
fee = estimated_tokens * service.input_price

# 1.4: Create signature payload
message = {
    "provider": provider,
    "nonce": nonce,
    "content_hash": content_hash,
    "fee": fee
}

# 1.5: Sign with Node.js (EdDSA)
signature = auth_manager.sign_message(private_key, message)

# 1.6: Return headers
return {
    "X-Phala-Signature-Type": "StandaloneApi",
    "Address": user_address,
    "Nonce": nonce,
    "Request-Hash": content_hash,
    "Signature": signature,  # [R, S]
    "Fee": fee,
    "Input-Fee": fee,
    "VLLM-Proxy": "true"
}

# Step 2: Make HTTP request to provider
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": [...], "model": model}
)

# Step 3: Provider verifies signature
# Provider checks:
# ✓ Signature matches user address
# ✓ Nonce is correct (prevents replay)
# ✓ Fee is sufficient
# ✓ User has balance in contract

# Step 4: Provider processes request
# ✓ Runs LLM inference
# ✓ Returns response

# Step 5: Provider settles billing (async)
# ✓ Calls contract.settleAccounts([user_address])
# ✓ Deducts actual tokens used from user balance
# ✓ Increments nonce on-chain
```

---

## Complete Working Example

See `test.py` for a full working example that:

1. ✅ Initializes broker
2. ✅ Discovers providers
3. ✅ Checks & adds funds
4. ✅ Acknowledges provider
5. ✅ Transfers funds to provider
6. ✅ Makes inference request
7. ✅ Receives AI response

Run it:
```bash
# Make sure you're in the project directory
cd og-py-sdk

# Activate virtual environment
source venv/bin/activate

# Run the test
python3 test.py
```

**Expected output:**
```
Testing broker initialization...
✓ Broker initialized
✓ Address: 0xB3AD3a10d187cbc4ca3e8c3EDED62F8286F8e16E

Testing service discovery...
✓ Found 4 services

Querying provider for 'Highest World Cup Holder'...
✓ Using provider: 0xf07240Efa67755B5311bc75784a061eDB47165Dd
✓ Model: phala/gpt-oss-120b
✓ Main ledger balance: 2.0 OG
✓ Provider acknowledged
✓ Transferred funds

==================================================
Question: Who owns the largest number of football World Cups?
Answer: Brazil owns the largest number of football World Cups with 5 titles.
==================================================

✅ All tests passed!
```

---

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
# Add funds to create account or top up
receipt = broker.ledger.add_ledger("0.1")

# Deposit more funds
receipt = broker.ledger.deposit_fund("0.5")

# Transfer to provider sub-account
from zerog_py_sdk.utils import og_to_wei
broker.ledger.transfer_fund(provider_address, "inference", og_to_wei("0.5"))

# Check balance
account = broker.ledger.get_ledger()
print(f"Balance: {account.balance} OG")
print(f"Total: {account.total_balance} OG")

# Request refund from all providers
receipt = broker.ledger.retrieve_fund("inference")
```

### Service Discovery

```python
# List all services
services = broker.inference.list_service()

for service in services:
    print(f"Provider: {service.provider}")
    print(f"Model: {service.model}")
    print(f"URL: {service.url}")
    print(f"Input Price: {service.input_price} wei/token")
    print(f"Output Price: {service.output_price} wei/token")
    print(f"Verifiable: {service.is_verifiable()}")

# Get specific service
service = broker.inference.get_service(provider_address)
```

### Making Requests

```python
import requests
import json

# 1. Acknowledge provider (once per provider)
broker.inference.acknowledge_provider_signer(provider_address)

# 2. Get service info
metadata = broker.inference.get_service_metadata(provider_address)
endpoint = metadata['endpoint']  # Already includes /v1/proxy
model = metadata['model']

# 3. Generate auth headers
question = "What is the capital of France?"
messages = [{"role": "user", "content": question}]
headers = broker.inference.get_request_headers(
    provider_address,
    json.dumps(messages)
)

# 4. Make request
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": messages, "model": model}
)

# 5. Parse response
if response.status_code == 200:
    answer = response.json()['choices'][0]['message']['content']
    print(f"Answer: {answer}")
```

### Using with OpenAI SDK

```python
from openai import OpenAI

# Get metadata
metadata = broker.inference.get_service_metadata(provider_address)

# Generate headers (OpenAI SDK will add these to every request)
headers = broker.inference.get_request_headers(
    provider_address,
    json.dumps([{"role": "user", "content": "Hello"}])
)

# Create client
client = OpenAI(
    base_url=metadata['endpoint'],
    api_key="",  # Empty string (auth via headers)
    default_headers=headers
)

# Make request
completion = client.chat.completions.create(
    model=metadata['model'],
    messages=[{"role": "user", "content": "Hello!"}]
)

print(completion.choices[0].message.content)
```

---

## Available Providers (Testnet)

Query live providers dynamically:

```python
services = broker.inference.list_service()
for s in services:
    print(f"{s.model} - {s.provider}")
```

**Example providers:**
- `phala/gpt-oss-120b` - 120B parameter model
- `phala/deepseek-chat-v3-0324` - DeepSeek v3 model
- `phala/qwen2.5-vl-72b-instruct` - Qwen 2.5 vision-language model

All providers use **TeeML** (TEE-verified compute) for security.

---

## Error Handling

```python
from zerog_py_sdk import (
    ZGServingBrokerError,
    InsufficientBalanceError,
    ProviderNotAcknowledgedError,
    ContractError,
    NetworkError
)

try:
    broker.ledger.add_ledger("0.1")
except InsufficientBalanceError as e:
    print(f"Not enough OG tokens in wallet: {e}")
except ContractError as e:
    print(f"Smart contract error: {e}")
except NetworkError as e:
    print(f"RPC connection failed: {e}")
```

---

## Troubleshooting

### "Transaction failed" when acknowledging provider
**Cause:** Account doesn't exist yet.
**Fix:** The SDK now auto-creates accounts. Update to latest version.

### "403 Forbidden" from provider
**Cause:** Missing `/v1/proxy` in endpoint URL.
**Fix:** Use `get_service_metadata()` - it adds the proxy path automatically.

### "Insufficient balance"
**Cause:** No funds in account or not transferred to provider.
**Fix:**
```python
# Add to main ledger
broker.ledger.deposit_fund("2")

# Transfer to provider
from zerog_py_sdk.utils import og_to_wei
broker.ledger.transfer_fund(provider, "inference", og_to_wei("0.5"))
```

### "Module not found: circomlibjs"
**Cause:** Node.js dependency not installed.
**Fix:** `npm install -g circomlibjs`

---

## Architecture Deep Dive

### Why Hybrid Python + Node.js?

**Python Benefits:**
- ✅ Rich ML/AI ecosystem
- ✅ Web3.py for Ethereum
- ✅ Easy HTTP requests
- ✅ Familiar to AI engineers

**Node.js Benefits:**
- ✅ circomlibjs (reference ZK crypto library)
- ✅ Signature compatibility with TypeScript SDK
- ✅ Baby JubJub + EdDSA support
- ✅ Faster cryptographic operations

**How they communicate:**
```
Python (main SDK)
    │
    ├── Web3.py ────────> Blockchain (RPC)
    ├── Requests ───────> AI Provider (HTTP)
    │
    └── Subprocess ─────> Node.js (circomlibjs)
                            │
                            └── EdDSA signatures
```

### Smart Contract Interaction

The SDK interacts with two main contracts:

**1. LedgerManager** (`0x5e583B...`)
- Manages user accounts and balances
- Handles deposits, withdrawals, transfers
- Tracks provider allocations

**2. InferenceServing** (`0x8e893C...`)
- Registers AI providers
- Stores service metadata (models, pricing, URLs)
- Verifies TEE signers
- Settles usage-based billing

---

## Get Testnet Tokens

Need 0G tokens for testing?

1. Get wallet address: `broker.get_address()`
2. Visit faucet: https://faucet.0g.ai
3. Paste your address and request tokens

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup

Follow the installation steps above, then:

```bash
# Make your changes to the SDK files
# The SDK is in zerog_py_sdk/ directory

# Test your changes
python3 test.py

# Or create your own test script
python3 your_script.py
```

### Project Structure

```
og-py-sdk/
├── zerog_py_sdk/          # Main SDK package
│   ├── __init__.py        # Public API exports
│   ├── broker.py          # Broker implementation
│   ├── ledger.py          # Ledger manager
│   ├── inference.py       # Inference manager
│   ├── auth.py            # Cryptography via Node.js
│   ├── models.py          # Data models
│   ├── exceptions.py      # Custom exceptions
│   └── utils.py           # Helper functions
├── test.py                # Working example script
├── queryProvider.py       # Provider query example
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
└── README.md              # This file
```

---

## License

MIT License - see LICENSE file for details.

---

## Links

- [0G Documentation](https://docs.0g.ai/)
- [TypeScript SDK](https://github.com/0glabs/0g-serving-broker)
- [Compute Network Docs](https://docs.0g.ai/developer-hub/building-on-0g/compute-network/sdk)
- [Author Twitter/X](https://x.com/damiclone)

---

## Support

For issues and questions:
- **GitHub Issues**: [Report a bug](https://github.com/0glabs/0g-compute-sdk-python/issues)
- **Discord**: [0G Labs Community](https://discord.gg/0glabs)
- **Documentation**: [docs.0g.ai](https://docs.0g.ai/)

---

## Changelog

### v0.1.0 (Latest)
- ✅ Fixed endpoint URL - now correctly appends `/v1/proxy`
- ✅ Auto-creates accounts when acknowledging providers
- ✅ Improved error handling
- ✅ Added complete working example
- ✅ Full documentation with architecture details
