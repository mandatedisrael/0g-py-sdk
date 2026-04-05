"""
List all providers and their service metadata on 0G testnet.
Displays each provider with pricing, model, verifiability, and health status.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from zerog_py_sdk.read_only import create_read_only_broker

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "https://evmrpc-testnet.0g.ai")

WEI_PER_OG = 10**18


def wei_to_og(wei_amount: int) -> str:
    """Convert wei to OG token amount with readable formatting."""
    og = wei_amount / WEI_PER_OG
    if og == 0:
        return "0 OG"
    if og < 0.000001:
        return f"{wei_amount} wei"
    return f"{og:.8f} OG"


def format_timestamp(ts: int) -> str:
    """Convert unix timestamp to human-readable date."""
    if ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def truncate(text: str, max_len: int = 50) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def main():
    print("=" * 80)
    print("  0G COMPUTE NETWORK — TESTNET PROVIDERS")
    print("=" * 80)
    print()

    broker = create_read_only_broker(rpc_url=RPC_URL)

    # Fetch all services with health details
    print("Fetching providers from on-chain + health API...")
    print()

    page_size = 50
    offset = 0
    all_services = []

    while True:
        batch = broker.list_service_with_detail(
            offset=offset, limit=page_size, include_unacknowledged=True
        )
        if not batch:
            break
        all_services.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    if not all_services:
        print("No providers found on testnet.")
        return

    # Group by model
    by_model = {}
    for svc in all_services:
        model = svc.model or "(unknown)"
        by_model.setdefault(model, []).append(svc)

    total = len(all_services)
    models = len(by_model)
    print(f"  Found {total} provider(s) across {models} model(s)")
    print()

    for model, services in sorted(by_model.items()):
        print("─" * 80)
        print(f"  MODEL: {model}  ({len(services)} provider(s))")
        print("─" * 80)

        for i, svc in enumerate(services, 1):
            addr = svc.provider
            short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr

            print(f"""
  [{i}] Provider: {addr}
      ├─ Service Type : {svc.service_type or 'N/A'}
      ├─ Endpoint     : {truncate(svc.url, 60)}
      ├─ Model        : {svc.model}
      ├─ Input Price  : {wei_to_og(svc.input_price)}  /token
      ├─ Output Price : {wei_to_og(svc.output_price)}  /token
      ├─ Verifiability: {svc.verifiability or 'None'}
      ├─ Updated      : {format_timestamp(svc.updated_at)}""", end="")

            if svc.health_metrics:
                hm = svc.health_metrics
                print(f"""
      ├─ Health Status: {hm.status.upper()}
      ├─ Uptime       : {hm.uptime:.1f}%
      ├─ Avg Response : {hm.avg_response_time:.0f} ms
      └─ Last Check   : {hm.last_check or 'N/A'}""")
            else:
                print(f"""
      └─ Health Status: NO DATA""")

        print()

    # Summary table
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print(f"  {'Model':<40} {'Providers':>10} {'Verified':>10}")
    print("  " + "─" * 62)
    for model, services in sorted(by_model.items()):
        verified = sum(1 for s in services if s.verifiability)
        print(f"  {truncate(model, 38):<40} {len(services):>10} {verified:>10}")
    print()
    print(f"  Total: {total} provider(s)")
    print("=" * 80)


if __name__ == "__main__":
    main()
