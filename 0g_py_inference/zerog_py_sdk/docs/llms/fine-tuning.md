# Fine-Tuning Guide

Fine-tuning uses a broker plus managed local binaries. Prefer public broker
factories and `BinaryConfig` over manually shelling out to storage tools.

## Create a Fine-Tuning Broker

```python
from zerog_py_sdk import create_broker

broker = create_broker(private_key="0x...", network="testnet")
fine_tuning = broker.fine_tuning
```

For lower-level composition, use `create_fine_tuning_broker(...)` only when the
app already owns the Web3/account wiring.

## Managed Binaries

```python
from zerog_py_sdk import BinaryConfig, BinaryResolver

config = BinaryConfig(
    storage_client_path="/usr/local/bin/0g-storage-client",
    token_counter_path="/usr/local/bin/token_counter",
)
resolver = BinaryResolver(config)
storage_client = resolver.resolve_storage_client()
token_counter = resolver.resolve_token_counter()
```

Resolution order supports explicit paths, environment variables, user cache,
packaged files, and `PATH`. Invalid explicit paths fail immediately.

Environment variables:

- `ZG_STORAGE_CLIENT_PATH`
- `ZG_TOKEN_COUNTER_PATH`
- `ZG_BINARY_CACHE_DIR`

## Dataset Uploads and Model Downloads

Use the broker methods for dataset and model storage operations so the SDK can
apply size checks, timeout calculation, gas flags, hash verification, and
atomic file writes.

```python
from zerog_py_sdk import ModelVerificationError

try:
    result = fine_tuning.download_model(model_name, output_dir="./models")
except ModelVerificationError as exc:
    print(f"Model verification failed: {exc}")
```

Decrypted model artifacts are only published after verification succeeds.

## LoRA Adapter Methods

Authenticated inference brokers expose LoRA helpers:

```python
adapters = broker.inference.list_adapters(provider)
status = broker.inference.get_adapter_status(provider, adapter_id)
resolved = broker.inference.resolve_adapter_name(provider, "adapter-name")
```

Use these methods instead of guessing provider-specific adapter endpoints.
