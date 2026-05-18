"""
Check balance with 0G Whisper Provider on MAINNET

This script checks your ledger balance on the 0G MAINNET.

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python check_balance.py
"""

import os
import sys

from zerog_py_sdk import create_broker


# --- Configuration ---

PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "mainnet"  # MAINNET


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        print('  export PRIVATE_KEY="0xYourPrivateKeyHere"')
        sys.exit(1)

    # Create broker connected to MAINNET
    print("Connecting to 0G MAINNET...")
    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    print(f"Address: {broker.get_address()}")

    # Check balance
    print("\nChecking ledger balance...")
    try:
        ledger = broker.ledger.get_ledger()
        available = ledger.available / 10**18
        total = ledger.total_balance / 10**18
        print(f"✓ Ledger Balance:")
        print(f"  Available: {available:.6f} A0GI")
        print(f"  Total: {total:.6f} A0GI")
    except Exception as e:
        print(f"Error checking balance: {e}")
        print("  Note: You may not have a ledger created yet.")
        sys.exit(1)

    print("\nDone!")


if __name__ == "__main__":
    main()
