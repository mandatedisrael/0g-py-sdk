"""
0G Account Setup Guide

This script explains and helps you set up your 0G account for Whisper provider.

Account Structure:
  1. MAIN LEDGER (your account on 0G) - where you deposit/withdraw
  2. PROVIDER SUB-ACCOUNTS (per provider) - where funds are locked for services

Flow:
  Wallet → [deposit] → Main Ledger → [transfer] → Whisper Sub-Account → [usage]

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python3 setup_account.py
"""

import os
import sys

from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei


PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "mainnet"

# 0G Whisper provider (speech-to-text)
WHISPER_PROVIDER = "0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517"


def format_balance(wei_balance):
    """Convert Wei to 0G tokens (18 decimals)"""
    return wei_balance / 10**18


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        sys.exit(1)

    print("=" * 70)
    print("0G ACCOUNT SETUP FOR WHISPER PROVIDER")
    print("=" * 70)

    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    address = broker.get_address()
    print(f"\n✓ Your Address: {address}")

    # Step 1: Check if main ledger exists
    print("\n" + "-" * 70)
    print("STEP 1: Check Main Ledger Account")
    print("-" * 70)
    main_ledger_exists = False
    try:
        ledger = broker.ledger.get_ledger()
        main_ledger_exists = True
        total = format_balance(ledger.total_balance)
        available = format_balance(ledger.balance)
        locked = format_balance(ledger.locked)
        print(f"✓ Main Ledger Account EXISTS")
        print(f"  Total:     {total:.6f} 0G")
        print(f"  Available: {available:.6f} 0G")
        print(f"  Locked:    {locked:.6f} 0G (in provider sub-accounts)")
    except Exception as e:
        print(f"✗ Main Ledger Account DOES NOT EXIST")
        print(f"  Need to create it with: broker.ledger.add_ledger('amount')")

    # Step 2: Create main ledger if needed
    if not main_ledger_exists:
        print("\n" + "-" * 70)
        print("STEP 2: Create Main Ledger Account (Optional Demo)")
        print("-" * 70)
        print("""
To create your main ledger and deposit 1.0 0G:

    broker.ledger.add_ledger('3')

This will:
- Create a main ledger account linked to your address
- Deposit 1.0 0G to it
- Allow you to transfer funds to providers
""")

    # Step 3: Check provider sub-accounts
    print("\n" + "-" * 70)
    print("STEP 3: Check Provider Sub-Accounts")
    print("-" * 70)
    if main_ledger_exists:
        try:
            providers = broker.ledger.get_providers_with_balance("inference")
            if providers:
                print(f"✓ Found {len(providers)} inference provider(s):")
                for p in providers:
                    print(f"  - {p}")
            else:
                print(f"✗ No inference providers found")
                print(f"  To transfer funds to Whisper provider:")
                print(f"  broker.ledger.transfer_fund('{WHISPER_PROVIDER}', 'inference', og_to_wei('1'))")
        except Exception as e:
            print(f"✗ Error: {e}")

    # Step 4: Summary and next steps
    print("\n" + "=" * 70)
    print("ACCOUNT TYPES SUMMARY")
    print("=" * 70)
    print("""
┌─ YOUR WALLET (0xE74096f8...) ─────────────────────────────┐
│ Private Key: 0x5c5f5927...                                 │
│                                                             │
│  [deposit] ─────────────────────────────────────────────▶  │
│                                                             │
│  ┌─ MAIN LEDGER ACCOUNT (on LedgerManager) ──────────────┐ │
│  │ Your balance here                                     │ │
│  │ Total, Available, Locked                             │ │
│  │                                                       │ │
│  │  [transfer] ──────────────────────────────────────▶  │ │
│  │                                                       │ │
│  │  ┌─ WHISPER SUB-ACCOUNT (Provider) ─────────────┐   │ │
│  │  │ Your balance with Whisper provider           │   │ │
│  │  │ Used for speech-to-text inference calls      │   │ │
│  │  └─────────────────────────────────────────────┘    │ │
│  │                                                       │ │
│  │  ┌─ CHATBOT SUB-ACCOUNT (Provider) ──────────────┐   │ │
│  │  │ Your balance with ChatBot provider           │   │ │
│  │  │ Used for chat inference calls                │   │ │
│  │  └─────────────────────────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

IMPORTANT DISTINCTIONS:

Main Ledger Account:
  - ONE per user (your address)
  - Used to deposit/withdraw from your wallet
  - Manages funds across all providers

Provider Sub-Accounts:
  - ONE per provider (Whisper, ChatBot, etc.)
  - Funds locked for that specific provider
  - Only that provider can deduct from it
  - Requires 24-hour refund lock for withdrawal

WORKFLOW:

1. Create Main Ledger (if not exists):
   broker.ledger.add_ledger('3')

2. Transfer to Whisper Sub-Account:
   from zerog_py_sdk.utils import og_to_wei
   broker.ledger.transfer_fund('0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517', 
                               'inference', 
                               og_to_wei('1'))

3. Check Whisper Sub-Account Balance:
   detail = broker.ledger.get_ledger_with_detail()
   for provider, balance, pending in detail.inference_providers:
       if provider == '0x36aCffCEa3CCe07cAdd1740Ad992dB16Ab324517':
           print(f"Whisper Balance: {balance / 10**18:.6f} 0G")

4. Use Whisper Service (will deduct from sub-account)
   headers = broker.inference.get_request_headers('0x36aCffCEa3...')
   # Make inference requests...

5. Withdraw (if needed):
   # Step 1: Request refund (starts 24-hour lock)
   broker.ledger.retrieve_fund_from_provider('0x36aCffCEa3...', 'inference')
   
   # Step 2: Wait 24 hours
   
   # Step 3: Call again to complete refund (moves to main account)
   broker.ledger.retrieve_fund_from_provider('0x36aCffCEa3...', 'inference')
   
   # Step 4: Withdraw from main account to wallet
   broker.ledger.refund('0.5')
""")

    print("\nDone!")


if __name__ == "__main__":
    main()
