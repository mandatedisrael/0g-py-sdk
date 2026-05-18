"""
Diagnostic script to check 0G MAINNET account status

This helps identify:
- Whether you have a ledger account
- Whether you have deposited funds
- Your wallet balance
- Available providers

Prerequisites:
    pip install 0g-inference-sdk web3

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python3 diagnose_account.py
"""

import os
import sys
from web3 import Web3

from zerog_py_sdk import create_broker


# --- Configuration ---

PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "mainnet"
RPC_URL = "https://evmrpc-mainnet.0g.ai"  # MAINNET RPC


def format_balance(wei_balance):
    """Convert Wei to 0G tokens (18 decimals)"""
    return wei_balance / 10**18


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        sys.exit(1)

    # Create broker and web3 instance
    print("=" * 70)
    print("0G MAINNET ACCOUNT DIAGNOSTIC")
    print("=" * 70)
    
    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    address = broker.get_address()
    print(f"\n✓ Your Address: {address}")

    # Check wallet balance on chain
    print("\n" + "-" * 70)
    print("1. WALLET BALANCE")
    print("-" * 70)
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            print("✗ Cannot connect to RPC")
        else:
            balance_wei = w3.eth.get_balance(address)
            balance_0g = format_balance(balance_wei)
            print(f"✓ Wallet Balance: {balance_0g:.6f} 0G")
            if balance_0g < 0.1:
                print("  ⚠ Warning: Low balance for gas fees")
    except Exception as e:
        print(f"✗ Error checking wallet: {e}")

    # Check if ledger account exists
    print("\n" + "-" * 70)
    print("2. LEDGER ACCOUNT STATUS")
    print("-" * 70)
    try:
        ledger = broker.ledger.get_ledger()
        print(f"✓ Ledger exists!")
        print(f"  Total: {format_balance(ledger.total_balance):.6f} 0G")
        print(f"  Available: {format_balance(ledger.balance):.6f} 0G")
        print(f"  Locked: {format_balance(ledger.locked):.6f} 0G")
    except Exception as e:
        print(f"✗ No ledger account found")
        print(f"  Error: {type(e).__name__}")
        print(f"  Next step: Create ledger with broker.ledger.add_ledger('amount')")

    # List available providers
    print("\n" + "-" * 70)
    print("3. AVAILABLE PROVIDERS")
    print("-" * 70)
    try:
        services = broker.inference.list_service()
        print(f"✓ Found {len(services)} services available")
        
        # Group by type
        service_types = {}
        for s in services:
            if s.service_type not in service_types:
                service_types[s.service_type] = []
            service_types[s.service_type].append(s)
        
        for stype, slist in service_types.items():
            print(f"\n  {stype.upper()} ({len(slist)}):")
            for s in slist[:3]:  # Show first 3
                print(f"    - Model: {s.model}")
                print(f"      Provider: {s.provider}")
    except Exception as e:
        print(f"✗ Error listing services: {e}")

    # Check for providers with balance
    print("\n" + "-" * 70)
    print("4. YOUR PROVIDER SUB-ACCOUNTS")
    print("-" * 70)
    try:
        providers = broker.ledger.get_providers_with_balance("inference")
        if providers:
            print(f"✓ You have {len(providers)} inference provider sub-account(s):")
            for provider in providers:
                print(f"  - {provider}")
        else:
            print("✗ No inference provider sub-accounts")
            print("  You need to transfer funds from your main account to a provider")
    except Exception as e:
        print(f"✗ Error checking providers: {e}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
If you haven't created an account yet:
  1. Create ledger: broker.ledger.add_ledger('3')
  2. Transfer to provider: 
     from zerog_py_sdk.utils import og_to_wei
     broker.ledger.transfer_fund('provider_address', 'inference', og_to_wei('1'))
  3. Check balance: broker.ledger.get_ledger()

If you already have funds in a provider:
  You should see it in "YOUR PROVIDER SUB-ACCOUNTS" above
""")

    print("Done!")


if __name__ == "__main__":
    main()
