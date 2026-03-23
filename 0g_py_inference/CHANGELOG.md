# Changelog

All notable changes to this project will be documented in this file.

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

---

## [Unreleased]

### Planned Features

- [ ] Automatic balance top-up when low
- [ ] Response verification with TEE attestation
- [ ] Streaming support for chat completions
- [ ] Batch request handling
- [ ] Provider health monitoring
- [ ] Gas price optimization
- [ ] Retry logic for failed requests

### Future Improvements

- [ ] Publish to PyPI as `og-compute-sdk`
- [ ] Add pytest test suite
- [ ] CI/CD with GitHub Actions
- [ ] Type hints with mypy validation
- [ ] Performance benchmarks
- [ ] More example scripts
