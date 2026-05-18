"""List inference providers on both testnet and mainnet, flagging ProviderType."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zerog_py_sdk import create_broker
from zerog_py_sdk.models import AdditionalInfo

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PRIVATE_KEY = os.environ["PRIVATE_KEY"]


def show(network: str) -> None:
    print(f"\n=== {network.upper()} ===")
    try:
        broker = create_broker(private_key=PRIVATE_KEY, network=network)
        services = broker.inference.list_service()
    except Exception as e:
        print(f"  error: {e}")
        return

    if not services:
        print("  no services")
        return

    centralized = 0
    for s in services:
        raw = getattr(s, "additional_info", "") or ""
        info = AdditionalInfo.from_json(raw) if raw else AdditionalInfo()
        tag = info.provider_type
        if tag == "centralized":
            centralized += 1
        print(
            f"  [{tag:13s}] {s.provider}  "
            f"type={s.service_type}  model={s.model}  "
            f"sep={info.target_separated}"
        )
    print(f"  total={len(services)}  centralized={centralized}")


if __name__ == "__main__":
    show("testnet")
    show("mainnet")
