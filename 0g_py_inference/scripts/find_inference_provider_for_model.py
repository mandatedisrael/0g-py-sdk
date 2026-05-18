"""List inference providers and flag those serving a target base model."""

import os
import sys

from zerog_py_sdk import create_broker

TARGET_MODEL = os.environ.get("TARGET_MODEL", "Qwen2.5-0.5B-Instruct")
NETWORK = os.environ.get("NETWORK", "mainnet")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")


def main():
    if not PRIVATE_KEY:
        print('Set PRIVATE_KEY="0x..." (read-only call, but broker requires a signer).')
        sys.exit(1)

    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    services = broker.inference.list_service()

    print(f"Looking for inference providers serving: {TARGET_MODEL!r}")
    print(f"Total inference services: {len(services)}\n")

    matches = []
    for s in services:
        marker = "  "
        if TARGET_MODEL.lower() in (s.model or "").lower():
            marker = "✅"
            matches.append(s)
        print(
            f"{marker} {s.provider}  model={s.model!r}  "
            f"verif={s.verifiability or 'none'}  url={s.url}"
        )

    print()
    if matches:
        print(f"Found {len(matches)} provider(s) serving {TARGET_MODEL}:")
        for m in matches:
            print(f"  INFERENCE_PROVIDER_ADDRESS={m.provider}")
    else:
        print(
            f"No inference provider serves {TARGET_MODEL!r}. "
            "Pick a different base model for fine-tuning, or wait for a "
            "matching inference provider."
        )


if __name__ == "__main__":
    main()
