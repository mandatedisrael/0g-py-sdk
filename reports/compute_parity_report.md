# Compute SDK Parity Report

Generated: `2026-05-18T15:06:00.078413+00:00`
Upstream: `@0gfoundation/0g-compute-ts-sdk` `0.8.3`
Commit: `cee4e39e6b80ff31869b92bdad343fbc915493a3`
Source path: `/Users/damiafo/Documents/projects/og-py-sdk/.cache/compute_ts_sdk`
Scope: `sdk`

## Summary

- TypeScript surface items: `320`
- Python surface items: `527`
- Matched items: `60`
- Needs review: `57`
- Present in TS only: `195`
- Present in Python only: `360`
- Missing feature probes: `0`

## Feature Probes

| Status | Feature | TS Evidence | Python Evidence |
| --- | --- | --- | --- |
| matched | Session token auth | `SessionToken, tokenId, Authorization.*Bearer app-sk` | `SessionToken, token_id, Authorization.*Bearer app-sk` |
| matched | Persistent API keys | `createApiKey, revokeApiKey` | `create_api_key, revoke_api_key` |
| matched | TEE response verification | `verify.*Response, processResponse, attestation` | `verify.*response, process_response, attestation` |
| matched | Read-only service browsing | `ReadOnly.*Broker, listServiceWithDetail` | `ReadOnly.*Broker, list_service_with_detail` |
| matched | Fine-tuning workflow | `FineTuningBroker, createTask, uploadDataset` | `FineTuningBroker, create_task, upload_dataset` |
| matched | LoRA adapter deployment | `deployAdapter, listAdapters, adapterName` | `deploy_adapter, list_adapters, adapter_name` |

## Coding Agent Brief

Use this section as the handoff for implementation or review work.

- Upstream commit: `cee4e39e6b80ff31869b92bdad343fbc915493a3`
- Upstream package: `@0gfoundation/0g-compute-ts-sdk` `0.8.3`
- Compare scope: `sdk`
- Python root: `0g_py_inference/zerog_py_sdk`
- Treat every action item as a hypothesis from static analysis, then confirm from source before coding.

### Prioritized Action Items

No missing or partial feature probes were detected. Review the TypeScript-only surface table for lower-priority drift.

## TypeScript Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `broker` | `re_export` | `getNetworkType` | `src.ts/sdk/broker.ts:23` |
| `extractors` | `method` | `ChatBot.getInputCount` | `src.ts/sdk/inference/extractor/chatbot.ts:15` |
| `extractors` | `method` | `ChatBot.getOutputCount` | `src.ts/sdk/inference/extractor/chatbot.ts:39` |
| `extractors` | `method` | `ChatBot.getSvcInfo` | `src.ts/sdk/inference/extractor/chatbot.ts:11` |
| `extractors` | `method` | `ImageEditing.getInputCount` | `src.ts/sdk/inference/extractor/imageEditing.ts:15` |
| `extractors` | `method` | `ImageEditing.getOutputCount` | `src.ts/sdk/inference/extractor/imageEditing.ts:38` |
| `extractors` | `method` | `ImageEditing.getSvcInfo` | `src.ts/sdk/inference/extractor/imageEditing.ts:11` |
| `extractors` | `method` | `SpeechToText.getInputCount` | `src.ts/sdk/inference/extractor/speech-to-text.ts:15` |
| `extractors` | `method` | `SpeechToText.getOutputCount` | `src.ts/sdk/inference/extractor/speech-to-text.ts:21` |
| `extractors` | `method` | `SpeechToText.getSvcInfo` | `src.ts/sdk/inference/extractor/speech-to-text.ts:11` |
| `extractors` | `method` | `TextToImage.getInputCount` | `src.ts/sdk/inference/extractor/textToImage.ts:15` |
| `extractors` | `method` | `TextToImage.getOutputCount` | `src.ts/sdk/inference/extractor/textToImage.ts:38` |
| `extractors` | `method` | `TextToImage.getSvcInfo` | `src.ts/sdk/inference/extractor/textToImage.ts:11` |
| `fine_tuning` | `class` | `BrokerBase` | `src.ts/sdk/fine-tuning/broker/base.ts:12` |
| `fine_tuning` | `class` | `FineTuningServingContract` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:15` |
| `fine_tuning` | `class` | `Provider` | `src.ts/sdk/fine-tuning/provider/provider.ts:50` |
| `fine_tuning` | `class` | `ReadOnlyFineTuningServingContract` | `src.ts/sdk/fine-tuning/contract/read-only-fine-tuning.ts:6` |
| `fine_tuning` | `class` | `ReadOnlyModelProcessor` | `src.ts/sdk/fine-tuning/broker/read-only-model.ts:15` |
| `fine_tuning` | `class` | `ReadOnlyServiceProcessor` | `src.ts/sdk/fine-tuning/broker/read-only-service.ts:8` |
| `fine_tuning` | `function` | `calculateTokenSizeViaExe` | `src.ts/sdk/fine-tuning/token/token.ts:47` |
| `fine_tuning` | `function` | `calculateTokenSizeViaPython` | `src.ts/sdk/fine-tuning/token/token.ts:98` |
| `fine_tuning` | `function` | `createFineTuningBroker` | `src.ts/sdk/fine-tuning/broker/broker.ts:553` |
| `fine_tuning` | `function` | `download` | `src.ts/sdk/fine-tuning/zg-storage/zg-storage.ts:100` |
| `fine_tuning` | `function` | `getBinaryDir` | `src.ts/sdk/fine-tuning/zg-storage/binary-path.ts:147` |
| `fine_tuning` | `function` | `getBundledBinary` | `src.ts/sdk/fine-tuning/zg-storage/binary-path.ts:162` |
| `fine_tuning` | `function` | `getPackageRoot` | `src.ts/sdk/fine-tuning/zg-storage/binary-path.ts:124` |
| `fine_tuning` | `function` | `upload` | `src.ts/sdk/fine-tuning/zg-storage/zg-storage.ts:12` |
| `fine_tuning` | `method` | `FineTuningServingContract.acknowledgeDeliverable` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:229` |
| `fine_tuning` | `method` | `FineTuningServingContract.acknowledgeTEESigner` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:159` |
| `fine_tuning` | `method` | `FineTuningServingContract.acknowledgeTEESignerByOwner` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:179` |
| `fine_tuning` | `method` | `FineTuningServingContract.checkReceipt` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:265` |
| `fine_tuning` | `method` | `FineTuningServingContract.getAccount` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:149` |
| `fine_tuning` | `method` | `FineTuningServingContract.getDeliverable` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:249` |
| `fine_tuning` | `method` | `FineTuningServingContract.getUserAddress` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:261` |
| `fine_tuning` | `method` | `FineTuningServingContract.listAccount` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:140` |
| `fine_tuning` | `method` | `FineTuningServingContract.removeService` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:217` |
| `fine_tuning` | `method` | `FineTuningServingContract.revokeTEESignerAcknowledgement` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:198` |
| `fine_tuning` | `method` | `FineTuningServingContract.sendTx` | `src.ts/sdk/fine-tuning/contract/fine-tuning.ts:41` |
| `fine_tuning` | `method` | `Provider.cancelTask` | `src.ts/sdk/fine-tuning/provider/provider.ts:138` |
| `fine_tuning` | `method` | `Provider.createTask` | `src.ts/sdk/fine-tuning/provider/provider.ts:116` |
| `fine_tuning` | `method` | `Provider.downloadLoRAFromTEE` | `src.ts/sdk/fine-tuning/provider/provider.ts:332` |
| `fine_tuning` | `method` | `Provider.getCustomizedModel` | `src.ts/sdk/fine-tuning/provider/provider.ts:246` |
| `fine_tuning` | `method` | `Provider.getCustomizedModelDetailUsage` | `src.ts/sdk/fine-tuning/provider/provider.ts:260` |
| `fine_tuning` | `method` | `Provider.getCustomizedModels` | `src.ts/sdk/fine-tuning/provider/provider.ts:235` |
| `fine_tuning` | `method` | `Provider.getLog` | `src.ts/sdk/fine-tuning/provider/provider.ts:221` |
| `fine_tuning` | `method` | `Provider.getPendingTaskCounter` | `src.ts/sdk/fine-tuning/provider/provider.ts:206` |
| `fine_tuning` | `method` | `Provider.getProviderUrl` | `src.ts/sdk/fine-tuning/provider/provider.ts:89` |
| `fine_tuning` | `method` | `Provider.getQuote` | `src.ts/sdk/fine-tuning/provider/provider.ts:98` |
| `fine_tuning` | `method` | `Provider.getTask` | `src.ts/sdk/fine-tuning/provider/provider.ts:163` |
| `fine_tuning` | `method` | `Provider.listTask` | `src.ts/sdk/fine-tuning/provider/provider.ts:183` |
| `fine_tuning` | `method` | `ReadOnlyFineTuningServingContract.getChainId` | `src.ts/sdk/fine-tuning/contract/read-only-fine-tuning.ts:47` |
| `fine_tuning` | `method` | `ReadOnlyFineTuningServingContract.getService` | `src.ts/sdk/fine-tuning/contract/read-only-fine-tuning.ts:39` |
| `fine_tuning` | `method` | `ReadOnlyFineTuningServingContract.listService` | `src.ts/sdk/fine-tuning/contract/read-only-fine-tuning.ts:23` |
| `fine_tuning` | `method` | `ReadOnlyFineTuningServingContract.lockTime` | `src.ts/sdk/fine-tuning/contract/read-only-fine-tuning.ts:19` |
| `fine_tuning` | `method` | `ReadOnlyModelProcessor.listModel` | `src.ts/sdk/fine-tuning/broker/read-only-model.ts:44` |
| `fine_tuning` | `method` | `ReadOnlyServiceProcessor.listService` | `src.ts/sdk/fine-tuning/broker/read-only-service.ts:21` |
| `fine_tuning` | `method` | `ServiceProcessor.acknowledgeTEESignerByOwner` | `src.ts/sdk/fine-tuning/broker/service.ts:180` |
| `fine_tuning` | `method` | `ServiceProcessor.modelUsage` | `src.ts/sdk/fine-tuning/broker/service.ts:363` |
| `fine_tuning` | `method` | `ServiceProcessor.removeService` | `src.ts/sdk/fine-tuning/broker/service.ts:208` |
| `fine_tuning` | `method` | `ServiceProcessor.revokeTEESignerAcknowledgement` | `src.ts/sdk/fine-tuning/broker/service.ts:194` |
| `fine_tuning` | `interface` | `StorageConfig` | `src.ts/sdk/fine-tuning/zg-storage/zg-storage.ts:7` |
| `fine_tuning` | `constant` | `AUTOMATA_ABI` | `src.ts/sdk/fine-tuning/const.ts:117` |
| `fine_tuning` | `constant` | `AUTOMATA_RPC` | `src.ts/sdk/fine-tuning/const.ts:112` |
| `fine_tuning` | `constant` | `INDEXER_URL_MAINNET_STANDARD` | `src.ts/sdk/fine-tuning/const.ts:9` |
| `fine_tuning` | `constant` | `INDEXER_URL_MAINNET_TURBO` | `src.ts/sdk/fine-tuning/const.ts:11` |
| `fine_tuning` | `constant` | `INDEXER_URL_TESTNET_STANDARD` | `src.ts/sdk/fine-tuning/const.ts:3` |
| `fine_tuning` | `constant` | `INDEXER_URL_TESTNET_TURBO` | `src.ts/sdk/fine-tuning/const.ts:5` |
| `fine_tuning` | `constant` | `TESTNET_DEV_MODELS` | `src.ts/sdk/fine-tuning/const.ts:85` |
| `fine_tuning` | `constant` | `TOKEN_COUNTER_FILE_HASH` | `src.ts/sdk/fine-tuning/const.ts:16` |
| `fine_tuning` | `constant` | `TOKEN_COUNTER_MERKLE_ROOT` | `src.ts/sdk/fine-tuning/const.ts:12` |
| `fine_tuning` | `constant` | `ZG_RPC_ENDPOINT_MAINNET` | `src.ts/sdk/fine-tuning/const.ts:8` |
| `fine_tuning` | `constant` | `ZG_RPC_ENDPOINT_TESTNET` | `src.ts/sdk/fine-tuning/const.ts:2` |
| `fine_tuning` | `re_export` | `FineTuningServiceStructOutput` | `src.ts/sdk/fine-tuning/index.ts:1` |
| `fine_tuning` | `re_export` | `createFineTuningBroker` | `src.ts/sdk/fine-tuning/index.ts:2` |
| `inference` | `class` | `AccountProcessor` | `src.ts/sdk/inference/broker/account.ts:9` |
| `inference` | `class` | `InferenceBroker` | `src.ts/sdk/inference/broker/broker.ts:30` |
| `inference` | `class` | `InferenceServingContract` | `src.ts/sdk/inference/contract/inference.ts:13` |
| `inference` | `class` | `ReadOnlyInferenceServingContract` | `src.ts/sdk/inference/contract/read-only-inference.ts:6` |
| `inference` | `class` | `ReadOnlyModelProcessor` | `src.ts/sdk/inference/broker/read-only-model.ts:281` |
| `inference` | `class` | `RequestProcessor` | `src.ts/sdk/inference/broker/request.ts:50` |

Showing first `80` of `195` items. See JSON for the full list.

## Needs Manual Review

| TypeScript | Python | Reason |
| --- | --- | --- |
| `ZGComputeNetworkBroker`<br>`src.ts/sdk/broker.ts:31` | `ZGComputeNetworkBroker`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ZGComputeNetworkReadOnlyBroker`<br>`src.ts/sdk/broker.ts:171` | `ZGComputeNetworkReadOnlyBroker`<br>`0g_py_inference/zerog_py_sdk/read_only.py:564` | `name_only` |
| `createZGComputeNetworkBroker`<br>`src.ts/sdk/broker.ts:66` | `create_zg_compute_network_broker`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `createZGComputeNetworkReadOnlyBroker`<br>`src.ts/sdk/broker.ts:212` | `create_zg_compute_network_read_only_broker`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `CONTRACT_ADDRESSES`<br>`src.ts/sdk/broker.ts:23` | `CONTRACT_ADDRESSES`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `HARDHAT_CHAIN_ID`<br>`src.ts/sdk/broker.ts:23` | `HARDHAT_CHAIN_ID`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `MAINNET_CHAIN_ID`<br>`src.ts/sdk/broker.ts:23` | `MAINNET_CHAIN_ID`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `TESTNET_CHAIN_ID`<br>`src.ts/sdk/broker.ts:23` | `TESTNET_CHAIN_ID`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `isDevMode`<br>`src.ts/sdk/broker.ts:23` | `is_dev_mode`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ChatBot`<br>`src.ts/sdk/inference/extractor/chatbot.ts:3` | `ChatBot`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ImageEditing`<br>`src.ts/sdk/inference/extractor/imageEditing.ts:3` | `ImageEditing`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `SpeechToText`<br>`src.ts/sdk/inference/extractor/speech-to-text.ts:3` | `SpeechToText`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `TextToImage`<br>`src.ts/sdk/inference/extractor/textToImage.ts:3` | `TextToImage`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `AUTOMATA_CONTRACT_ADDRESS`<br>`src.ts/sdk/fine-tuning/const.ts:114` | `AUTOMATA_CONTRACT_ADDRESS`<br>`0g_py_inference/zerog_py_sdk/contracts/__init__.py:16` | `name_only` |
| `AttestationReport`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:7` | `AttestationReport`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ComposeVerificationResult`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:23` | `ComposeVerificationResult`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `EventLogEntry`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:17` | `EventLogEntry`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `SignerReportMatch`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:36` | `SignerReportMatch`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `VerificationResult`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:42` | `VerificationResult`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `VerificationStep`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:31` | `VerificationStep`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `VerificationSummary`<br>`src.ts/sdk/fine-tuning/broker/verifier.ts:63` | `VerificationSummary`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ModelProcessor`<br>`src.ts/sdk/inference/broker/model.ts:34` | `ModelProcessor`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/broker/model.py:16` | `name_only` |
| `ReadOnlyInferenceBroker`<br>`src.ts/sdk/inference/broker/read-only-broker.ts:22` | `ReadOnlyInferenceBroker`<br>`0g_py_inference/zerog_py_sdk/read_only.py:241` | `name_only` |
| `EPHEMERAL_TOKEN_ID`<br>`src.ts/sdk/inference/broker/base.ts:30` | `EPHEMERAL_TOKEN_ID`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `EPHEMERAL_TOKEN_MAX_DURATION`<br>`src.ts/sdk/inference/broker/base.ts:36` | `EPHEMERAL_TOKEN_MAX_DURATION`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `SessionMode`<br>`src.ts/sdk/inference/broker/base.ts:41` | `SessionMode`<br>`0g_py_inference/zerog_py_sdk/session.py:28` | `name_only` |
| `VerifiabilityEnum`<br>`src.ts/sdk/inference/broker/read-only-model.ts:5` | `VerifiabilityEnum`<br>`0g_py_inference/zerog_py_sdk/read_only.py:28` | `name_only` |
| `isVerifiability`<br>`src.ts/sdk/inference/broker/read-only-model.ts:453` | `is_verifiability`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `parseCacheTokenBilling`<br>`src.ts/sdk/inference/broker/read-only-model.ts:219` | `parse_cache_token_billing`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `parseCacheTokenBillingFromModelInfo`<br>`src.ts/sdk/inference/broker/read-only-model.ts:241` | `parse_cache_token_billing_from_model_info`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `parseTieredPricing`<br>`src.ts/sdk/inference/broker/read-only-model.ts:148` | `parse_tiered_pricing`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `parseTieredPricingFromModelInfo`<br>`src.ts/sdk/inference/broker/read-only-model.ts:183` | `parse_tiered_pricing_from_model_info`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `ApiKeyInfo`<br>`src.ts/sdk/inference/broker/base.ts:67` | `ApiKeyInfo`<br>`0g_py_inference/zerog_py_sdk/session.py:67` | `name_only` |
| `AutoFundingConfig`<br>`src.ts/sdk/inference/broker/base.ts:96` | `AutoFundingConfig`<br>`0g_py_inference/zerog_py_sdk/models.py:240` | `name_only` |
| `CacheTokenBillingInfo`<br>`src.ts/sdk/inference/broker/read-only-model.ts:211` | `CacheTokenBillingInfo`<br>`0g_py_inference/zerog_py_sdk/read_only.py:74` | `name_only` |
| `CachedSession`<br>`src.ts/sdk/inference/broker/base.ts:57` | `CachedSession`<br>`0g_py_inference/zerog_py_sdk/session.py:59` | `name_only` |
| `PricingTier`<br>`src.ts/sdk/inference/broker/read-only-model.ts:131` | `PricingTier`<br>`0g_py_inference/zerog_py_sdk/read_only.py:58` | `name_only` |
| `ProviderModelInfo`<br>`src.ts/sdk/inference/broker/read-only-model.ts:53` | `ProviderModelInfo`<br>`0g_py_inference/zerog_py_sdk/read_only.py:81` | `name_only` |
| `ServiceWithDetail`<br>`src.ts/sdk/inference/broker/read-only-model.ts:254` | `ServiceWithDetail`<br>`0g_py_inference/zerog_py_sdk/read_only.py:132` | `name_only` |
| `ServingRequestHeaders`<br>`src.ts/sdk/inference/broker/request.ts:13` | `ServingRequestHeaders`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |
| `SessionToken`<br>`src.ts/sdk/inference/broker/base.ts:47` | `SessionToken`<br>`0g_py_inference/zerog_py_sdk/session.py:35` | `name_only` |
| `TdxQuoteResponse`<br>`src.ts/sdk/inference/broker/base.ts:18` | `TdxQuoteResponse`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:144` | `name_only` |
| `TieredPricingInfo`<br>`src.ts/sdk/inference/broker/read-only-model.ts:140` | `TieredPricingInfo`<br>`0g_py_inference/zerog_py_sdk/read_only.py:67` | `name_only` |
| `ReadOnlyInferenceBroker.listService`<br>`src.ts/sdk/inference/broker/read-only-broker.ts:45` | `ReadOnlyInferenceBroker.list_service`<br>`0g_py_inference/zerog_py_sdk/read_only.py:287` | `name_only` |
| `ReadOnlyInferenceBroker.listServiceWithDetail`<br>`src.ts/sdk/inference/broker/read-only-broker.ts:78` | `ReadOnlyInferenceBroker.list_service_with_detail`<br>`0g_py_inference/zerog_py_sdk/read_only.py:348` | `name_only` |
| `HealthStatus`<br>`src.ts/sdk/inference/broker/read-only-model.ts:16` | `HealthStatus`<br>`0g_py_inference/zerog_py_sdk/read_only.py:40` | `name_only` |
| `ChatResponse`<br>`src.ts/sdk/inference/broker/lora.ts:40` | `ChatResponse`<br>`0g_py_inference/zerog_py_sdk/models.py:121` | `name_only` |
| `aesGCMDecryptToFile`<br>`src.ts/sdk/common/utils/encrypt.ts:116` | `aes_gcm_decrypt_to_file`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/crypto/__init__.py:4` | `name_only` |
| `eciesDecrypt`<br>`src.ts/sdk/common/utils/encrypt.ts:67` | `ecies_decrypt`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/crypto/__init__.py:4` | `name_only` |
| `getNonce`<br>`src.ts/sdk/common/utils/nonce.ts:1` | `get_nonce`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` | `name_only` |
| `makeAdapterName`<br>`src.ts/sdk/common/utils/adapter-name.ts:5` | `make_adapter_name`<br>`0g_py_inference/zerog_py_sdk/lora.py:56` | `name_only` |
| `signDatasetUpload`<br>`src.ts/sdk/common/utils/encrypt.ts:58` | `sign_dataset_upload`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` | `name_only` |
| `signRequest`<br>`src.ts/sdk/common/utils/encrypt.ts:21` | `sign_request`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` | `name_only` |
| `signTaskID`<br>`src.ts/sdk/common/utils/encrypt.ts:35` | `sign_task_id`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` | `name_only` |
| `Verifier`<br>`src.ts/sdk/inference/broker/verifier.ts:109` | `Verifier`<br>`0g_py_inference/zerog_py_sdk/fine_tuning/broker/verifier.py:15` | `name_only` |
| `AdditionalInfo`<br>`src.ts/sdk/inference/broker/verifier.ts:64` | `AdditionalInfo`<br>`0g_py_inference/zerog_py_sdk/models.py:253` | `name_only` |
| `ProviderType`<br>`src.ts/sdk/inference/broker/verifier.ts:62` | `ProviderType`<br>`0g_py_inference/zerog_py_sdk/__init__.py:153` | `name_only` |

## Python Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `auth_session` | `class` | `AuthManager` | `0g_py_inference/zerog_py_sdk/auth.py:100` |
| `auth_session` | `class` | `Request` | `0g_py_inference/zerog_py_sdk/auth.py:29` |
| `auth_session` | `class` | `SessionManager` | `0g_py_inference/zerog_py_sdk/session.py:75` |
| `auth_session` | `method` | `AuthManager.generate_request_headers` | `0g_py_inference/zerog_py_sdk/auth.py:122` |
| `auth_session` | `method` | `AuthManager.verify_response` | `0g_py_inference/zerog_py_sdk/auth.py:189` |
| `auth_session` | `method` | `Request.serialize` | `0g_py_inference/zerog_py_sdk/auth.py:51` |
| `auth_session` | `method` | `Request.to_dict` | `0g_py_inference/zerog_py_sdk/auth.py:90` |
| `auth_session` | `method` | `SessionManager.clear_session_cache` | `0g_py_inference/zerog_py_sdk/session.py:326` |
| `auth_session` | `method` | `SessionManager.create_api_key` | `0g_py_inference/zerog_py_sdk/session.py:246` |
| `auth_session` | `method` | `SessionManager.generate_session_token` | `0g_py_inference/zerog_py_sdk/session.py:100` |
| `auth_session` | `method` | `SessionManager.get_or_create_session` | `0g_py_inference/zerog_py_sdk/session.py:195` |
| `auth_session` | `method` | `SessionManager.get_request_headers` | `0g_py_inference/zerog_py_sdk/session.py:219` |
| `auth_session` | `method` | `SessionToken.to_dict` | `0g_py_inference/zerog_py_sdk/session.py:45` |
| `broker` | `class` | `ZGServingBroker` | `0g_py_inference/zerog_py_sdk/broker.py:27` |
| `broker` | `function` | `create_broker` | `0g_py_inference/zerog_py_sdk/broker.py:171` |
| `broker` | `function` | `create_broker_from_env` | `0g_py_inference/zerog_py_sdk/broker.py:263` |
| `broker` | `method` | `ZGServingBroker.fine_tuning` | `0g_py_inference/zerog_py_sdk/broker.py:148` |
| `broker` | `method` | `ZGServingBroker.get_address` | `0g_py_inference/zerog_py_sdk/broker.py:161` |
| `broker` | `method` | `ZGServingBroker.inference` | `0g_py_inference/zerog_py_sdk/broker.py:134` |
| `broker` | `method` | `ZGServingBroker.ledger` | `0g_py_inference/zerog_py_sdk/broker.py:119` |
| `extractors` | `class` | `ChatBotExtractor` | `0g_py_inference/zerog_py_sdk/extractors.py:86` |
| `extractors` | `class` | `ImageEditingExtractor` | `0g_py_inference/zerog_py_sdk/extractors.py:177` |
| `extractors` | `class` | `SpeechToTextExtractor` | `0g_py_inference/zerog_py_sdk/extractors.py:217` |
| `extractors` | `class` | `TextToImageExtractor` | `0g_py_inference/zerog_py_sdk/extractors.py:137` |
| `extractors` | `function` | `create_extractor` | `0g_py_inference/zerog_py_sdk/extractors.py:257` |
| `extractors` | `method` | `ChatBotExtractor.get_input_count` | `0g_py_inference/zerog_py_sdk/extractors.py:98` |
| `extractors` | `method` | `ChatBotExtractor.get_output_count` | `0g_py_inference/zerog_py_sdk/extractors.py:117` |
| `extractors` | `method` | `Extractor.get_input_count` | `0g_py_inference/zerog_py_sdk/extractors.py:60` |
| `extractors` | `method` | `Extractor.get_output_count` | `0g_py_inference/zerog_py_sdk/extractors.py:73` |
| `extractors` | `method` | `Extractor.get_svc_info` | `0g_py_inference/zerog_py_sdk/extractors.py:50` |
| `extractors` | `method` | `ImageEditingExtractor.get_input_count` | `0g_py_inference/zerog_py_sdk/extractors.py:189` |
| `extractors` | `method` | `ImageEditingExtractor.get_output_count` | `0g_py_inference/zerog_py_sdk/extractors.py:208` |
| `extractors` | `method` | `SpeechToTextExtractor.get_input_count` | `0g_py_inference/zerog_py_sdk/extractors.py:229` |
| `extractors` | `method` | `SpeechToTextExtractor.get_output_count` | `0g_py_inference/zerog_py_sdk/extractors.py:237` |
| `extractors` | `method` | `TextToImageExtractor.get_input_count` | `0g_py_inference/zerog_py_sdk/extractors.py:149` |
| `extractors` | `method` | `TextToImageExtractor.get_output_count` | `0g_py_inference/zerog_py_sdk/extractors.py:168` |
| `fine_tuning` | `class` | `Deliverable` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:23` |
| `fine_tuning` | `class` | `FineTuningAccountDetails` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:33` |
| `fine_tuning` | `class` | `FineTuningContract` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/contract.py:28` |
| `fine_tuning` | `class` | `FineTuningProvider` | `0g_py_inference/zerog_py_sdk/fine_tuning/provider/provider.py:19` |
| `fine_tuning` | `class` | `FineTuningRefund` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:15` |
| `fine_tuning` | `class` | `FineTuningService` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:59` |
| `fine_tuning` | `class` | `Quota` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:6` |
| `fine_tuning` | `export` | `Deliverable` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `Deliverable` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `FineTuningAccountDetails` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `FineTuningAccountDetails` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `FineTuningContract` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `FineTuningContract` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `FineTuningProvider` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `FineTuningProvider` | `0g_py_inference/zerog_py_sdk/fine_tuning/provider/__init__.py:3` |
| `fine_tuning` | `export` | `FineTuningRefund` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `FineTuningRefund` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `FineTuningService` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `FineTuningService` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `FineTuningVerifier` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `Quota` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `Quota` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/__init__.py:11` |
| `fine_tuning` | `export` | `get_model_config` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `export` | `get_storage_config` | `0g_py_inference/zerog_py_sdk/fine_tuning/__init__.py:30` |
| `fine_tuning` | `function` | `get_model_config` | `0g_py_inference/zerog_py_sdk/fine_tuning/constants.py:60` |
| `fine_tuning` | `function` | `get_storage_config` | `0g_py_inference/zerog_py_sdk/fine_tuning/constants.py:68` |
| `fine_tuning` | `method` | `CustomizedModel.from_dict` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:131` |
| `fine_tuning` | `method` | `DatasetProcessor.upload_dataset_to_tee` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/dataset.py:18` |
| `fine_tuning` | `method` | `FineTuningAccountDetails.locked_balance` | `0g_py_inference/zerog_py_sdk/fine_tuning/contract/types.py:48` |
| `fine_tuning` | `method` | `FineTuningBroker.acknowledge_deliverable` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:318` |
| `fine_tuning` | `method` | `FineTuningBroker.acknowledge_model` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:295` |
| `fine_tuning` | `method` | `FineTuningBroker.acknowledge_provider_signer` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:160` |
| `fine_tuning` | `method` | `FineTuningBroker.acknowledge_tee_signer_by_owner` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:170` |
| `fine_tuning` | `method` | `FineTuningBroker.calculate_token` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:279` |
| `fine_tuning` | `method` | `FineTuningBroker.cancel_task` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:219` |
| `fine_tuning` | `method` | `FineTuningBroker.create_task` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:200` |
| `fine_tuning` | `method` | `FineTuningBroker.decrypt_model` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:368` |
| `fine_tuning` | `method` | `FineTuningBroker.download_dataset` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:273` |
| `fine_tuning` | `method` | `FineTuningBroker.download_lora_from_tee` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:331` |
| `fine_tuning` | `method` | `FineTuningBroker.download_model_from_0g_storage` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:350` |
| `fine_tuning` | `method` | `FineTuningBroker.download_model_usage` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:128` |
| `fine_tuning` | `method` | `FineTuningBroker.get_account` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:140` |
| `fine_tuning` | `method` | `FineTuningBroker.get_account_with_detail` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:146` |
| `fine_tuning` | `method` | `FineTuningBroker.get_customized_model` | `0g_py_inference/zerog_py_sdk/fine_tuning/broker/broker.py:118` |

Showing first `80` of `360` items. See JSON for the full list.

## Maintainer Notes

- Treat `missing_in_python` feature probes and `TypeScript Only` classes/functions/methods as triage candidates.
- A match here means the public names look aligned; it does not prove behavior parity.
- For high-risk areas like auth, billing, response verification, and fine-tuning, follow up with source-level review and parity tests.
