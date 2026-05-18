"""
Check balance and explore providers on 0G MAINNET

This script checks your ledger balance and lists available 0G whisper providers.

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python3 check_balance_mainnet.py
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
    address = broker.get_address()
    print(f"✓ Your Address: {address}\n")

    # List available inference services
    print("Discovering available AI services...")
    try:
        services = broker.inference.list_service()
        if not services:
            print("  No inference services available!")
        else:
            print(f"  Found {len(services)} services:")
            
            # Group by service type
            service_types = {}
            for s in services:
                stype = s.service_type
                if stype not in service_types:
                    service_types[stype] = []
                service_types[stype].append(s)
            
            for stype, slist in service_types.items():
                print(f"\n  {stype.upper()} Services ({len(slist)}):")
                for s in slist[:5]:  # Show first 5
                    print(f"    - Model: {s.model}")
                    print(f"      Provider: {s.provider[:10]}...")
                    print(f"      Type: {s.service_type}")
                if len(slist) > 5:
                    print(f"    ... and {len(slist) - 5} more")
    except Exception as e:
        print(f"  Error listing services: {e}")

    # Check ledger balance
    print("\n" + "="*60)
    print("Checking ledger balance...")
    try:
        ledger = broker.ledger.get_ledger()
        available = ledger.available / 10**18
        total = ledger.total_balance / 10**18
        print(f"✓ Ledger exists!")
        print(f"  Available: {available:.6f} A0GI")
        print(f"  Total: {total:.6f} A0GI")
    except Exception as e:
        print(f"✗ No ledger found for your address")
        print(f"  Error: {e}")
        print("\n  To create a ledger and deposit funds, you can run:")
        print("    broker.ledger.add_ledger('amount_in_A0GI')")
        print("    Example: broker.ledger.add_ledger('3')  # Deposit 3 A0GI (contract minimum)")

    print("\nDone!")


if __name__ == "__main__":
    main()
