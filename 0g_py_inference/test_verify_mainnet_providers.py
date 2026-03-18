"""
Test: Verify All Mainnet Providers

This script:
1. Connects to 0G mainnet
2. Lists all available providers on mainnet
3. Runs verification on each provider
4. Shows detailed results for each provider
5. Generates a summary report
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zerog_py_sdk import create_broker


def format_address(addr: str, length: int = 10) -> str:
    """Shorten address for display"""
    if not addr:
        return "N/A"
    return f"{addr[:length]}...{addr[-4:]}"


def main():
    print("=" * 80)
    print("VERIFY ALL MAINNET PROVIDERS TEST")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create broker for MAINNET
    print("🌐 Connecting to 0G Mainnet...")
    print(f"   Network: mainnet")
    print(f"   RPC: https://evmrpc.0g.ai")
    print(f"   Chain ID: 16661")
    print()

    private_key = "0xc5509a5827e17a1cd286d85d5084bb8fdb37112cee4f7683508bd2ed422916fe"

    try:
        broker = create_broker(
            private_key=private_key,
            network="mainnet"  # ← MAINNET
        )
        print("✅ Connected to mainnet")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to mainnet: {e}")
        return

    # Get all providers
    print("🔍 Fetching all mainnet providers...")
    try:
        services = broker.inference.list_service()
    except Exception as e:
        print(f"❌ Failed to list services: {e}")
        return

    if not services:
        print("❌ No providers found on mainnet!")
        return

    print(f"✅ Found {len(services)} mainnet provider(s)")
    print()

    # Store results
    all_results = []
    verified_count = 0
    failed_count = 0

    # Test each provider
    for i, service in enumerate(services, 1):
        provider = service.provider

        print("=" * 80)
        print(f"MAINNET PROVIDER {i}/{len(services)}")
        print("=" * 80)

        # Show provider info
        print(f"Address:       {provider}")
        print(f"Model:         {service.model}")
        print(f"Service Type:  {service.service_type}")
        print(f"Verifiability: {service.verifiability}")
        print(f"URL:           {service.url}")
        print(f"Input Price:   {service.input_price} wei")
        print(f"Output Price:  {service.output_price} wei")
        print()

        # Run verification
        print(f"⟳ Running verification for {format_address(provider)}...")
        print()

        try:
            result = broker.inference.verify_service(
                provider,
                output_dir="./reports/mainnet"
            )

            # Store result
            provider_result = {
                "provider": provider,
                "model": service.model,
                "service_type": service.service_type,
                "verifiability": service.verifiability,
                "url": service.url,
                "input_price": service.input_price,
                "output_price": service.output_price,
                "verification": {
                    "is_valid": result["is_valid"],
                    "tee_signer": result.get("tee_signer"),
                    "signer_match": result.get("signer_match"),
                    "quote_available": result["quote_available"],
                    "attestation_verified": result.get("attestation_verified"),
                    "expected_signer": result.get("expected_signer"),
                    "errors": result.get("errors", [])
                },
                "timestamp": result["timestamp"]
            }
            all_results.append(provider_result)

            # Count results
            if result["is_valid"]:
                verified_count += 1
            else:
                failed_count += 1

            # Show result
            print()
            if result["is_valid"]:
                print("🎉 VERIFICATION RESULT: ✅ PASSED")
            else:
                print("⚠️  VERIFICATION RESULT: ❌ FAILED")
            print()

        except Exception as e:
            print(f"❌ Verification error: {e}")
            print()

            provider_result = {
                "provider": provider,
                "model": service.model,
                "service_type": service.service_type,
                "verifiability": service.verifiability,
                "url": service.url,
                "verification": {
                    "is_valid": False,
                    "error": str(e)
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            all_results.append(provider_result)
            failed_count += 1

    # ============================================================================
    # SUMMARY REPORT
    # ============================================================================

    print()
    print()
    print("=" * 80)
    print("MAINNET SUMMARY REPORT")
    print("=" * 80)
    print()

    # Overall stats
    print(f"Network:             MAINNET")
    print(f"Total Providers:     {len(services)}")
    print(f"✅ Verified:         {verified_count}")
    print(f"❌ Not Verified:     {failed_count}")
    if len(services) > 0:
        print(f"Success Rate:        {(verified_count/len(services)*100):.1f}%")
    print()

    # Detailed table
    print("=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print()

    # Table header
    print(f"{'#':<4} {'Provider':<20} {'Model':<30} {'Status':<12} {'TEE Signer':<20}")
    print("-" * 80)

    # Table rows
    for i, result in enumerate(all_results, 1):
        provider_short = format_address(result["provider"], 16)
        model_short = result["model"][:28] + "..." if len(result["model"]) > 28 else result["model"]
        status = "✅ VERIFIED" if result["verification"]["is_valid"] else "❌ FAILED"
        tee_signer = format_address(result["verification"].get("tee_signer", "N/A"), 16)

        print(f"{i:<4} {provider_short:<20} {model_short:<30} {status:<12} {tee_signer:<20}")

    print()

    # Show verification details
    print("=" * 80)
    print("VERIFICATION DETAILS")
    print("=" * 80)
    print()

    for i, result in enumerate(all_results, 1):
        print(f"Provider {i}: {result['model']}")
        print(f"  Address: {result['provider']}")
        print(f"  TEE Signer: {result['verification'].get('tee_signer', 'N/A')}")
        print(f"  Expected: {result['verification'].get('expected_signer', 'N/A')}")
        print(f"  Match: {result['verification'].get('signer_match', False)}")
        print(f"  Valid: {result['verification']['is_valid']}")
        print()

    # Show errors if any
    print("=" * 80)
    print("ERRORS (if any)")
    print("=" * 80)
    print()

    has_errors = False
    for i, result in enumerate(all_results, 1):
        errors = result["verification"].get("errors", [])
        error_msg = result["verification"].get("error")

        if errors or error_msg:
            has_errors = True
            print(f"Provider {i}: {format_address(result['provider'])}")
            print(f"  Model: {result['model']}")
            if error_msg:
                print(f"  Error: {error_msg}")
            for error in errors:
                print(f"  - {error}")
            print()

    if not has_errors:
        print("No errors! 🎉")
        print()

    # Save comprehensive report
    report_path = f"./reports/mainnet/mainnet_verification_{int(datetime.now().timestamp())}.json"
    try:
        os.makedirs("./reports/mainnet", exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump({
                "network": "mainnet",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(services),
                    "verified": verified_count,
                    "failed": failed_count,
                    "success_rate": round(verified_count/len(services)*100, 2) if len(services) > 0 else 0
                },
                "providers": all_results
            }, f, indent=2)

        print("=" * 80)
        print(f"📄 Full report saved: {report_path}")
        print("=" * 80)
    except Exception as e:
        print(f"⚠️  Could not save report: {e}")

    print()

    # Final summary
    print("=" * 80)
    print("MAINNET TEST COMPLETE")
    print("=" * 80)
    print()

    if verified_count == len(services):
        print("🎉 ALL MAINNET PROVIDERS VERIFIED! 100% success rate!")
    elif verified_count > 0:
        print(f"✅ {verified_count}/{len(services)} mainnet providers verified")
    else:
        print("⚠️  No mainnet providers verified")

    print()


if __name__ == "__main__":
    main()
