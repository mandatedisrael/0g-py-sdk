# Storage SDK Parity Report

Generated: `2026-05-17T15:55:48.617089+00:00`
Upstream: `0g-storage-ts-starter` `2.0.0`
Commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3`
Source path: `/Users/damiafo/Documents/projects/og-py-sdk/.cache/storage_ts_starter_kit`
Scope: `sdk`

## Summary

- TypeScript surface items: `42`
- Python surface items: `347`
- Matched items: `3`
- Needs review: `2`
- Present in TS only: `34`
- Present in Python only: `343`
- Missing feature probes: `2`

## Feature Probes

| Status | Feature | TS Evidence | Python Evidence |
| --- | --- | --- | --- |
| matched | File upload | `uploadFile, Indexer, ZgFile\.fromFilePath` | `upload, Indexer, ZgFile\.from_file_path` |
| matched | File download | `downloadFile, indexer\.download, downloadToBlob` | `download, Downloader, download_segment` |
| matched | In-memory data upload | `uploadData, MemData` | `from_bytes, ZgFile\.from_bytes` |
| matched | Batch upload wrapper | `batchUpload, batch-upload` | `splitable_upload, Uploader` |
| missing_in_python | Client-side encryption | `aes256, ecies, EncryptionHeader` | `-` |
| missing_in_python | Encryption header peek | `peekHeader, peek-header` | `-` |
| needs_review | Network and storage modes | `StorageMode, turbo, standard` | `turbo` |
| matched | Merkle roots and proofs | `merkleTree, rootHash, proof` | `merkle_tree, root_hash, Proof` |
| matched | KV storage | `key-value, stream` | `KvClient, Batcher, StreamDataBuilder` |

## Coding Agent Brief

Use this section as the handoff for implementation or review work.

- Upstream commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3`
- Upstream package: `0g-storage-ts-starter` `2.0.0`
- Compare scope: `sdk`
- Python root: `0g_py_storage`
- Treat every action item as a hypothesis from static analysis, then confirm from source before coding.

### Prioritized Action Items

#### 1. P1 - Client-side encryption

- Status: `missing_in_python`
- Why: Upstream evidence was found, but the checker found no matching Python evidence.
- Suggested next step: Start by reading the upstream implementation for Client-side encryption, then decide whether to port it into Python.
- Upstream evidence patterns: `aes256, ecies, EncryptionHeader`
- Python evidence patterns: `-`

Upstream refs:
- `EncryptionHeader` in `src/index.ts:39`
- `generateAes256Key` in `src/index.ts:15`
- `batchUpload` in `src/storage.ts:259`
- `downloadFile` in `src/storage.ts:152`
- `peekHeader` in `src/storage.ts:198`
- `uploadData` in `src/storage.ts:214`
- `uploadFile` in `src/storage.ts:99`
- `generateAes256Key` in `src/config.ts:125`

Likely Python refs:
- `Downloader` in `0g_py_storage/core/downloader.py:23`
- `download` in `0g_py_storage/simple_download.py:19`
- `main` in `0g_py_storage/test_download.py:22`
- `Downloader.check_exist` in `0g_py_storage/core/downloader.py:381`
- `Downloader.download` in `0g_py_storage/core/downloader.py:49`
- `Downloader.download_file` in `0g_py_storage/core/downloader.py:148`
- `Downloader.download_file_helper` in `0g_py_storage/core/downloader.py:317`
- `Downloader.download_fragments` in `0g_py_storage/core/downloader.py:75`

Name-only matches to inspect:
- TS `hexToBytes`<br>`src/index.ts:15` -> Python `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64`

Acceptance criteria:
- Confirm whether the upstream behavior is a real Python SDK parity requirement.
- If porting, implement the Python API or behavior with tests and docs/examples where user-facing.
- If already covered or intentionally different, update the parity tracker with the decision and rationale.
- Rerun this parity checker and the relevant Python test suite after changes.

#### 2. P1 - Encryption header peek

- Status: `missing_in_python`
- Why: Upstream evidence was found, but the checker found no matching Python evidence.
- Suggested next step: Start by reading the upstream implementation for Encryption header peek, then decide whether to port it into Python.
- Upstream evidence patterns: `peekHeader, peek-header`
- Python evidence patterns: `-`

Upstream refs:
- `peekHeader` in `src/storage.ts:198`
- `peekHeader` in `src/index.ts:2`
- `batchUpload` in `src/storage.ts:259`
- `downloadFile` in `src/storage.ts:152`
- `uploadData` in `src/storage.ts:214`
- `uploadFile` in `src/storage.ts:99`
- `DownloadResult` in `src/storage.ts:27`
- `UploadResult` in `src/storage.ts:22`

Likely Python refs:
- `Downloader` in `0g_py_storage/core/downloader.py:23`
- `download` in `0g_py_storage/simple_download.py:19`
- `main` in `0g_py_storage/test_download.py:22`
- `Downloader.check_exist` in `0g_py_storage/core/downloader.py:381`
- `Downloader.download` in `0g_py_storage/core/downloader.py:49`
- `Downloader.download_file` in `0g_py_storage/core/downloader.py:148`
- `Downloader.download_file_helper` in `0g_py_storage/core/downloader.py:317`
- `Downloader.download_fragments` in `0g_py_storage/core/downloader.py:75`

Name-only matches to inspect:
- TS `hexToBytes`<br>`src/index.ts:15` -> Python `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64`

Acceptance criteria:
- Confirm whether the upstream behavior is a real Python SDK parity requirement.
- If porting, implement the Python API or behavior with tests and docs/examples where user-facing.
- If already covered or intentionally different, update the parity tracker with the decision and rationale.
- Rerun this parity checker and the relevant Python test suite after changes.

#### 3. P2 - Network and storage modes

- Status: `needs_review`
- Why: Both sides have some evidence, but the match is incomplete or name-only and needs source review.
- Suggested next step: Compare the upstream and Python implementations for Network and storage modes; decide whether the Python behavior is complete.
- Upstream evidence patterns: `StorageMode, turbo, standard`
- Python evidence patterns: `turbo`

Upstream refs:
- `StorageMode` in `src/config.ts:8`
- `createIndexer` in `src/config.ts:169`
- `createSigner` in `src/config.ts:161`
- `generateAes256Key` in `src/config.ts:125`
- `getConfig` in `src/config.ts:92`
- `getNetwork` in `src/config.ts:65`
- `pubKeyFromPrivateKey` in `src/config.ts:130`
- `NETWORKS` in `src/config.ts:50`

Likely Python refs:
- `Indexer` in `0g_py_storage/core/indexer.py:28`
- `SegmentTreeNode` in `0g_py_storage/core/node_selector.py:17`
- `StorageNode` in `0g_py_storage/core/storage_node.py:17`
- `check_replica` in `0g_py_storage/core/node_selector.py:181`
- `insert` in `0g_py_storage/core/node_selector.py:65`
- `is_valid_config` in `0g_py_storage/core/node_selector.py:219`
- `pushdown` in `0g_py_storage/core/node_selector.py:37`
- `select_nodes` in `0g_py_storage/core/node_selector.py:124`

Name-only matches to inspect:
- TS `hexToBytes`<br>`src/config.ts:112` -> Python `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64`

Acceptance criteria:
- Confirm whether the upstream behavior is a real Python SDK parity requirement.
- If porting, implement the Python API or behavior with tests and docs/examples where user-facing.
- If already covered or intentionally different, update the parity tracker with the decision and rationale.
- Rerun this parity checker and the relevant Python test suite after changes.


## TypeScript Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `config` | `function` | `createIndexer` | `src/config.ts:169` |
| `config` | `function` | `createSigner` | `src/config.ts:161` |
| `config` | `function` | `generateAes256Key` | `src/config.ts:125` |
| `config` | `function` | `getConfig` | `src/config.ts:92` |
| `config` | `function` | `getNetwork` | `src/config.ts:65` |
| `config` | `function` | `pubKeyFromPrivateKey` | `src/config.ts:130` |
| `config` | `interface` | `AppConfig` | `src/config.ts:27` |
| `config` | `interface` | `ConfigOverrides` | `src/config.ts:84` |
| `config` | `interface` | `DecryptionConfig` | `src/config.ts:22` |
| `config` | `interface` | `NetworkConfig` | `src/config.ts:9` |
| `config` | `type` | `EncryptionConfig` | `src/config.ts:18` |
| `config` | `type` | `NetworkName` | `src/config.ts:6` |
| `config` | `type` | `StorageMode` | `src/config.ts:8` |
| `config` | `constant` | `NETWORKS` | `src/config.ts:50` |
| `shared` | `function` | `batchUpload` | `src/storage.ts:259` |
| `shared` | `function` | `downloadFile` | `src/storage.ts:152` |
| `shared` | `function` | `peekHeader` | `src/storage.ts:198` |
| `shared` | `function` | `uploadData` | `src/storage.ts:214` |
| `shared` | `function` | `uploadFile` | `src/storage.ts:99` |
| `shared` | `interface` | `DownloadResult` | `src/storage.ts:27` |
| `shared` | `interface` | `UploadResult` | `src/storage.ts:22` |
| `shared` | `re_export` | `EncryptionHeader` | `src/index.ts:39` |
| `shared` | `re_export` | `NETWORKS` | `src/index.ts:15` |
| `shared` | `re_export` | `batchUpload` | `src/index.ts:2` |
| `shared` | `re_export` | `createIndexer` | `src/index.ts:15` |
| `shared` | `re_export` | `createSigner` | `src/index.ts:15` |
| `shared` | `re_export` | `downloadFile` | `src/index.ts:2` |
| `shared` | `re_export` | `generateAes256Key` | `src/index.ts:15` |
| `shared` | `re_export` | `getConfig` | `src/index.ts:15` |
| `shared` | `re_export` | `getNetwork` | `src/index.ts:15` |
| `shared` | `re_export` | `peekHeader` | `src/index.ts:2` |
| `shared` | `re_export` | `pubKeyFromPrivateKey` | `src/index.ts:15` |
| `shared` | `re_export` | `uploadData` | `src/index.ts:2` |
| `shared` | `re_export` | `uploadFile` | `src/index.ts:2` |

## Needs Manual Review

| TypeScript | Python | Reason |
| --- | --- | --- |
| `hexToBytes`<br>`src/config.ts:112` | `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64` | `name_only` |
| `hexToBytes`<br>`src/index.ts:15` | `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64` | `name_only` |

## Python Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `contracts` | `class` | `FlowContract` | `0g_py_storage/contracts/flow.py:15` |
| `contracts` | `export` | `FLOW_CONTRACT_ABI` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `export` | `FlowContract` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `export` | `MAINNET_FLOW_ADDRESS` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `export` | `NETWORK_ADDRESSES` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `export` | `TESTNET_FLOW_ADDRESS` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `export` | `get_flow_contract_address` | `0g_py_storage/contracts/__init__.py:12` |
| `contracts` | `function` | `get_flow_contract_address` | `0g_py_storage/contracts/abis.py:280` |
| `contracts` | `method` | `FlowContract.batch_submit` | `0g_py_storage/contracts/flow.py:131` |
| `contracts` | `method` | `FlowContract.create_submission` | `0g_py_storage/contracts/flow.py:309` |
| `contracts` | `method` | `FlowContract.get_submission_info` | `0g_py_storage/contracts/flow.py:248` |
| `contracts` | `method` | `FlowContract.process_logs` | `0g_py_storage/contracts/flow.py:193` |
| `contracts` | `method` | `FlowContract.submit` | `0g_py_storage/contracts/flow.py:52` |
| `contracts` | `method` | `FlowContract.wait_for_receipt` | `0g_py_storage/contracts/flow.py:273` |
| `data` | `class` | `AbstractFile` | `0g_py_storage/core/file.py:279` |
| `data` | `class` | `FileFdIterator` | `0g_py_storage/core/file.py:226` |
| `data` | `class` | `FileInfo` | `0g_py_storage/models/file.py:79` |
| `data` | `class` | `FileIterator` | `0g_py_storage/core/file.py:42` |
| `data` | `class` | `FileProof` | `0g_py_storage/models/file.py:18` |
| `data` | `class` | `FlowProof` | `0g_py_storage/models/file.py:151` |
| `data` | `class` | `KeyValue` | `0g_py_storage/models/file.py:132` |
| `data` | `class` | `MemIterator` | `0g_py_storage/core/file.py:181` |
| `data` | `class` | `Metadata` | `0g_py_storage/models/file.py:98` |
| `data` | `class` | `SegmentWithProof` | `0g_py_storage/models/file.py:33` |
| `data` | `class` | `Transaction` | `0g_py_storage/models/file.py:54` |
| `data` | `class` | `Value` | `0g_py_storage/models/file.py:115` |
| `data` | `class` | `ZgFile` | `0g_py_storage/core/file.py:623` |
| `data` | `function` | `compute_padded_size` | `0g_py_storage/utils/file_utils.py:36` |
| `data` | `function` | `iterator_padded_size` | `0g_py_storage/utils/file_utils.py:72` |
| `data` | `function` | `next_pow2` | `0g_py_storage/utils/file_utils.py:18` |
| `data` | `function` | `num_splits` | `0g_py_storage/utils/file_utils.py:9` |
| `data` | `method` | `AbstractFile.create_fragment` | `0g_py_storage/core/file.py:325` |
| `data` | `method` | `AbstractFile.create_node` | `0g_py_storage/core/file.py:534` |
| `data` | `method` | `AbstractFile.create_segment_node` | `0g_py_storage/core/file.py:561` |
| `data` | `method` | `AbstractFile.create_submission` | `0g_py_storage/core/file.py:460` |
| `data` | `method` | `AbstractFile.iterate` | `0g_py_storage/core/file.py:388` |
| `data` | `method` | `AbstractFile.iterate_with_offset_and_batch` | `0g_py_storage/core/file.py:397` |
| `data` | `method` | `AbstractFile.merkle_tree` | `0g_py_storage/core/file.py:410` |
| `data` | `method` | `AbstractFile.num_chunks` | `0g_py_storage/core/file.py:444` |
| `data` | `method` | `AbstractFile.num_segments` | `0g_py_storage/core/file.py:452` |
| `data` | `method` | `AbstractFile.padded_size` | `0g_py_storage/core/file.py:292` |
| `data` | `method` | `AbstractFile.segment_root` | `0g_py_storage/core/file.py:344` |
| `data` | `method` | `AbstractFile.size` | `0g_py_storage/core/file.py:380` |
| `data` | `method` | `AbstractFile.split` | `0g_py_storage/core/file.py:300` |
| `data` | `method` | `AbstractFile.split_nodes` | `0g_py_storage/core/file.py:502` |
| `data` | `method` | `FileFdIterator.read_from_file` | `0g_py_storage/core/file.py:249` |
| `data` | `method` | `FileIterator.clear_buffer` | `0g_py_storage/core/file.py:100` |
| `data` | `method` | `FileIterator.current` | `0g_py_storage/core/file.py:172` |
| `data` | `method` | `FileIterator.next` | `0g_py_storage/core/file.py:121` |
| `data` | `method` | `FileIterator.padding_zeros` | `0g_py_storage/core/file.py:108` |
| `data` | `method` | `FileIterator.read_from_file` | `0g_py_storage/core/file.py:92` |
| `data` | `method` | `MemIterator.read_from_file` | `0g_py_storage/core/file.py:204` |
| `data` | `method` | `ZgFile.close` | `0g_py_storage/core/file.py:744` |
| `data` | `method` | `ZgFile.create_fragment` | `0g_py_storage/core/file.py:692` |
| `data` | `method` | `ZgFile.from_bytes` | `0g_py_storage/core/file.py:671` |
| `data` | `method` | `ZgFile.from_file_path` | `0g_py_storage/core/file.py:645` |
| `data` | `method` | `ZgFile.iterate_with_offset_and_batch` | `0g_py_storage/core/file.py:753` |
| `download` | `class` | `Downloader` | `0g_py_storage/core/downloader.py:23` |
| `download` | `function` | `download` | `0g_py_storage/simple_download.py:19` |
| `download` | `function` | `main` | `0g_py_storage/test_download.py:22` |

Showing first `60` of `343` items. See JSON for the full list.

## Maintainer Notes

- Treat `missing_in_python` feature probes and `TypeScript Only` classes/functions/methods as triage candidates.
- A match here means the public names look aligned; it does not prove behavior parity.
- For high-risk areas like upload/download semantics, encryption wire format, network config, and proof verification, follow up with source-level review and parity tests.
