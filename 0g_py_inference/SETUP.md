# Quick Setup Guide

Get up and running with the 0G Python SDK in 5 minutes.

## Prerequisites

- Python 3.8+
- Node.js 16.x+
- Git

## Step-by-Step Setup

### 1. Clone and Enter Directory

```bash
git clone https://github.com/yourusername/og-py-sdk.git
cd og-py-sdk
```

### 2. Install Node.js Dependencies

```bash
npm install -g circomlibjs
```

### 3. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

Create `.env` file:

```bash
PRIVATE_KEY=your_wallet_private_key_without_0x
RPC_URL=https://evmrpc-testnet.0g.ai
```

### 6. Get Testnet Tokens

1. Run: `python3 -c "from zerog_py_sdk import create_broker; import os; from dotenv import load_dotenv; load_dotenv(); print(create_broker(os.getenv('PRIVATE_KEY'), os.getenv('RPC_URL')).get_address())"`
2. Copy your address
3. Visit: https://faucet.0g.ai
4. Request tokens

### 7. Run the Test

```bash
python3 test.py
```

**Expected Output:**
```
✓ Broker initialized
✓ Found 4 services
✓ Provider acknowledged
✓ Transferred funds

Answer: 2 + 2 = 4.

✅ All tests passed!
```

## Troubleshooting

### "Module not found: web3"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "circomlibjs not found"
```bash
npm install -g circomlibjs
```

### "403 Forbidden" from provider
Make sure you:
1. Have funds: `broker.ledger.get_ledger()`
2. Acknowledged provider: `broker.inference.acknowledge_provider_signer(provider)`
3. Transferred funds: `broker.ledger.transfer_fund(provider, "inference", og_to_wei("0.5"))`

## Next Steps

- Check `test.py` for a complete working example
- Read `README.md` for detailed architecture documentation
- Explore `zerog_py_sdk/` to understand the implementation

## Need Help?

- Discord: https://discord.gg/0glabs
- Docs: https://docs.0g.ai/
