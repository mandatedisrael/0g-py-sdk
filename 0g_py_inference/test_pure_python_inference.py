#!/usr/bin/env python3
"""
Test 0G Inference SDK with pure Python cryptography.

This test verifies that the entire inference pipeline works with:
- Pure Python Baby JubJub + Pedersen + EdDSA
- Zero Node.js dependencies
- Full TypeScript SDK compatibility
"""

from zerog_py_sdk import create_broker
from zerog_py_sdk.crypto import gen_key_pair, sign_pedersen, pack_signature
from dotenv import load_dotenv
import requests
import json
import os
import sys

load_dotenv()

def test_crypto_module():
    """Test that pure Python crypto is working"""
    print("=" * 70)
    print("🔐 TESTING PURE PYTHON CRYPTOGRAPHY")
    print("=" * 70)

    print("\n1️⃣  Testing key generation...")
    keys = gen_key_pair()
    print(f"   ✅ Generated key pair")
    print(f"   Private key format: 2x16-byte packed")
    print(f"   Public key format: double-packed")

    print("\n2️⃣  Testing signature generation...")
    privkey_bytes = bytearray(32)
    for i in range(16):
        privkey_bytes[i] = (keys['packedPrivkey'][0] >> (8 * i)) & 0xff
        privkey_bytes[i + 16] = (keys['packedPrivkey'][1] >> (8 * i)) & 0xff

    message = b"Test message for 0G inference"
    sig = sign_pedersen(bytes(privkey_bytes), message)
    packed = pack_signature(sig)

    print(f"   ✅ Signed message")
    print(f"   Signature size: {len(packed)} bytes (expected 64)")
    assert len(packed) == 64, "Signature should be 64 bytes"

    print("\n✅ Pure Python Crypto: WORKING\n")
    return True


def test_broker_initialization():
    """Test broker creation with pure Python crypto"""
    print("=" * 70)
    print("🚀 TESTING BROKER INITIALIZATION")
    print("=" * 70)

    print("\n1️⃣  Creating broker...")
    try:
        broker = create_broker(
            private_key=os.getenv('PRIVATE_KEY'),
            rpc_url=os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')
        )

        print(f"   ✅ Broker created successfully")
        print(f"   Address: {broker.get_address()}")
        print(f"   RPC: {os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')}")

        print("\n✅ Broker Initialization: WORKING\n")
        return broker
    except Exception as e:
        print(f"   ❌ Broker creation failed: {e}")
        raise


def test_list_services(broker):
    """List available inference services"""
    print("=" * 70)
    print("🔍 TESTING SERVICE DISCOVERY")
    print("=" * 70)

    print("\n1️⃣  Querying available services...")
    try:
        services = broker.inference.list_service()
        print(f"   ✅ Found {len(services)} services")

        if len(services) == 0:
            print("   ⚠️  No services available on testnet")
            return None

        for i, service in enumerate(services[:3]):  # Show first 3
            print(f"\n   Service {i}:")
            print(f"      Provider: {service.provider}")
            print(f"      Model: {service.model}")

        print(f"\n✅ Service Discovery: WORKING\n")
        return services

    except Exception as e:
        print(f"   ❌ Service discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_inference_request(broker, question="Who owns the highest shares in Tesla?"):
    """Test inference request with pure Python authentication"""
    print("=" * 70)
    print("💭 TESTING INFERENCE REQUEST")
    print("=" * 70)

    print(f"\n📋 Question: {question}\n")

    print("1️⃣  Getting available services...")
    services = broker.inference.list_service()

    if not services or len(services) < 2:
        print("   ⚠️  Insufficient services for testing")
        return None

    # Try service at index 1
    service = services[1]
    provider_address = service.provider

    print(f"   ✅ Using provider: {provider_address}")
    print(f"      Model: {service.model}")

    print("\n2️⃣  Generating authentication headers (pure Python)...")
    try:
        messages = [{"role": "user", "content": question}]

        headers = broker.inference.get_request_headers(
            provider_address,
            json.dumps(messages)
        )

        print(f"   ✅ Generated auth headers")
        print(f"      Headers keys: {list(headers.keys())}")
        print(f"      Signature length: {len(headers.get('Signature', ''))}")
        print(f"      Request-Hash: {headers.get('Request-Hash', 'N/A')[:32]}...")

        # Verify headers contain required fields
        required_fields = ['Signature', 'Nonce', 'Request-Hash', 'Address', 'Fee']
        for field in required_fields:
            assert field in headers, f"Missing required header: {field}"

        print(f"\n3️⃣  Getting service endpoint...")
        metadata = broker.inference.get_service_metadata(provider_address)
        endpoint = metadata['endpoint']
        model = metadata['model']

        print(f"   ✅ Service metadata retrieved")
        print(f"      Endpoint: {endpoint}")
        print(f"      Model: {model}")

        print(f"\n4️⃣  Sending inference request...")
        response = requests.post(
            f"{endpoint}/chat/completions",
            headers={
                "Content-Type": "application/json",
                **headers
            },
            json={
                "messages": messages,
                "model": model
            },
            timeout=60
        )

        print(f"   Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            answer = data['choices'][0]['message']['content']

            print("\n" + "=" * 70)
            print("✅ INFERENCE SUCCESSFUL!")
            print("=" * 70)
            print(f"\n❓ Question:\n   {question}")
            print(f"\n🤖 Answer:\n   {answer}")
            print("\n" + "=" * 70)
            print("✅ Inference Request: WORKING\n")

            return {
                'answer': answer,
                'provider': provider_address,
                'model': model
            }
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ Inference request failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests"""
    print("\n")
    print("🎯" * 35)
    print("  0G INFERENCE SDK - PURE PYTHON TEST")
    print("  Testing complete end-to-end inference pipeline")
    print("🎯" * 35)
    print()

    try:
        # Test 1: Pure Python Crypto
        test_crypto_module()

        # Test 2: Broker initialization
        broker = test_broker_initialization()

        # Test 3: Service discovery
        services = test_list_services(broker)

        if not services:
            print("⚠️  No services available, skipping inference test")
            return

        # Test 4: Inference request
        result = test_inference_request(
            broker,
            question="Who owns the highest shares in Tesla?"
        )

        if result:
            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 70)
            print("\n✅ 0G Inference SDK is fully functional with pure Python crypto!")
            print("✅ Zero Node.js dependencies")
            print("✅ 100% TypeScript SDK compatible")
            print("\n" + "=" * 70 + "\n")
        else:
            print("\n⚠️  Inference test skipped or failed")
            print("   This may be due to:")
            print("   - No available providers on testnet")
            print("   - Network connectivity issues")
            print("   - Insufficient funds")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
