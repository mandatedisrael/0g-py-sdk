# Contract Error Guide

The SDK decodes ABI-aware EVM revert data into `ContractError`. Agents should
surface the decoded fields instead of printing opaque Web3 exceptions.

## Decode an Existing Exception

```python
from zerog_py_sdk import contract_error_from_exception

try:
    tx_hash = broker.ledger.retrieve_fund(provider)
except Exception as exc:
    decoded = contract_error_from_exception(exc)
    if decoded is not None:
        print(decoded.error_name)
        print(decoded.error_args)
        print(decoded.revert_data)
    else:
        raise
```

## Catch SDK Contract Errors

```python
from zerog_py_sdk import ContractError

try:
    broker.ledger.retrieve_fund(provider)
except ContractError as exc:
    print(f"Contract reverted: {exc.error_name}")
    print(exc.error_args)
```

`ContractError` may include:

- `error_name`: Solidity custom error name, `Error`, or `Panic`.
- `error_args`: decoded revert arguments.
- `revert_data`: raw revert data when available.
- `__cause__`: the original Web3/RPC exception.

## Practical Recovery

- Check whether the provider service name is registered before refund calls.
- Check account balance and pending refunds before top-ups.
- For fine-tuning, check task state before mutating or downloading.
- Preserve the original exception when re-raising so debugging context is not
  lost.
