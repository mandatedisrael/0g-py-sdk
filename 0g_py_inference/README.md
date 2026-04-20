# 0G Compute Network Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for interacting with the 0G Compute Network - a decentralized AI inference marketplace where you pay for AI model access using blockchain tokens.

> **✅ Available on PyPI:** `pip install 0g-py-sdk`

## What is 0G Compute Network?

0G Compute Network is a **blockchain-based marketplace** for AI inference services:
- **Providers** offer AI models (LLMs) with TEE-verified compute
- **Users** pay per request using 0G tokens (ERC-20)
- **Smart contracts** handle billing, accounts, and cryptographic verification
- **Decentralized** - no central authority, fully on-chain payment settlement

## Features

- ✅ **Session Token Auth**: New simplified authorization system (no complex headers)
- ✅ **Account Management**: Fund and manage prepaid accounts for AI services
- ✅ **Service Discovery**: List and query available AI providers on-chain
- ✅ **Read-Only Mode**: Browse services without wallet connection
- ✅ **Multi-Network Support**: Mainnet and testnet with auto-detection
- ✅ **API Key Management**: Create persistent, revocable API keys
- ✅ **Provider Integration**: OpenAI-compatible API interface
- ✅ **Verifiable Computing**: TEE (Trusted Execution Environment) attestation support
- ✅ **Response Verification**: Verify TEE-signed responses
- ✅ **Caching System**: Built-in caching for performance
- ✅ **Fine-Tuning Support**: Upload datasets and fine-tune models on 0G Compute Network

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
       │  3. Get session token          │                                │
       │  (auto-generated & cached)     │                                │
       │                                │                                │
       │  4. Make inference request     │                                │
       ├────────────────────────────────┼───────────────────────────────>│
       │  (with Authorization header)   │                                │
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

## Installation

> **Quick Start:** For a condensed setup guide, see [SETUP.md](SETUP.md)

### Install from PyPI (Recommended)

```bash
pip install 0g-py-sdk
```

### Development Setup (Optional)

If you want to contribute or modify the SDK:

```bash
# Clone the repository
git clone https://github.com/mandatedisrael/0g-py-sdk.git
cd 0g-py-sdk/0g_py_inference

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e .
```

### Configure Environment Variables

Create a `.env` file in your project directory:

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
    broker.ledger.deposit_fund("2")  # Add 2 OG tokens (ledger must already exist)
    print(f"✓ Added funds. New balance: {broker.ledger.get_ledger().balance} OG")

# 4. Acknowledge provider (one-time per provider)
broker.inference.acknowledge_provider_signer(provider_address)
print("✓ Provider acknowledged")

# 5. Transfer funds to provider sub-account (recommended minimum: 1 OG)
broker.ledger.transfer_fund(provider_address, "inference", og_to_wei("1"))
print("✓ Transferred 1 OG to provider")

# 6. Get service metadata
metadata = broker.inference.get_service_metadata(provider_address)
endpoint = metadata['endpoint']  # Automatically appends /v1/proxy
model = metadata['model']

# 7. Get authentication headers (NEW: simplified session token auth)
headers = broker.inference.get_request_headers(provider_address)
# Returns: {"Authorization": "Bearer app-sk-..."}

# 8. Make inference request
messages = [{"role": "user", "content": "What is 2+2?"}]
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
Model: qwen/qwen-2.5-7b-instruct
✓ Added funds. New balance: 2.0 OG
✓ Provider acknowledged
✓ Transferred 0.5 OG to provider
Answer: 2 + 2 = 4.
```

---

## Browse Services Without Wallet (Read-Only Mode)

You can list available AI providers without connecting a wallet:

```python
from zerog_py_sdk import create_read_only_broker

# Create read-only broker (no private key needed)
broker = create_read_only_broker()

# List all available services
services = broker.list_service()
for svc in services:
    print(f"{svc.model} - {svc.provider}")
    print(f"  URL: {svc.url}")
    print(f"  Input: {svc.input_price} wei/token")
    print(f"  Output: {svc.output_price} wei/token")

# Get services with health metrics
detailed = broker.list_service_with_detail()
for svc in detailed:
    if svc.health_metrics:
        print(f"{svc.model}: {svc.health_metrics.uptime}% uptime")

# Use mainnet instead of testnet
mainnet_broker = create_read_only_broker(network="mainnet")
```

---

## Network Configuration

The SDK supports multiple networks with auto-detection:

```python
from zerog_py_sdk import (
    create_broker,
    get_contract_addresses,
    get_rpc_url,
    MAINNET_CHAIN_ID,  # 16661
    TESTNET_CHAIN_ID,  # 16602
)

# Testnet (default)
broker = create_broker(
    private_key="0x...",
    rpc_url="https://evmrpc-testnet.0g.ai"
)

# Mainnet
broker = create_broker(
    private_key="0x...",
    rpc_url="https://evmrpc.0g.ai"
)

# Get contract addresses for a network
addrs = get_contract_addresses("mainnet")
print(f"Inference: {addrs.inference}")
print(f"Ledger: {addrs.ledger}")

# Auto-detect from chain ID
addrs = get_contract_addresses(chain_id=16661)
```

## SDK Architecture

### High-Level Structure

```
zerog_py_sdk/
├── broker.py          # Main entry point - ZGServingBroker class
├── ledger.py          # Account & balance management (LedgerManager)
├── inference.py       # Service discovery & request signing (InferenceManager)
├── session.py         # Session token management (NEW)
├── read_only.py       # Read-only broker for wallet-less operations (NEW)
├── constants.py       # Network constants & contract addresses (NEW)
├── extractors.py      # Service type extractors (chatbot, image, etc.) (NEW)
├── cache.py           # Built-in caching system (NEW)
├── verifier.py        # Response verification for TEE (NEW)
├── auth.py            # Cryptographic operations (native Python)
├── models.py          # Data structures (ServiceMetadata, LedgerAccount, etc.)
├── exceptions.py      # Custom error types
├── utils.py           # Helper functions (og_to_wei, parse receipts, etc.)
└── crypto/            # Native Python crypto (no Node.js dependency)
    ├── eddsa.py       # EdDSA signatures on Baby JubJub curve
    ├── pedersen.py    # Pedersen hash function
    └── baby_jubjub.py # Baby JubJub elliptic curve
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
    - Generating session tokens for authentication
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
                "model": "qwen/qwen-2.5-7b-instruct"
            }
        """

    def get_request_headers(provider_address) -> dict:
        """
        Generate session token auth headers for request.
        
        NEW: No content parameter needed! Session tokens are
        provider-scoped and auto-cached for 24 hours.

        Returns headers like:
            {
                "Authorization": "Bearer app-sk-..."
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
service.model           # "qwen/qwen-2.5-7b-instruct"
service.url             # "http://50.145.48.92:30081"
service.input_price     # 100000000000 (wei per token)
service.output_price    # 400000000000 (wei per token)
service.verifiability   # "TeeML"
service.is_verifiable() # True
```

---

#### 4. **SessionManager** (`session.py`) - NEW

Manages session tokens for the new authorization system.

```python
from zerog_py_sdk import SessionManager, SessionMode

class SessionManager:
    """
    Manages session tokens for the 0G Compute Network.
    
    Replaces the old header-based authentication with the new
    session token system. Supports both ephemeral (SDK usage) 
    and persistent (API keys) tokens.
    """
    
    def get_request_headers(provider_address) -> dict:
        """
        Get request headers with session token authorization.
        Auto-generates and caches ephemeral tokens (24h).
        
        Returns:
            {"Authorization": "Bearer app-sk-..."}
        """
    
    def create_api_key(provider_address, expires_in=None) -> ApiKeyInfo:
        """
        Create a persistent API key (tokenId 0-254).
        Can be individually revoked. Great for server applications.
        
        Args:
            provider_address: Provider's wallet address
            expires_in: Expiration in milliseconds (0 = never)
        
        Returns:
            ApiKeyInfo with raw_token for use in requests
        """
```

**Token Types:**
- **Ephemeral (tokenId=255)**: Auto-generated, 24h max, can't be individually revoked
- **Persistent (tokenId 0-254)**: Manually created, individually revocable API keys

---

#### 5. **Native Crypto** (`crypto/`) - No Node.js Required!

The SDK now includes pure Python implementations of ZK-friendly cryptography:

```python
# Internally used - you don't need to call these directly
from zerog_py_sdk.crypto import (
    eddsa_sign,           # EdDSA signatures on Baby JubJub
    pedersen_hash,        # Pedersen hash function
    BabyJubJubPoint,      # Baby JubJub curve operations
)
```

**Why native Python?**
- No Node.js/npm dependency
- Easier installation
- Works in any Python environment

---

#### 6. **Models** (`models.py`)

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

#### 7. **Utilities** (`utils.py`)

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

Here's what happens when you make an inference request with the new session token system:

```python
# Step 1: Get session token headers
headers = broker.inference.get_request_headers(provider)
# Returns: {"Authorization": "Bearer app-sk-..."}

# Internally:
# 1.1: Check session cache for valid token
cached = session_cache.get(provider)
if cached and cached.expires_at > now + 1_hour:
    return cached.headers

# 1.2: Create session token
token = {
    "address": user_address,
    "provider": provider,
    "timestamp": current_time_ms,
    "expiresAt": current_time_ms + 24_hours,
    "nonce": random_hex(16),
    "generation": account.generation,
    "tokenId": 255  # Ephemeral
}

# 1.3: Sign token (native Python EdDSA)
message_hash = keccak256(json.dumps(token))
signature = eth_sign(private_key, message_hash)

# 1.4: Encode as Authorization header
encoded = base64(json.dumps(token) + "|" + signature)
return {"Authorization": f"Bearer app-sk-{encoded}"}

# Step 2: Make HTTP request to provider
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": [...], "model": model}
)

# Step 3: Provider validates session token
# Provider checks:
# ✓ Signature matches address in token
# ✓ Token not expired
# ✓ Token generation matches account (not batch-revoked)
# ✓ TokenId not individually revoked (for persistent tokens)
# ✓ User has balance in contract

# Step 4: Provider processes request
# ✓ Runs LLM inference
# ✓ Returns response

# Step 5: Provider settles billing (async)
# ✓ Calls contract.settleAccounts([user_address])
# ✓ Deducts actual tokens used from user balance
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
# Create ledger account (contract minimum: 3 0G)
receipt = broker.ledger.add_ledger("3")

# Top up an existing ledger (any positive amount)
receipt = broker.ledger.deposit_fund("0.5")

# Transfer to provider sub-account (recommended minimum: 1 0G)
from zerog_py_sdk.utils import og_to_wei
broker.ledger.transfer_fund(provider_address, "inference", og_to_wei("1"))

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

# 3. Get auth headers (NEW: no content parameter needed!)
headers = broker.inference.get_request_headers(provider_address)

# 4. Make request
messages = [{"role": "user", "content": "What is the capital of France?"}]
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

### Creating Persistent API Keys

#### Using get_secret() (Recommended)

```python
# Generate a permanent API key (never expires)
secret = broker.inference.get_secret(provider_address)
print(f"API Key: {secret}")
# Output: app-sk-eyJhZGRyZXNzIjoiMHhCM0FEM2ExMGQxODdjYmM...

# Use directly in HTTP requests
headers = {"Authorization": f"Bearer {secret}"}
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": messages, "model": model}
)

# Generate API key with expiration (7 days)
secret_7d = broker.inference.get_secret(
    provider_address,
    expires_in=7*24*60*60*1000  # milliseconds
)

# Generate API key with specific token ID
secret_with_id = broker.inference.get_secret(
    provider_address,
    token_id=10  # 0-254 available
)

# Revoke specific API key
broker.inference.revoke_api_key(provider_address, token_id=10)

# Revoke all API keys for a provider
broker.inference.revoke_all_tokens(provider_address)
```

#### Using create_api_key() (Alternative method)

For server applications that need long-lived credentials:

```python
from zerog_py_sdk import SessionMode

# Create an API key that never expires
api_key_info = broker.inference.create_api_key(
    provider_address,
    expires_in=0  # 0 = never expires
)

print(f"API Key: {api_key_info.raw_token}")
print(f"Token ID: {api_key_info.token_id}")

# Use the API key in requests
headers = {"Authorization": f"Bearer {api_key_info.raw_token}"}
response = requests.post(
    f"{endpoint}/chat/completions",
    headers={"Content-Type": "application/json", **headers},
    json={"messages": messages, "model": model}
)
```

### Using with OpenAI SDK

```python
from openai import OpenAI

# Get metadata
metadata = broker.inference.get_service_metadata(provider_address)

# Get session token headers (NEW: no content needed!)
headers = broker.inference.get_request_headers(provider_address)

# Create client with Authorization header
client = OpenAI(
    base_url=metadata['endpoint'],
    api_key="not-used",  # Auth via headers
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

**Example providers (as of Feb 2026):**
- `qwen/qwen-2.5-7b-instruct` - Qwen 2.5 7B chat model
- `openai/gpt-oss-20b` - GPT-compatible 20B model
- `google/gemma-3-27b-it` - Gemma 3 27B instruction-tuned
- `qwen/qwen-image-edit-2511` - Image editing model

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
    broker.ledger.add_ledger("3")
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

### "401 Unauthorized" from provider
**Cause:** Invalid or expired session token.
**Fix:** Session tokens are auto-refreshed. If using API keys, check expiration.

### "Insufficient balance"
**Cause:** No funds in account or not transferred to provider.
**Fix:**
```python
# Add to main ledger (or create one with add_ledger("3"))
broker.ledger.deposit_fund("2")

# Transfer to provider (recommended minimum: 1 0G)
from zerog_py_sdk.utils import og_to_wei
broker.ledger.transfer_fund(provider, "inference", og_to_wei("1"))
```

### "Provider not found" or empty service list
**Cause:** Wrong network or no providers registered.
**Fix:** Ensure you're connected to the correct network (testnet vs mainnet).

```python
# Check which network you're on
chain_id = broker.web3.eth.chain_id
print(f"Chain ID: {chain_id}")  # 16602 = testnet, 16661 = mainnet
```

---

## Architecture Deep Dive

### Pure Python Implementation

The SDK is now 100% Python with native cryptographic implementations:

**Python Benefits:**
- ✅ No Node.js/npm dependency
- ✅ Rich ML/AI ecosystem
- ✅ Web3.py for Ethereum
- ✅ Easy HTTP requests
- ✅ Familiar to AI engineers

**Native Crypto:**
- ✅ Baby JubJub elliptic curve
- ✅ EdDSA signatures
- ✅ Pedersen hash

**Architecture:**
```
Python SDK
    │
    ├── Web3.py ────────> Blockchain (RPC)
    │                         │
    │                         ├── LedgerManager contract
    │                         └── InferenceServing contract
    │
    ├── Requests ───────> AI Provider (HTTP)
    │                         │
    │                         └── OpenAI-compatible API
    │
    └── crypto/ ────────> Native Python
                              │
                              ├── EdDSA signatures
                              └── Pedersen hash
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
0g_py_inference/
├── zerog_py_sdk/          # Main SDK package
│   ├── __init__.py        # Public API exports
│   ├── broker.py          # Broker implementation
│   ├── ledger.py          # Ledger manager
│   ├── inference.py       # Inference manager
│   ├── session.py         # Session token management (NEW)
│   ├── read_only.py       # Read-only broker (NEW)
│   ├── constants.py       # Network constants (NEW)
│   ├── extractors.py      # Service type extractors (NEW)
│   ├── cache.py           # Caching system (NEW)
│   ├── verifier.py        # Response verification (NEW)
│   ├── auth.py            # Authentication utilities
│   ├── models.py          # Data models
│   ├── exceptions.py      # Custom exceptions
│   ├── utils.py           # Helper functions
│   ├── crypto/            # Native Python crypto (NEW)
│   │   ├── eddsa.py       # EdDSA signatures
│   │   ├── pedersen.py    # Pedersen hash
│   │   └── baby_jubjub.py # Baby JubJub curve
│   └── contracts/         # Contract ABIs
│       └── abis.py        # Updated ABI definitions
├── test.py                # Working example script
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

### v0.2.0 (Latest - Feb 2026)
- ✅ **Session Token Auth**: New simplified authorization system (no content parameter needed)
- ✅ **No Node.js Dependency**: Native Python crypto implementation
- ✅ **Read-Only Broker**: Browse services without wallet connection
- ✅ **Multi-Network Support**: Mainnet/testnet with auto-detection
- ✅ **API Key Management**: Create persistent, revocable API keys
- ✅ **Response Verification**: Verify TEE-signed responses
- ✅ **Caching System**: Built-in caching for performance
- ✅ **Service Extractors**: Support for chatbot, image, speech services
- ✅ **Updated ABIs**: Compatible with latest 0G contracts

### v0.1.0
- ✅ Fixed endpoint URL - now correctly appends `/v1/proxy`
- ✅ Auto-creates accounts when acknowledging providers
- ✅ Improved error handling
- ✅ Added complete working example
- ✅ Full documentation with architecture details
