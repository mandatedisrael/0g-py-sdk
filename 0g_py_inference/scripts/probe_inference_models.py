"""Probe each inference provider's /v1/models endpoint to see what's actually loaded."""

import os
import sys
import json
import urllib.request
import urllib.error

from zerog_py_sdk import create_broker

NETWORK = os.environ.get("NETWORK", "mainnet")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
TARGETS = ["qwen2.5-0.5b", "qwen3-32b"]


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    if not PRIVATE_KEY:
        print('Set PRIVATE_KEY="0x..."')
        sys.exit(1)

    broker = create_broker(private_key=PRIVATE_KEY, network=NETWORK)
    services = broker.inference.list_service()

    print(f"Probing {len(services)} inference providers for Qwen2.5-0.5B-Instruct / Qwen3-32B\n")

    matches = []
    for s in services:
        url = f"{s.url.rstrip('/')}/v1/models"
        try:
            data = fetch(url)
            ids = [m.get("id", "") for m in data.get("data", [])]
        except Exception as e:
            print(f"  {s.provider}  advertised={s.model!r}  ERROR: {type(e).__name__}: {e}")
            continue

        match = any(any(t in mid.lower() for t in TARGETS) for mid in ids)
        marker = "✅" if match else "  "
        print(f"{marker} {s.provider}  advertised={s.model!r}")
        for mid in ids:
            print(f"     - {mid}")
        if match:
            matches.append((s.provider, ids))

    print()
    if matches:
        print("Providers serving a fine-tuning base model:")
        for p, ids in matches:
            print(f"  {p}  →  {ids}")
    else:
        print("CONFIRMED: no inference provider serves Qwen2.5-0.5B-Instruct or Qwen3-32B.")


if __name__ == "__main__":
    main()
