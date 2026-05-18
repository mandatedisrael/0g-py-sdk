"""
Check balance with 0G Whisper provider on MAINNET

This script checks:
- Your main account balance
- All provider sub-accounts with their balances
- Pending refunds

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python3 check_whisper_balance.py
"""

import os
import sys

from zerog_py_sdk import create_broker


# --- Configuration ---

PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "mainnet"  # MAINNET


def format_balance(wei_balance):
    """Convert Wei to 0G tokens (18 decimals)"""
    return wei_balance / 10**18


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        print('  export PRIVATE_KEY="0xYourPrivateKeyHere"')
        sys.exit(1)

    # Create broker connected to MAINNET
    print("Connecting to 0G MAINNET...")
    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    address = broker.get_address()
    print(f"✓ Your Address: {address}\n")

    # Check detailed ledger with provider balances
    print("=" * 70)
    print("ACCOUNT BALANCE DETAILS")
    print("=" * 70)
    try:
        detail = broker.ledger.get_ledger_with_detail()
        
        total = format_balance(detail.total_balance)
        available = format_balance(detail.available_balance)
        locked = format_balance(detail.locked_balance)
        
        print(f"\nMain Account:")
        print(f"  Total Balance:     {total:.6f} 0G")
        print(f"  Available:         {available:.6f} 0G")
        print(f"  Locked:            {locked:.6f} 0G")
        
        # Show inference providers
        if detail.inference_providers:
            print(f"\nInference Sub-Accounts ({len(detail.inference_providers)}):")
            for provider, balance, pending in detail.inference_providers:
                bal = format_balance(balance)
                pend = format_balance(pending)
                print(f"  Provider: {provider[:10]}...")
                print(f"    Balance:        {bal:.6f} 0G")
                if pending > 0:
                    print(f"    Pending Refund: {pend:.6f} 0G")
        else:
            print(f"\nInference Sub-Accounts: None")
        
        # Show fine-tuning providers
        if detail.fine_tuning_providers:
            print(f"\nFine-Tuning Sub-Accounts ({len(detail.fine_tuning_providers)}):")
            for provider, balance, pending in detail.fine_tuning_providers:
                bal = format_balance(balance)
                pend = format_balance(pending)
                print(f"  Provider: {provider[:10]}...")
                print(f"    Balance:        {bal:.6f} 0G")
                if pending > 0:
                    print(f"    Pending Refund: {pend:.6f} 0G")
        else:
            print(f"\nFine-Tuning Sub-Accounts: None")
            
    except Exception as e:
        print(f"✗ Error checking account details: {e}")

    # Show withdrawal instructions
    print("\n" + "=" * 70)
    print("WITHDRAWAL INSTRUCTIONS")
    print("=" * 70)
    print("""
To withdraw funds from a provider:

1. Request refund from provider sub-account:
   broker.ledger.retrieve_fund_from_provider('<PROVIDER_ADDRESS>')

2. Wait 24 hours for the security lock period

3. Call retrieve_fund_from_provider again to complete the refund

4. Once back in main account, withdraw to your wallet:
   broker.ledger.refund('<AMOUNT_IN_0G>')  # e.g., "0.5"

Example:
   # Withdraw from Whisper provider
   receipt = broker.ledger.retrieve_fund_from_provider('0x36aCffCE...')
   print(receipt)
""")

    print("Done!")


if __name__ == "__main__":
    main()
