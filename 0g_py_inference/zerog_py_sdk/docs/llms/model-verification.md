# Model Verification Guide

The SDK has two verification paths:

1. TEE response verification for provider responses.
2. Fine-tuning model artifact verification before decrypted files are published.

Both paths should fail closed. Do not swallow verification failures unless the
user explicitly chooses an unsafe workflow.

## TEE Response Verification

```python
from zerog_py_sdk import verify_tee_response, InvalidResponseError

try:
    verified = verify_tee_response(
        response=provider_response,
        provider_url=provider_url,
        chat_id=chat_id,
        tee_signer_address=tee_signer_address,
        tee_signer_acknowledged=True,
        service=service_metadata,
    )
except InvalidResponseError as exc:
    print(f"Provider response verification failed: {exc}")
else:
    print(verified)
```

If you need structured step-by-step reporting, use the inference broker's
`verify_service(...)` flow and inspect the returned `VerificationResult`.

## Automata Attestation

```python
from zerog_py_sdk import Automata, NetworkError

automata = Automata()

try:
    ok, output = automata.verify_quote("0x...")
except NetworkError as exc:
    print(f"Automata unavailable: {exc}")
else:
    print(ok, output)
```

An explicit Automata rejection should be treated differently from temporary RPC
unavailability. The SDK's structured verification result preserves that
distinction.

## Fine-Tuning Model Artifact Verification

Encrypted fine-tuning model artifacts must include valid TEE signer material.
The SDK verifies raw `keccak256(tags)` signatures and AES-GCM authentication
before publishing decrypted files.

```python
from zerog_py_sdk import ModelVerificationError

try:
    model_path = broker.fine_tuning.download_model(
        model_name,
        output_dir="./models",
    )
except ModelVerificationError as exc:
    print(f"Unsafe model artifact rejected: {exc}")
```

Common rejection reasons:

- missing provider signer address
- malformed signature
- recovered signer does not match the provider signer
- invalid decryption key
- AES-GCM authentication failure
- incomplete download

When this error appears, do not use any partially downloaded or decrypted file.
The SDK writes through temporary files and only replaces the destination after
successful verification.
