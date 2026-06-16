# Changelog

All notable changes to this project will be documented in this file.

## [0.9.1] - 2026-06-17

Agent-readiness and production-hardening release for builders preparing for
0G Bridge by AKINDO and Zero Cup. This release includes the bundled
agent-readable documentation added in `0.9.1`, plus the production updates
introduced in `0.9.0`.

### Agent-Readable SDK

- **Bundled agent documentation.** The `0g-inference-sdk` wheel now ships
  local, version-locked markdown guides under
  `zerog_py_sdk/docs/llms/`, plus `zerog_py_sdk/llms.txt` as a lightweight
  machine-readable index.
- **Agent front-door breadcrumbs.** The top-level `zerog_py_sdk` docstring now
  points coding agents to the bundled docs and to the real public broker,
  verification, Automata, and error-decoding APIs.
- **Task-specific recipes.** Added local guides for inference, provider
  discovery, fine-tuning, model verification, contract errors, and common
  troubleshooting.
- **Wheel packaging guard.** Added tests that build the wheel and confirm the
  agent docs are included in the installable artifact.
- **Installed-package resource access.** Packaged docs as importable SDK
  resources so agents can access the right docs for the installed version after
  `pip install`.

### Production Updates Included

- **Production-grade TEE model signer verification.** Model artifact
  verification now fails closed on missing signers, signer mismatches,
  malformed signatures, invalid keys, and AES-GCM authentication failures.
- **Ledger refund and provider balance fixes.** Refund flows now resolve
  service names correctly, and provider balance details are more accurate for
  production usage.
- **Atomic decrypted model publishing.** Decrypted model artifacts and 0G
  Storage downloads are written to temporary files and atomically replace the
  destination only after verification or successful completion.
- **Official Automata attestation client.** Added a public `Automata` helper
  using the official RPC and contract interface for service verification flows.
- **Speech billing parity.** Speech-to-text billing now supports duration and
  token usage accounting with compatible rounding and malformed-input handling.
- **Multi-model discovery/API parity.** Authenticated and read-only brokers can
  browse provider models, pricing, health, and service details before routing
  inference requests.

### Also Included

- Managed fine-tuning binary resolution with explicit paths, environment
  variables, user cache, packaged files, and `PATH` lookup.
- Verified token counter bootstrap with SHA-256 validation and atomic cache
  installation.
- ABI-aware contract error decoding for custom Solidity errors, standard
  reverts, panics, nested RPC errors, and Web3 exception shapes.
- Tests covering agent-doc packaging, Automata outcomes, model encryption
  security, binary management, contract errors, speech billing, and
  multi-model discovery.

## [0.9.0] - 2026-06-13

Production-hardening parity release for
`@0gfoundation/0g-compute-ts-sdk` `0.9.0-beta.0` at commit
`acaba1ec073cb565a67ef94a5f351d1ab0709bbf`.

### Added

- **Official Automata client.** Added a public `Automata` helper using the
  official `https://1rpc.io/ata` RPC and
  `verifyAndAttestOnChain(bytes) -> (bool, bytes)` contract interface.
- **Managed fine-tuning binaries.** Added `BinaryConfig` and `BinaryResolver`
  with explicit path, environment, user-cache, packaged-file, and `PATH`
  resolution. Invalid explicit configuration fails immediately.
- **Verified token counter bootstrap.** Missing `token_counter` executables can
  be retrieved from the TypeScript SDK's pinned 0G Storage root, SHA-256
  verified, and atomically installed in the user's SDK cache.
- **ABI-aware contract errors.** `ContractError` now includes `error_name`,
  `error_args`, and `revert_data` when Web3 exposes a Solidity custom error,
  `Error(string)`, or `Panic(uint256)`.

### Changed

- **Model decryption now fails closed.** TEE tag signatures use the same raw
  `keccak256(tags)` recovery as the TypeScript SDK. Missing signers, signer
  mismatches, malformed signatures, invalid keys, and AES-GCM authentication
  failures raise `ModelVerificationError`.
- Decrypted model artifacts and 0G Storage downloads are written to temporary
  files and atomically replace the destination only after verification or
  successful completion.
- `verify_service()` now distinguishes an explicit Automata rejection
  (`attestation_verified=False`, verification fails) from an unavailable
  Automata RPC (`attestation_verified=None`, signer verification can continue).
- Dataset upload now forwards the TypeScript SDK's storage-client gas flags.
  Model and dataset storage operations share one configured, validated binary.
- Fine-tuning, ledger, and inference contract paths preserve decoded revert
  metadata and the original exception cause.

### Tests

- Added real AES-GCM and secp256k1 model-artifact fixtures.
- Added Automata ABI and rejected-versus-unavailable outcome coverage.
- Added binary precedence, hash verification, atomic download, and subprocess
  behavior coverage.
- Added custom Solidity error, standard revert, panic, nested RPC, and Web3
  exception coverage.

## [0.8.0] - 2026-06-12

Parity release for `@0gfoundation/0g-compute-ts-sdk` `0.9.0-beta.0`
at commit `acaba1ec073cb565a67ef94a5f351d1ab0709bbf`.

### Added

- **Multi-model provider discovery.** `get_provider_models(provider_address)`
  is available on authenticated and read-only inference brokers. It fetches
  the provider's authoritative `/v1/models` catalog and returns
  `ProviderModels`, including the on-chain default model, multi-model flag,
  price denomination, canonical model IDs, pricing, and per-model health.
- **Multi-model service detail.** `list_service_with_detail()` now includes
  `multi_model`, `price_denomination`, and the provider's complete `models`
  list when available.
- **New public parity types.** `MultiModelInfo`, `ProviderModels`, and
  `ServiceHealthMetric`, plus `parse_multi_model_info()`.
- **Standalone broker factories.** Added `create_ledger_broker()`,
  `create_inference_broker()`, and `create_fine_tuning_broker()`, plus
  `LedgerBroker`, `InferenceBroker`, and
  `create_read_only_inference_broker` aliases.
- **Direct LoRA broker methods.** The inference broker now exposes
  `list_adapters()`, `get_adapter_status()`, `resolve_adapter_name()`,
  `deploy_adapter()`, `deploy_adapter_by_name()`, and
  `chat_with_fine_tuned_model()`, matching the official broker surface.
- **Canonical network detection.** `get_network_type(chain_id)` returns
  `mainnet`, `testnet`, `hardhat`, or `unknown` without dev-mode overrides.

### Changed

- **Request-time model selection.**
  `get_service_metadata(provider_address, model=None)` now accepts an optional
  model ID. The SDK forwards the requested ID unchanged and falls back to the
  on-chain default when omitted, matching the TypeScript SDK.
- **Speech-to-text billing.** `SpeechToTextExtractor` now supports both
  duration-billed usage (`{"type":"duration","seconds":N}`) and token-billed
  usage (`{"type":"tokens","input_tokens":N,"output_tokens":N}`), including
  TypeScript-compatible rounding and malformed-input handling.
- Provider model catalog responses are capped at 5 MB and schema-validated.
  Provider lookup failures are surfaced; status API health enrichment remains
  best-effort.
- **Ledger provider details.** `get_providers_with_balance()` now returns
  `(provider, balance, pending_refund)` tuples, filters empty accounts, and
  reads provider lists through the current `getLedgerProviders` contract API.
- **Ledger refunds.** `retrieve_fund()` and
  `retrieve_fund_from_provider()` resolve registered service names before
  submitting transactions. Bulk refunds filter accounts using the same
  balance and pending-refund rule as TypeScript.
- **Fine-tuning downloads and uploads.** Model-usage downloads accept an
  output directory and write `<model>.zip`. TEE dataset uploads support
  `max_file_size_mb` and `timeout_ms`, including TS-compatible size checks
  and calculated timeouts.

### Tests

- Added direct ports of the TypeScript speech-to-text billing cases.
- Added multi-model parsing, catalog, health matching, response validation,
  and authenticated model-selection coverage.
- Added network helper, direct LoRA broker, ledger detail/refund,
  fine-tuning transfer, and standalone factory coverage.

## [0.7.0] - 2026-05-18

### Breaking Changes

- **`verify_service` returns a typed result.** Replaces the previous
  `dict` return with a `VerificationResult` dataclass, and adds an
  optional `on_log: Callable[[VerificationStep], None]` callback. The
  method is now **silent by default** (no stdout writes) — opt in to
  terminal output via `on_log`, or iterate `result.steps` after the
  call to replay the verification trace.

  ```python
  # before
  result = broker.inference.verify_service(provider)
  if result["is_valid"]:
      ...

  # after
  result = broker.inference.verify_service(provider)
  if result.success:
      ...

  # stream progress
  broker.inference.verify_service(
      provider,
      on_log=lambda step: print(step.message),
  )
  ```

  Field renames: `is_valid` → `success`, `report_path` →
  `reports_generated[0]`. All other fields keep their names as
  dataclass attributes.

- **Removed async-inference broker methods.** `submit_async_request`,
  `submit_async_image_generation`, `submit_async_image_edit`,
  `get_async_job`, `wait_for_async_job`,
  `get_async_service_metadata`, and the `AsyncServiceMetadata` /
  `AsyncInferenceSubmission` / `AsyncInferenceJob` dataclasses are
  gone. Async image jobs are now driven by callers issuing
  `/v1/async/...` HTTP themselves with headers from
  `broker.inference.get_request_headers(...)`. See the README for
  the new pattern.

### Added

- **Provider signer administration.** New helpers on the inference
  broker for managing on-chain TEE signer state:
  `check_provider_signer_status`, `acknowledge_provider_tee_signer`,
  `acknowledge_tee_signer_by_owner`,
  `revoke_provider_tee_signer_acknowledgement`, `revoke_tokens`,
  `list_accounts`, `get_chain_id`, `get_user_address`, `lock_time`.

- **Typed verifier surface.** New dataclasses exported from
  `zerog_py_sdk`: `VerificationStep`, `VerificationResult`,
  `VerificationSummary`, `SignerVerification`, `SignerReportMatch`,
  `SignerRAVerificationResult`, `AttestationReport`, `EventLogEntry`,
  `ReportsData`, `ComposeVerification`,
  `ComposeVerificationDetail`, `ComposeVerificationResult`,
  `ProviderType`, `VerificationLogger`.

- **`is_verifiability(value)`** — type guard returning `True` iff
  `value` matches a `VerifiabilityEnum` member.

- **Combined read-only broker.** `ZGComputeNetworkReadOnlyBroker` +
  `create_zg_compute_network_read_only_broker` bundle the inference
  and fine-tuning read-only sub-brokers behind one object for
  wallet-less browsing of the full network surface.

- **Top-level broker aliases.** `ZGComputeNetworkBroker` and
  `create_zg_compute_network_broker` are now exported as alternative
  names for `ZGServingBroker` and `create_broker`.

- **Extractor name aliases.** `ChatBot`, `TextToImage`,
  `ImageEditing`, and `SpeechToText` are now exported alongside the
  existing `*Extractor` classes.

- **`ServingRequestHeaders`** — alias for `RequestHeaders` so callers
  can use whichever name reads better in their codebase.

- **Ledger: `list_ledger(offset, limit)`** — paginated enumeration of
  all ledger accounts via `getAllLedgers`.

- **Fine-tuning model retrieval.** `acknowledge_model` gains a
  default `auto` strategy that tries 0G Storage first, falls back to
  TEE LoRA download with hash verification, then acknowledges the
  deliverable on-chain. New companion helpers:
  `acknowledge_deliverable`, advanced
  `download_model_from_0g_storage`, and directory-aware
  `download_lora_from_tee` with configurable retry options.

- **Read-only service detail enrichment.** `list_service_with_detail`
  now augments services with status-API model metadata and parsed
  `tiered_pricing` / `cache_token_billing` fields where providers
  expose them.

- **Contract ABI.** Added bindings for `acknowledgeTEESignerByOwner`
  and `getAllAccounts`; the `getService` return tuple now includes
  `teeSignerAddress` and `teeSignerAcknowledged`.

### Changed

- **Auto-funding.** Inline auto-funding checks are tightened so
  balance top-ups respect the configured interval and
  buffer-multiplier consistently across rapid request bursts.

### Removed

- The async-inference broker methods and dataclasses listed under
  Breaking Changes.

### Tests

- `tests/test_inference_admin_parity.py`
- `tests/test_fine_tuning_model_retrieval.py`
- `tests/test_verify_service_structured.py`
- `tests/test_auto_funding.py`
- `tests/test_read_only_detail.py`

## [0.5.0] - 2026-03-23

### Breaking Changes - Contract ABI Update

Updated SDK to match current 0G testnet/mainnet contract ABIs. The deployed contracts have changed significantly since v0.4.0.

### Fixed
- **`acknowledgeTEESigner`** now takes `(provider, bool)` instead of `(provider, address)` to match updated contract
- **`addAccount`** removed obsolete `signer` (uint256[2]) parameter
- **`getAccount`** Account struct updated: removed `signer`/`providerPubKey`/`teeSignerAddress`, added `acknowledged` (bool), `generation`, `revokedBitmap`
- **`transferFund`** service name changed from `"inference"` to `"inference-v1.0"` to match new ledger service registry
- Fixed Account struct index references in `auth.py` and `inference.py`

### Changed
- Updated `SERVING_CONTRACT_ABI` with new function signatures and Account/Service structs
- Added new contract functions: `serviceExists`, `isTokenRevoked`, `getPendingRefund`, `processRefund`, `revokeTokens`
- Updated `Account` model dataclass to match new on-chain struct

## [0.2.2] - 2026-03-17

### 🎉 NEW: verify_service() Method (Comprehensive TEE Verification)

This release adds comprehensive service verification capabilities .

### ✅ Added

- **`verify_service(provider_address, output_dir?)` method**
  - Comprehensive TEE service verification
  - Fetches and validates TEE quotes
  - Verifies attestation via Automata contract
  - Checks provider signer status
  - Generates detailed verification reports
  - Returns structured results with error tracking
  - Example:
    ```python
    result = broker.inference.verify_service(provider_address)
    print(f"Valid: {result['is_valid']}")
    print(f"TEE Signer: {result['tee_signer']}")

    # With report generation
    result = broker.inference.verify_service(
        provider_address,
        output_dir="./reports"
    )
    print(f"Report: {result['report_path']}")
    ```

- **Comprehensive test suite** (`test_verify_service.py`)
  - Tests basic verification
  - Tests report generation
  - Tests multi-provider verification
  - Tests error handling
  - All tests passing

- **Usage example** (`example_verify_service.py`)
  - Basic verification workflow
  - Report generation
  - Batch verification
  - Practical integration examples

### 📝 Features

- **Quote Fetching**: Retrieves TEE quotes from provider endpoints
- **Attestation Verification**: Validates quotes using Automata contract
- **Provider Status**: Checks contract acknowledgment status
- **Error Tracking**: Collects all errors in results array
- **Report Generation**: Optional JSON report with full details
- **Graceful Degradation**: Handles provider unavailability
- **Comprehensive Output**: Returns 15+ data points about service

### 🔧 Technical Details

- Integrates with existing `_verify_quote_with_automata()` method
- Uses Pathlib for cross-platform report saving
- Includes timestamp for audit trails
- Non-blocking - doesn't fail on individual errors
- Returns detailed error messages for troubleshooting

---

## [0.2.1] - 2026-03-17

### 🎉 NEW: get_secret() Method

This release adds the `get_secret()` method to match the TypeScript SDK's `getSecret()` functionality.

### ✅ Added

- **`get_secret(provider_address, token_id?, expires_in?)` method**
  - Generate persistent API keys for direct HTTP usage
  - Returns raw token string in format: `app-sk-<base64_encoded_token>`
  - Supports custom token IDs (0-254)
  - Supports expiration times (milliseconds)
  - Standard token format
  - Example:
    ```python
    secret = broker.inference.get_secret(provider_address)
    headers = {"Authorization": f"Bearer {secret}"}
    ```

- **Comprehensive test suite** (`test_get_secret.py`)
  - Validates token generation with default settings
  - Tests token ID assignment
  - Tests expiration handling
  - Validates against real API requests
  - Compares with `get_request_headers()` output

- **Usage example** (`example_get_secret.py`)
  - Simple demonstration of API key generation
  - Shows advanced usage patterns
  - Includes revocation examples

### 📝 Documentation

- Updated README with `get_secret()` usage examples
- Added API key management section
- Documented token ID ranges (0-254 for persistent, 255 for ephemeral)
- Added comparison between `get_secret()` and `create_api_key()`

### ✅ Verified

- Standard token format
- Successfully tested with live providers on testnet
- API keys work in real inference requests
- Token structure validated (JSON + signature)
- Compatible with existing session token infrastructure

### 🔧 Technical Details

- Wraps existing `SessionManager.create_api_key()` functionality
- Returns raw token string for convenience
- Auto-assigns token IDs if not specified
- Validates token IDs and checks revocation bitmap
- No breaking changes to existing API

---

## [0.1.0] - 2025-10-06

### 🎉 Initial Working Release

This is the first fully functional version of the 0G Python SDK.

### ✅ Fixed

- **Endpoint URL Bug** - Fixed missing `/v1/proxy` path in endpoint URL
  - Before: `http://provider.com:8080`
  - After: `http://provider.com:8080/v1/proxy`
  - This was causing 403 Forbidden errors from providers

- **Account Creation** - Provider acknowledgment now auto-creates accounts
  - Previously would fail if account didn't exist
  - Now calls `transfer_fund(provider, "inference", 0)` to create account

### 🚀 Added

- Complete working example in `test.py`
- Comprehensive README with architecture deep-dive
- Quick setup guide in `SETUP.md`
- Detailed component documentation
- Request flow diagrams
- Troubleshooting section

### 📝 Documentation

- Added visual flow diagram showing system interaction
- Documented all SDK components:
  - `broker.py` - Main orchestrator
  - `ledger.py` - Payment management
  - `inference.py` - AI request handling
  - `auth.py` - Cryptographic signing
  - `models.py` - Data structures
  - `utils.py` - Helper functions
- Explained hybrid Python + Node.js architecture
- Added account model visualization
- Included complete request flow walkthrough

### 🧪 Testing

- Verified against live 0G testnet providers
- Successfully queried multiple AI models:
  - `phala/gpt-oss-120b`
  - `phala/deepseek-chat-v3-0324`
  - `phala/qwen2.5-vl-72b-instruct`

### 📦 Files Changed

```
Modified:
- zerog_py_sdk/inference.py:318 (fixed endpoint URL)
- zerog_py_sdk/broker.py (pass ledger_manager to InferenceManager)
- README.md (complete rewrite with detailed docs)

Added:
- SETUP.md (quick start guide)
- CHANGELOG.md (this file)

Updated:
- .gitignore (ensure venv/ is ignored, allow test.py)
- test.py (complete working example)
```

### 🐛 Known Issues

None currently identified.

### 🔗 Dependencies

- Python 3.8+
- web3>=6.0.0
- eth-account>=0.10.0
- eth-utils>=2.0.0
- requests>=2.31.0
- python-dotenv>=1.0.0
- Node.js 16.x+
- circomlibjs (npm global package)

### 🙏 Credits

- Python implementation: [@damiclone](https://x.com/damiclone)
