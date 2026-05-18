"""List all fine-tuning providers and the base models they support."""

import os
import sys

from zerog_py_sdk import create_broker

NETWORK = os.environ.get("NETWORK", "mainnet")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")


def main():
    if not PRIVATE_KEY:
        print('Set PRIVATE_KEY="0x..."')
        sys.exit(1)

    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    services = broker.fine_tuning.list_service()

    print(f"Fine-tuning providers on {NETWORK}: {len(services)}\n")
    for s in services:
        print(f"Provider:  {s.provider}")
        print(f"URL:       {s.url}")
        print(f"Models:    {s.models}")
        print(f"Price/tok: {s.price_per_token}")
        print()


if __name__ == "__main__":
    main()
