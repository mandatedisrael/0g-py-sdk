# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-10-06

### 🎉 Initial Working Release

This is the first fully functional version of the 0G Python SDK.

### ✅ Fixed

- **Endpoint URL Bug** - Fixed missing `/v1/proxy` path in endpoint URL
  - Before: `http://provider.com:8080`
  - After: `http://provider.com:8080/v1/proxy`
  - This was causing 403 Forbidden errors from providers
  - Found by comparing with TypeScript SDK implementation

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

- TypeScript SDK reference: [@0glabs/0g-serving-broker](https://github.com/0glabs/0g-serving-broker)
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
