# Troubleshooting Guide

Use this guide when generated code fails during setup, provider discovery,
verification, contract interaction, or fine-tuning binary resolution.

## Import Errors

Use real public exports:

```python
from zerog_py_sdk import create_broker, create_read_only_broker, Automata
```

Do not import `ZeroGInferenceClient` or `ZeroGVerifier`; those names are not
part of this SDK.

## Missing Wallet or Private Key

Use read-only discovery when no wallet is available:

```python
from zerog_py_sdk import create_read_only_broker

broker = create_read_only_broker(network="testnet")
services = broker.list_service_with_detail()
```

Use authenticated brokers only for paid actions:

```python
from zerog_py_sdk import create_broker_from_env

broker = create_broker_from_env()
```

## Provider Not Acknowledged

If a provider signer is not acknowledged, acknowledge it before sending paid
requests:

```python
broker.inference.acknowledge_provider_signer(provider)
```

## Fine-Tuning Binary Failures

Set explicit binary paths when automatic resolution is not enough:

```text
ZG_STORAGE_CLIENT_PATH=/path/to/0g-storage-client
ZG_TOKEN_COUNTER_PATH=/path/to/token_counter
ZG_BINARY_CACHE_DIR=/path/to/cache
```

Invalid explicit paths fail immediately. That is intentional.

## Verification Failures

`ModelVerificationError` means the SDK rejected an unsafe artifact. Do not use
partial outputs. Re-run discovery, confirm the provider signer, and retry with a
fresh download.

## Contract Reverts

Catch `ContractError` and inspect `error_name`, `error_args`, and
`revert_data`. For raw Web3 exceptions, use `contract_error_from_exception`.
