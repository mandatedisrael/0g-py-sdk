# Updated test_local.py
from zerog_py_sdk.utils import og_to_wei
from zerog_py_sdk import create_broker
from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

def test_broker_initialization():
    """Test broker creation"""
    print("Testing broker initialization...")
    
    broker = create_broker(
        private_key=os.getenv('PRIVATE_KEY'),
        rpc_url=os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')
    )
    
    print(f"✓ Broker initialized")
    print(f"✓ Address: {broker.get_address()}")
    return broker

def test_ledger_operations(broker):
    """Test ledger operations - NO PROVIDER NEEDED"""
    print("\nTesting ledger operations...")
    
    try:
        account = broker.ledger.get_ledger()  # No provider address!

        print(f"✓ Current balance: {account.balance } 0G")
        print(f"✓ Total balance: {account.total_balance } 0G")
        print(f"✓ Available: {account.available } 0G")
        print(f"Withdrawing 1.0 OG from ledger...")
        receipt = broker.ledger.retrieve_fund('inference')  # No provider address!
        print(f"✓ Withdrawal successful: {receipt['transaction_hash']}")
        print(f"✓ New balance: {broker.ledger.get_ledger().balance } 0G")
    except Exception as e:
        print(f"⚠ No existing ledger: {e}")
        print("  Creating new ledger with 0.01 OG...")
        
        # Create ledger - NO PROVIDER ADDRESS!
        # receipt = broker.ledger.add_ledger("0.01")
        # print(f"✓ Ledger created: {receipt['transaction_hash']}")

def test_list_services(broker):
    """Test service discovery"""
    print("\nTesting service discovery...")

    services = broker.inference.list_service()
    print(f"✓ Found {len(services)} services")

    for service in services:
        print("--------------------------------")
        print(f" {service} ")

    return services

def test_query_provider(broker):
    """Query a provider for Highest World Cup Holder (adjust as needed)"""


    print("\nQuerying provider for ' Highest World Cup Holder'...")

    # Get first available service
    services = broker.inference.list_service()
    if not services:
        print("❌ No services available")
        return None
    
    service = services[1]
    provider_address = service.provider

    print(f"✓ Using provider: {provider_address}")
    print(f"✓ Model: {service.model}")

    # Check balance to prevent insuffificient funds error
    try:
        account = broker.ledger.get_ledger()
        print(f"✓ Main ledger balance: {account.balance} OG")
        print(f"✓ Total balance: {account.total_balance} OG")

        # Add funds if balance is too low
        if account.balance < 0.1:
            print("  Balance too low, adding 2 OG...")
            receipt = broker.ledger.deposit_fund("2")
            print(f"✓ Added 2 OG to ledger: {receipt['transaction_hash']}")

            # Check new balance
            account = broker.ledger.get_ledger()
            print(f"✓ New balance: {account.balance} OG")
    except Exception as e:
        print(f"⚠ Could not check balance: {e}")

    # Acknowledge provider if not already done
    try:
        print("  Acknowledging provider...")
        broker.inference.acknowledge_provider_signer(provider_address)
        print("✓ Provider acknowledged")
    except Exception as e:
        print(f"  Already acknowledged or error: {e}")

    # Get service metadata
    metadata = broker.inference.get_service_metadata(provider_address)
    endpoint = metadata['endpoint']
    model = metadata['model']

    # Generate auth headers
    question = "Who owns the largest number of football World Cups?"
    messages = [{"role": "user", "content": question}]

    headers = broker.inference.get_request_headers(
        provider_address,
        json.dumps(messages)
    )

    # Make inference request
    print(f"✓ Sending request to {endpoint}...")
    print(f"  Model: {model}")
    print(f"  Headers: {list(headers.keys())}")

    response = requests.post(
        f"{endpoint}/chat/completions",
        headers={
            "Content-Type": "application/json",
            **headers
        },
        json={
            "messages": messages,
            "model": model
        }
    )

    print(f"  Response status: {response.status_code}")
    print(f"  Response headers: {dict(response.headers)}")

    if response.status_code == 200:
        data = response.json()
        answer = data['choices'][0]['message']['content']

        print(f"\n{'='*50}")
        print(f"Question: {question}")
        print(f"Answer: {answer}")
        print(f"{'='*50}\n")

        return {
            'answer': answer,
            'chat_id': data.get('id'),
            'provider': provider_address
        }
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

if __name__ == "__main__":
    try:
        broker = test_broker_initialization()
        test_query_provider(broker)

        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()