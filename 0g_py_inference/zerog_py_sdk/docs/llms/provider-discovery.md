# Provider Discovery Guide

Use read-only discovery when an app needs provider choices before a wallet is
connected. This is the safest path for dashboards, routing logic, and setup
screens.

## Read-Only Service Detail

```python
from zerog_py_sdk import create_read_only_broker

broker = create_read_only_broker(network="testnet")
services = broker.list_service_with_detail()

for service in services:
    print(service.provider)
    print(service.url)
    print(service.tee_signer_address)
    print(service.models)
```

`list_service_with_detail()` enriches on-chain services with provider metadata,
model catalogs, health, pricing, verifiability, and TEE signer information when
available.

## Provider Model Catalog

```python
models = broker.get_provider_models(provider_address)

print(models.provider)
print(models.default_model)
for model in models.models:
    print(model.id, model.price, model.health_metrics)
```

The SDK fetches the provider `/v1/models` catalog, caps response size, validates
the response shape, and best-effort enriches health data.

## Routing Pattern

1. Use `create_read_only_broker()` to list services.
2. Filter providers by model availability, health, pricing, and verifiability.
3. Ask the user to connect a wallet only when a paid action is needed.
4. Use `create_broker(...)` and `get_request_headers(provider)` for execution.

Avoid scraping internal contract classes for discovery. The read-only broker is
the public API for wallet-free provider selection.
