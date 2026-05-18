# 0G Compute TS SDK Parity Tracker

This repo treats [`0gfoundation/0g-compute-ts-sdk`](https://github.com/0gfoundation/0g-compute-ts-sdk) as the upstream source of truth for the Python inference SDK.

## Workflow

1. Run the checker against the latest upstream TS SDK:

   ```bash
   python3 scripts/check_compute_parity.py --refresh
   ```

   Use the broader package scope when reviewing CLI/provider-controller/web UI parity:

   ```bash
   python3 scripts/check_compute_parity.py --refresh --scope package
   ```

2. Review `reports/compute_parity_report.md` for:

   - the `Coding Agent Brief` section, which is the primary handoff for implementation agents
   - `missing_in_python` feature probes
   - TypeScript-only classes, functions, and methods
   - name-only matches that need manual behavior review

3. For each meaningful upstream change, classify it:

   - `port`: Python should implement the feature or behavior.
   - `covered`: Python already supports it under a different name or shape.
   - `intentional-difference`: Python intentionally diverges.
   - `docs-only`: No SDK behavior to port.
   - `needs-research`: Source-level review is needed before deciding.

4. Add or update Python parity tests for any ported behavior.

## Last Checked Upstream

- Commit: `cee4e39e6b80ff31869b92bdad343fbc915493a3`
- Package version: `0.8.3`
- Date: `2026-05-17`
- Scope: `sdk`

## Last Reviewed Upstream

- Commit: `cee4e39e6b80ff31869b92bdad343fbc915493a3`
- Package version: `0.8.3`
- Date: `2026-05-18`
- Reviewer: `mandatedisrael`

Feature-probe status: **0 missing, 6 matched** (`session_tokens`, `persistent_api_keys`, `response_verification`, `read_only_broker`, `fine_tuning`, `lora_adapters`). The stale `async_inference` probe was removed — TS has no SDK-level async inference; both SDKs expose `get_request_headers` and the caller hits `/v1/async/...` directly.

The remaining 195 `ts_only` items are all internal structural drift: TS splits responsibilities across small processor classes (`RequestProcessor`, `ResponseProcessor`, `AccountProcessor`, `ModelProcessor`, `Verifier`, `InferenceServingContract`, `LedgerProcessor`, etc.) while Python collapses these into broader public managers (`InferenceManager`, `LedgerManager`, `FineTuningBroker`). Every method on a TS internal class is exposed on the matching Python manager.

## Open Parity Items

_None._ All inference, fine-tuning, ledger, and read-only methods/types/feature-probes are matched against TS `0.8.3`.

## Intentional Differences

| Upstream Area | Python Area | Reason | Review Date |
| --- | --- | --- | --- |
| `ZGComputeNetworkBroker` / `createZGComputeNetworkBroker` | `ZGServingBroker` / `create_broker` (aliases for TS names also exported) | Python kept the original class name; both work. | 2026-05-18 |
| `InferenceBroker` / `RequestProcessor` / `ResponseProcessor` / `AccountProcessor` / `ModelProcessor` / `Verifier` / `InferenceServingContract` | `InferenceManager` (single class) | Python collapses TS's internal processor classes into one public manager. Same methods, fewer layers. | 2026-05-18 |
| `LedgerProcessor` + `LedgerBroker` + `LedgerServingContract` | `LedgerManager` (single class) | Same rationale. | 2026-05-18 |
| Browser/Node runtime helpers (`isBrowser`, `isNode`, `crypto-adapter`) | not ported | TS-runtime-only abstractions; do not apply to Python. | 2026-05-18 |
| TypeChain generated contract types | not ported | Python uses web3.py ABIs directly. | 2026-05-18 |
| `getBundledBinary` / `getBinaryDir` / `getPackageRoot` | not ported | Node-only bundled-binary resolution; Python uses its own discovery. | 2026-05-18 |

## Shipped Parity Work

| Date | Upstream Reference | Python Change | Tests |
| --- | --- | --- | --- |
| 2026-05-18 | Inference `checkProviderSignerStatus`, owner TEE signer acknowledgement, token revocation, service signer fields; fine-tuning provider helper methods | Added Python snake_case wrappers for signer status/admin acknowledgement, batch token revocation, chain/user/lock-time helpers, signer-aware service metadata, and fine-tuning provider helpers for quote/model/task metadata. Fixed current inference account refund parsing. | `0g_py_inference/tests/test_inference_admin_parity.py`, `0g_py_inference/tests/test_fine_tuning_model_retrieval.py` |
| 2026-05-18 | Fine-tuning `acknowledgeModel`, `acknowledgeDeliverable`, `downloadModelFrom0GStorage`, TEE LoRA download retry options | Added TS-style model retrieval: default `auto` download tries 0G Storage first, falls back to TEE, verifies TEE artifact hashes when possible, then acknowledges the deliverable on-chain. Added queue-release `acknowledge_deliverable`, advanced `download_model_from_0g_storage`, and directory-aware/retrying TEE downloads. | `0g_py_inference/tests/test_fine_tuning_model_retrieval.py` |
| 2026-05-18 | Removed Python-only async-inference broker methods (`submit_async_request`, `submit_async_image_generation`/`_edit`, `get_async_job`, `wait_for_async_job`, `get_async_service_metadata`) and the `AsyncServiceMetadata`/`AsyncInferenceSubmission`/`AsyncInferenceJob` dataclasses. TS `InferenceBroker` only exposes `getRequestHeaders`; callers issue `/v1/async/...` HTTP themselves. README example updated to mirror `src.ts/example/inference-server.ts`. | n/a |
| 2026-05-18 | Ledger `listLedger`, combined `ZGComputeNetworkReadOnlyBroker`, factory + class name aliases (`ZGComputeNetworkBroker`/`createZGComputeNetworkBroker`/`createZGComputeNetworkReadOnlyBroker`), extractor aliases (`ChatBot`/`TextToImage`/`ImageEditing`/`SpeechToText`) | Ported `LedgerManager.list_ledger` over `getAllLedgers`; added `ZGComputeNetworkReadOnlyBroker` + `create_zg_compute_network_read_only_broker` bundling read-only inference + fine-tuning; added TS-name aliases at top-level package. | n/a |
| 2026-05-18 | Inference verifier types + structured `verifyService` (`VerificationStep`, `VerificationResult`, `VerificationSummary`, `SignerReportMatch`, `SignerRAVerificationResult`, `EventLogEntry`, `AttestationReport`, `ComposeVerificationResult`, `ProviderType`, `isVerifiability`, `ServingRequestHeaders`) | Added typed verifier dataclasses; refactored `InferenceManager.verify_service` to be silent-by-default, accept an `on_log: Callable[[VerificationStep], None]` callback, and return a typed `VerificationResult` instead of an ad-hoc dict. Added `is_verifiability` type guard and `ServingRequestHeaders` alias. | `0g_py_inference/tests/test_verify_service_structured.py` |
