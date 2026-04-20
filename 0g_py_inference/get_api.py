import os
from dotenv import load_dotenv
from zerog_py_sdk import create_broker

load_dotenv()

broker = create_broker(
    private_key=os.getenv("PRIVATE_KEY"),
    rpc_url=os.getenv("RPC_URL", "https://evmrpc.0g.ai"),
)

# Pick first available chat provider
services = broker.inference.list_service()
provider = services[0].provider

# Generate API key
api_key = broker.inference.get_secret(provider)

# Get endpoint and model
meta = broker.inference.get_service_metadata(provider)
endpoint = meta["endpoint"]
model = meta["model"]

print(f"ENDPOINT: {endpoint}")
print(f"MODEL:    {model}")
print(f"API_KEY:  {api_key}")
print()
print("# Example curl:")
print(f"""curl {endpoint}/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer {api_key}" -d '{{"model": "{model}", "messages": [{{"role": "user", "content": "Hello!"}}], "max_tokens": 150}}'""")
