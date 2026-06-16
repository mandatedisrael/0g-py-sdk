# 0G Python Inference SDK Agent Guide

This directory is bundled inside the `0g-inference-sdk` wheel. It is intended
for coding agents and AI assistants that inspect installed packages directly.
Use these local files as the version-locked source of truth for SDK usage.

## Agent Workflow

1. Start from the public exports in `zerog_py_sdk.__init__`.
2. Prefer broker factory functions over importing internal modules.
3. Read the task-specific guide before writing code.
4. Use examples that match the installed package version.
5. Catch SDK exceptions explicitly and surface actionable errors.

## Public Entry Points

```python
from zerog_py_sdk import (
    create_broker,
    create_broker_from_env,
    create_read_only_broker,
    create_fine_tuning_broker,
    ResponseVerifier,
    verify_tee_response,
    Automata,
    ModelVerificationError,
    ContractError,
    decode_contract_error,
)
```

Do not use non-existent APIs such as `ZeroGInferenceClient` or
`ZeroGVerifier`. The canonical client surface is broker-based.

## Task Map

- [Inference](inference.md): create an authenticated broker, get headers,
  send requests, and parse usage.
- [Provider Discovery](provider-discovery.md): discover providers and model
  catalogs without a wallet.
- [Fine-Tuning](fine-tuning.md): upload datasets, manage fine-tuning tasks,
  resolve binaries, and use LoRA adapters.
- [Model Verification](model-verification.md): verify TEE responses, Automata
  quotes, and encrypted model artifacts.
- [Contract Errors](contract-errors.md): decode custom EVM reverts.
- [Troubleshooting](troubleshooting.md): common failures and recovery steps.

## Environment Variables

Common variables used by examples:

- `PRIVATE_KEY`: wallet private key for authenticated broker operations.
- `NETWORK`: optional network selector, such as `testnet` or `mainnet`.
- `ZG_STORAGE_CLIENT_PATH`: explicit 0G Storage client binary path.
- `ZG_TOKEN_COUNTER_PATH`: explicit fine-tuning token counter binary path.
- `ZG_BINARY_CACHE_DIR`: cache directory for managed fine-tuning binaries.

Prefer `create_broker_from_env()` when the user's app already configures these
values in the environment.
