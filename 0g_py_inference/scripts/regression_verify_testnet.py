"""Regression test: decentralized verification still works on testnet.

Picks the first verifiable testnet chatbot, sends one chat, then calls
process_response. Expected: returns True (or None if not verifiable).
A False return means PR #195 broke the decentralized path.
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zerog_py_sdk import create_broker
from zerog_py_sdk.utils import og_to_wei

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
PRIVATE_KEY = os.environ["PRIVATE_KEY"]


def main() -> None:
    broker = create_broker(private_key=PRIVATE_KEY, network="testnet")
    print(f"address: {broker.get_address()}")

    services = [s for s in broker.inference.list_service() if s.service_type == "chatbot"]
    if not services:
        print("no chatbot providers on testnet")
        sys.exit(1)

    svc = services[0]
    provider = svc.provider
    print(f"provider: {provider}  model={svc.model}  verifiability={svc.verifiability!r}")

    try:
        ledger = broker.ledger.get_ledger()
        print(f"ledger available: {ledger.available / 10**18:.4f} A0GI")
    except Exception:
        print("creating ledger (3 A0GI)...")
        broker.ledger.add_ledger("3")

    try:
        broker.ledger.transfer_fund(provider, "inference", og_to_wei("1"))
        print("transferred 1 A0GI to provider")
    except Exception as e:
        print(f"transfer skipped: {e}")

    try:
        broker.inference.acknowledge_provider_signer(provider)
        print("provider acknowledged")
    except Exception as e:
        print(f"ack note: {e}")

    metadata = broker.inference.get_service_metadata(provider)
    endpoint, model = metadata["endpoint"], metadata["model"]
    print(f"endpoint: {endpoint}")

    messages = [{"role": "user", "content": "Reply with the single word: pong"}]
    headers = broker.inference.get_request_headers(provider, json.dumps(messages))
    resp = requests.post(
        f"{endpoint}/chat/completions",
        headers={"Content-Type": "application/json", **headers},
        json={"messages": messages, "model": model, "max_tokens": 32},
        timeout=60,
    )
    if not resp.ok:
        print(f"chat failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]
    chat_id = data.get("id")
    print(f"answer: {answer!r}")
    print(f"chat_id: {chat_id}")

    print("\n--- verification ---")
    result = broker.inference.process_response(provider, answer, chat_id)
    print(f"process_response -> {result}")
    if result is True:
        print("PASS: decentralized verification still works")
    elif result is None:
        print("SKIPPED: service not verifiable or no chat_id (not a regression)")
    else:
        print("FAIL: verification returned False — PR #195 may have broken the path")


if __name__ == "__main__":
    main()
