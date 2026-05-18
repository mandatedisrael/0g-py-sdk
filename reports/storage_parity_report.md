# Storage SDK Parity Report

Generated: `2026-05-18T17:45:25.872750+00:00`
Upstream: `0g-storage-ts-starter` `2.0.0`
Commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3`
Source path: `/Users/damiafo/Documents/projects/og-py-sdk/.cache/storage_ts_starter_kit`
Scope: `sdk`

## Summary

- TypeScript surface items: `42`
- Python surface items: `384`
- Matched items: `10`
- Needs review: `5`
- Present in TS only: `24`
- Present in Python only: `372`
- Missing feature probes: `0`

## Feature Probes

| Status | Feature | TS Evidence | Python Evidence |
| --- | --- | --- | --- |
| matched | File upload | `uploadFile, Indexer, ZgFile\.fromFilePath` | `upload, Indexer, ZgFile\.from_file_path` |
| matched | File download | `downloadFile, indexer\.download, downloadToBlob` | `download, Downloader, download_segment` |
| matched | In-memory data upload | `uploadData, MemData` | `from_bytes, ZgFile\.from_bytes` |
| matched | Batch upload wrapper | `batchUpload, batch-upload` | `splitable_upload, Uploader` |
| matched | Client-side encryption | `aes256, ecies, EncryptionHeader` | `aes256, ecies, EncryptionHeader` |
| matched | Encryption header peek | `peekHeader, peek-header` | `peek_header, EncryptionHeader` |
| matched | Network and storage modes | `StorageMode, turbo, standard` | `turbo, standard, indexer-storage-testnet-standard` |
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

No missing or partial feature probes were detected. Review the TypeScript-only surface table for lower-priority drift.

## TypeScript Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `config` | `function` | `createIndexer` | `src/config.ts:169` |
| `config` | `function` | `createSigner` | `src/config.ts:161` |
| `config` | `function` | `generateAes256Key` | `src/config.ts:125` |
| `config` | `function` | `pubKeyFromPrivateKey` | `src/config.ts:130` |
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
| `shared` | `re_export` | `NETWORKS` | `src/index.ts:15` |
| `shared` | `re_export` | `batchUpload` | `src/index.ts:2` |
| `shared` | `re_export` | `createIndexer` | `src/index.ts:15` |
| `shared` | `re_export` | `createSigner` | `src/index.ts:15` |
| `shared` | `re_export` | `downloadFile` | `src/index.ts:2` |
| `shared` | `re_export` | `generateAes256Key` | `src/index.ts:15` |
| `shared` | `re_export` | `peekHeader` | `src/index.ts:2` |
| `shared` | `re_export` | `pubKeyFromPrivateKey` | `src/index.ts:15` |
| `shared` | `re_export` | `uploadData` | `src/index.ts:2` |
| `shared` | `re_export` | `uploadFile` | `src/index.ts:2` |

## Needs Manual Review

| TypeScript | Python | Reason |
| --- | --- | --- |
| `hexToBytes`<br>`src/config.ts:112` | `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64` | `name_only` |
| `EncryptionHeader`<br>`src/index.ts:39` | `EncryptionHeader`<br>`0g_py_storage/core/encryption.py:46` | `name_only` |
| `getConfig`<br>`src/index.ts:15` | `get_config`<br>`0g_py_storage/config.py:220` | `name_only` |
| `getNetwork`<br>`src/index.ts:15` | `get_network`<br>`0g_py_storage/config.py:187` | `name_only` |
| `hexToBytes`<br>`src/index.ts:15` | `hex_to_bytes`<br>`0g_py_storage/utils/crypto.py:64` | `name_only` |

## Python Only

| Domain | Kind | Item | Location |
| --- | --- | --- | --- |
| `config` | `method` | `EncryptionConfig.to_upload_opt` | `0g_py_storage/config.py:147` |
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
| `download` | `method` | `Downloader.check_exist` | `0g_py_storage/core/downloader.py:410` |
| `download` | `method` | `Downloader.download` | `0g_py_storage/core/downloader.py:49` |
| `download` | `method` | `Downloader.download_file` | `0g_py_storage/core/downloader.py:148` |
| `download` | `method` | `Downloader.download_file_helper` | `0g_py_storage/core/downloader.py:346` |
| `download` | `method` | `Downloader.download_fragments` | `0g_py_storage/core/downloader.py:75` |
| `download` | `method` | `Downloader.download_task` | `0g_py_storage/core/downloader.py:268` |
| `download` | `method` | `Downloader.query_file` | `0g_py_storage/core/downloader.py:222` |
| `encryption` | `class` | `EncryptedFile` | `0g_py_storage/core/encrypted_file.py:39` |
| `encryption` | `class` | `EncryptedFileFragment` | `0g_py_storage/core/encrypted_file.py:107` |
| `encryption` | `class` | `FragmentDecryptResult` | `0g_py_storage/core/encryption.py:311` |
| `encryption` | `class` | `TryDecryptResult` | `0g_py_storage/core/decryption.py:44` |
| `encryption` | `function` | `crypt_at` | `0g_py_storage/core/encryption.py:129` |
| `encryption` | `function` | `decrypt_file` | `0g_py_storage/core/encryption.py:299` |
| `encryption` | `function` | `decrypt_fragment_data` | `0g_py_storage/core/encryption.py:316` |
| `encryption` | `function` | `derive_ecies_decrypt_key` | `0g_py_storage/core/encryption.py:271` |
| `encryption` | `function` | `derive_ecies_encrypt_key` | `0g_py_storage/core/encryption.py:249` |
| `encryption` | `function` | `new_ecies_encrypted_file` | `0g_py_storage/core/encrypted_file.py:150` |
| `encryption` | `function` | `new_ecies_header` | `0g_py_storage/core/encryption.py:286` |
| `encryption` | `function` | `new_symmetric_encrypted_file` | `0g_py_storage/core/encrypted_file.py:143` |

Showing first `80` of `372` items. See JSON for the full list.

## Maintainer Notes

- Treat `missing_in_python` feature probes and `TypeScript Only` classes/functions/methods as triage candidates.
- A match here means the public names look aligned; it does not prove behavior parity.
- For high-risk areas like upload/download semantics, encryption wire format, network config, and proof verification, follow up with source-level review and parity tests.
