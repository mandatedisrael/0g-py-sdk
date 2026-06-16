# Inference Guide

Use the authenticated broker for paid inference requests and the read-only
broker for discovery. Keep provider selection separate from request execution:
first discover a provider, then create request headers for that provider.

## Authenticated Broker

```python
from zerog_py_sdk import create_broker

broker = create_broker(private_key="0x...", network="testnet")
services = broker.inference.list_service()

provider = services[0].provider
headers = broker.inference.get_request_headers(provider)
metadata = broker.inference.get_service_metadata(provider)

print(metadata.endpoint)
print(headers)
```

`get_request_headers(provider)` returns signed request headers for provider
HTTP APIs. Generate headers close to request time and do not reuse them after a
provider rejects or consumes them.

## Model-Specific Metadata

Some providers expose multiple models. Pass a model ID when routing to a
non-default model:

```python
metadata = broker.inference.get_service_metadata(
    provider,
    model="provider-model-id",
)
```

If `model` is omitted, the SDK uses the provider's on-chain default model.

## Speech Billing

`SpeechToTextExtractor` supports duration-billed and token-billed usage. Use the
extractor rather than hand-parsing provider responses:

```python
from zerog_py_sdk import SpeechToTextExtractor

extractor = SpeechToTextExtractor()
usage = extractor.extract_usage({
    "usage": {"type": "duration", "seconds": 12.4}
})
print(usage)
```

## Error Handling

```python
from zerog_py_sdk import ContractError, NetworkError, ProviderNotAcknowledgedError

try:
    headers = broker.inference.get_request_headers(provider)
except ProviderNotAcknowledgedError:
    broker.inference.acknowledge_provider_signer(provider)
except ContractError as exc:
    print(exc.error_name, exc.error_args)
except NetworkError as exc:
    print(f"Network error: {exc}")
```

For provider and model discovery before authentication, read
`provider-discovery.md`.
