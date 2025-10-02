from zerog_py_sdk import create_broker
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_full_inference_request():
    """Complete workflow: get provider, acknowledge, make inference request"""
    
    # Initialize broker
    broker = create_broker(
        private_key=os.getenv('PRIVATE_KEY'),
        rpc_url=os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')
    )
    
    print("=== Getting first provider ===")
    services = broker.inference.list_service()
    first_service = services[1]
    provider_address = first_service.provider
    
    print(f"Provider: {provider_address}")
    print(f"Model: {first_service.model}")
    
    print("\n=== Acknowledging provider ===")
    try:
        broker.ledger.transfer_fund(provider_address, "inference", 0)
        broker.inference.acknowledge_provider_signer(provider_address)
        print("Provider acknowledged")
    except Exception as e:
        print(f"Already acknowledged or error: {e}")
    
    print("\n=== Getting service metadata ===")
    metadata = broker.inference.get_service_metadata(provider_address)
    endpoint = metadata['endpoint']
    model = metadata['model']
    
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model}")
    
    print("\n=== Generating auth headers ===")
    question = "What is 89+11 and what equation is this?"
    messages = [{"role": "user", "content": question}]
    
    headers = broker.inference.get_request_headers(
        provider_address,
        json.dumps(messages)
    )
    
    print("Headers generated")
    
    print("\n=== Making inference request ===")
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
    
    if response.status_code == 200:
        data = response.json()
        answer = data['choices'][0]['message']['content']
        chat_id = data['id']
        
        print(f"Status: {response.status_code}")
        print(f"Answer: {answer}")
        print(f"Chat ID: {chat_id}")
        
        return {
            'answer': answer,
            'chat_id': chat_id,
            'full_response': data
        }
    else:
        print(f"Request failed: {response.status_code}")
        print(f"Error: {response}")
        return None

if __name__ == "__main__":
    result = test_full_inference_request()
    if result:
        print("\n✅ -- Inference request successful! -- ✅")
    else:
        print("\n❌ Inference request failed.")