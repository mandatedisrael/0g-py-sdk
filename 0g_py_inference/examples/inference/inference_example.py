"""
0G Inference SDK Example

This script demonstrates the full inference workflow:
1. Create broker and connect to testnet
2. Discover available AI services
3. Fund account (if needed)
4. Acknowledge provider TEE signer
5. Transfer funds to provider sub-account
6. Get authenticated headers
7. Make an inference request

Prerequisites:
    pip install 0g-inference-sdk

Usage:
    export PRIVATE_KEY="0xYourPrivateKeyHere"
    python inference_example.py
"""

import os
import sys
import json

import requests

from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei


# --- Configuration ---

PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
NETWORK = "testnet"

# Amount to deposit/transfer (in A0GI)
DEPOSIT_AMOUNT = "2"
TRANSFER_AMOUNT = "0.5"


def main():
    if not PRIVATE_KEY:
        print("Error: Set PRIVATE_KEY environment variable")
        print('  export PRIVATE_KEY="0xYourPrivateKeyHere"')
        sys.exit(1)

    # Step 1: Create broker
    print("Step 1: Creating broker...")
    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    print(f"  Address: {broker.get_address()}")

    # Step 2: Discover available AI services
    print("\nStep 2: Listing inference services...")
    services = broker.inference.list_service()
    if not services:
        print("  No inference services available!")
        sys.exit(1)

    # Filter for chatbot services
    chatbot_services = [s for s in services if s.service_type == "chatbot"]
    print(f"  Found {len(chatbot_services)} chatbot services:")
    for s in chatbot_services:
        print(f"    - {s.model} ({s.provider[:10]}...)")

    # Pick the first chatbot provider
    provider_address = chatbot_services[0].provider
    print(f"\n  Using provider: {provider_address}")

    # Step 3: Check/fund ledger
    print("\nStep 3: Checking ledger balance...")
    ledger_exists = False
    try:
        ledger = broker.ledger.get_ledger()
        ledger_exists = True
        available = ledger.available / 10**18
        total = ledger.total_balance / 10**18
        print(f"  Ledger: available={available:.6f}, total={total:.6f} A0GI")

        if available < 0.1:
            print(f"  Low balance, depositing {DEPOSIT_AMOUNT} A0GI...")
            broker.ledger.deposit_fund(DEPOSIT_AMOUNT)
            print("  Deposit successful!")
    except Exception:
        if not ledger_exists:
            print(f"  No ledger found, creating with {DEPOSIT_AMOUNT} A0GI...")
            broker.ledger.add_ledger(DEPOSIT_AMOUNT)
            print("  Ledger created!")

    # Step 4: Transfer funds to provider sub-account
    print("\nStep 4: Transferring funds to provider...")
    try:
        broker.ledger.transfer_fund(
            provider_address, "inference-v1.0", og_to_wei(TRANSFER_AMOUNT)
        )
        print(f"  Transferred {TRANSFER_AMOUNT} A0GI to provider")
    except Exception as e:
        print(f"  Transfer note: {e}")
        print("  (May already have sufficient balance)")

    # Step 5: Acknowledge provider TEE signer
    print("\nStep 5: Acknowledging provider TEE signer...")
    try:
        broker.inference.acknowledge_provider_signer(provider_address)
        print("  Provider acknowledged!")
    except Exception as e:
        print(f"  Acknowledge note: {e}")

    # Step 6: Get service metadata (endpoint + model)
    print("\nStep 6: Getting service metadata...")
    metadata = broker.inference.get_service_metadata(provider_address)
    endpoint = metadata["endpoint"]
    model = metadata["model"]
    print(f"  Endpoint: {endpoint}")
    print(f"  Model: {model}")

    # Step 7: Get authentication headers
    print("\nStep 7: Getting auth headers...")
    headers = broker.inference.get_request_headers(provider_address)
    print("  Got session token!")

    # Step 8: Make inference request
    print("\nStep 8: Sending inference request...")
    question = "What is the name of Elon Musk's first company?"

    response = requests.post(
        f"{endpoint}/chat/completions",
        headers={"Content-Type": "application/json", **headers},
        json={
            "messages": [{"role": "user", "content": question}],
            "model": model,
            "max_tokens": 512,
        },
        timeout=60,
    )

    if response.ok:
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"\n  Question: {question}")
        print(f"  Answer: {answer}")
        print(f"\n  Tokens used: {usage.get('total_tokens', 'N/A')}")
    else:
        print(f"  Error: {response.status_code} - {response.text}")

    print("\nDone!")


if __name__ == "__main__":
    main()
