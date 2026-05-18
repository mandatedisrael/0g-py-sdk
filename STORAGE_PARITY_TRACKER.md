# 0G Storage TS Starter Kit Parity Tracker

This repo treats [`0gfoundation/0g-storage-ts-starter-kit`](https://github.com/0gfoundation/0g-storage-ts-starter-kit) as the upstream source for storage wrapper features that may need to land in the Python storage SDK.

The Python package is lower-level than the starter kit, so not every TypeScript-only wrapper is automatically a missing Python SDK feature. Use the generated report as a triage input, then decide whether each item should become a Python API, example, script, or intentional difference.

## Workflow

1. Run the checker against the latest upstream starter kit:

   ```bash
   python3 scripts/check_storage_parity.py --refresh
   ```

2. Review `reports/storage_parity_report.md` for:

   - the `Coding Agent Brief` section, which is the primary handoff for implementation agents
   - `missing_in_python` feature probes
   - TypeScript-only wrapper functions
   - name-only matches that need manual behavior review

3. Use broader package scope when reviewing CLI scripts and the browser UI:

   ```bash
   python3 scripts/check_storage_parity.py --refresh --scope package
   ```

4. Classify each meaningful upstream change:

   - `port`: Python should implement the feature or behavior.
   - `example`: Python should add a script or example, not a core API.
   - `covered`: Python already supports it under a different name or lower-level API.
   - `intentional-difference`: Python intentionally diverges.
   - `docs-only`: No SDK behavior to port.
   - `needs-research`: Source-level review is needed before deciding.

5. Add or update Python parity tests for any ported behavior.

## Last Checked Upstream

- Commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3`
- Package version: `2.0.0`
- Date: `2026-05-17`
- Scope: `sdk`

## Last Reviewed Upstream

- Commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3` (starter kit)
- SDK reference: `github.com/0gfoundation/0g-ts-sdk` cloned to `.cache/0g_ts_sdk` (encryption primitives port source)
- Package version: `2.0.0`
- Date: `2026-05-18`
- Reviewer: `mandatedisrael`

## Open Parity Items

_None._ Local TS↔Python interop is verified by running the real
`@0gfoundation/0g-ts-sdk` encryption code against Python output and vice
versa (see `tests/test_ts_python_interop.py`). The storage layer is just an
opaque byte store: if both sides agree on every byte of the encrypted file
(which they do, byte-for-byte, for v1 with fixed key+nonce), network
round-trips work by construction. Live testnet exercising would only add
operational confidence, not new correctness signal.

## Intentional Differences

| Upstream Area | Python Area | Reason | Review Date |
| --- | --- | --- | --- |
| Starter-kit wrapper functions (`uploadFile`, `downloadFile`, `batchUpload`, `uploadData`) | Not ported as SDK methods | Python `0g_py_storage` is the SDK layer; TS upstream is a starter-kit wrapper *on top of* `@0gfoundation/0g-ts-sdk`. Wrapper convenience can live in user code or a future Python starter-kit package. | 2026-05-18 |
| `createSigner` / `createIndexer` / `getConfig` / `pubKeyFromPrivateKey` config helpers | Not ported | Same rationale — starter-kit ergonomics, not SDK capability. | 2026-05-18 |
| `generateAes256Key` utility | Use `os.urandom(32)` directly | TS exposes it for convenience; idiomatic Python uses `secrets.token_bytes(32)` or `os.urandom(32)`. No SDK function needed. | 2026-05-18 |

## Shipped Parity Work

| Date | Upstream Reference | Python Change | Tests |
| --- | --- | --- | --- |
| 2026-05-18 | Encryption primitives — `src.ts/common/encryption.ts` from `@0gfoundation/0g-ts-sdk`: `EncryptionHeader`, `parseEncryptionHeader`, `cryptAt`, `normalizePubKey`, `normalizePrivKey`, `deriveEciesEncryptKey`, `deriveEciesDecryptKey`, `newSymmetricHeader`, `newEciesHeader`, `decryptFile`, `decryptFragmentData`, `resolveDecryptionKey` | New module `0g_py_storage/core/encryption.py` ports the entire TS encryption surface 1:1 (snake_case). AES-256-CTR via `cryptography.Cipher`, secp256k1 ECDH via `cryptography.ec.ECDH`, HKDF-SHA256 with the exact TS info string `b"0g-storage-client/ecies/v1/aes-256"`. Wire-compatible header formats (v1: 17 bytes, v2: 50 bytes). Added `cryptography>=45.0.0` to `requirements.txt`. | `0g_py_storage/tests/test_encryption.py` — 26 tests covering header round-trip, byte-aligned and non-aligned CTR offsets, TS-reference secp256k1 vector (`priv=0x01*32 → 031b84c5...078f`), ECIES encrypt/decrypt key match, full-file round-trip for both versions, fragment decryption, error paths. |
| 2026-05-18 | `EncryptedFile` + `EncryptedFileFragment` wrapper — `src.ts/file/EncryptedFile.ts` | New module `0g_py_storage/core/encrypted_file.py` ports the wrapper that adapts any `AbstractFile` for transparent on-the-fly encryption. Header bytes are streamed for the first N reads; subsequent reads are AES-256-CTR encrypted via `crypt_at(... inner_start_offset)` so merkle/segment pipelines need no changes. `new_symmetric_encrypted_file` and `new_ecies_encrypted_file` mirror TS factory naming. | `0g_py_storage/tests/test_encrypted_file.py` — covers size+header inclusion (v1/v2), partial reads, fragment delegation. |
| 2026-05-18 | `Uploader` encryption plumbing — TS `Uploader.uploadFile` calls `this.wrapEncryption(file, mergedOpts.encryption)` before computing the merkle tree | `Uploader.upload_file` now inspects `opts['encryption']` and routes through `Uploader._wrap_encryption` to wrap the input with `EncryptedFile` before merkle/submission. Accepts `{"type": "aes256", "key": bytes}` or `{"type": "ecies", "recipient_pub_key": bytes\|hex}`. | `tests/test_encrypted_file.py` covers the wrap-helper directly (4 cases including the error paths). |
| 2026-05-18 | `Downloader` decryption plumbing — TS `Indexer.downloadToBlob` calls `tryDecrypt` on the final bytes | `Downloader.download_file` now accepts `symmetric_key=` and `private_key=` kwargs. On success it reads the downloaded file, runs `try_decrypt`, and rewrites with plaintext if a header matches and the key resolves cleanly. Best-effort: any failure leaves the ciphertext on disk unchanged. | `tests/test_encrypted_file.py::test_try_decrypt_*` covers all five decision branches (recover v1, recover v2, raw on no header, raw on missing key, raw on off-curve ephemeral pub). |
| 2026-05-18 | `Indexer.peekHeader` + `tryDecrypt` / `tryDecryptFragments` — `src.ts/indexer/decryption.ts` + `Indexer.ts:482` | Added `0g_py_storage/core/decryption.py` with `try_decrypt` and `try_decrypt_fragments` (non-throwing for decryption errors). Added `Indexer.peek_header(root_hash) -> (EncryptionHeader \| None, Exception \| None)` that fetches just enough bytes from segment 0 to parse the header. Extracted `_new_downloader_from_indexer_nodes` so `download` and `peek_header` share node-selection logic. | `tests/test_encrypted_file.py::test_try_decrypt_fragments_*` (3 cases). |
| 2026-05-18 | Cross-language byte-for-byte vectors | `tests/test_cross_language_vectors.py` — frozen AES-CTR offset-alignment vector, full v1 round-trip vector, HKDF info-string equality, and the TS secp256k1 reference pubkey from `.cache/0g_ts_sdk/tests/encryption.test.ts`. A diverging implementation in either language would flip one of these tests. | 5 tests, all pass. |
| 2026-05-18 | Typed network configuration — `src/config.ts` from `0g-storage-ts-starter-kit`: `NetworkName`, `StorageMode`, `NetworkConfig`, `EncryptionConfig`, `DecryptionConfig`, `AppConfig`, `ConfigOverrides`, `INDEXER_URLS`, `NETWORKS`, `getNetwork`, `getConfig` | Extended `0g_py_storage/config.py` with snake_case-named equivalents (`NetworkConfig`, `EncryptionConfig`, `DecryptionConfig`, `AppConfig`, `ConfigOverrides` dataclasses; `NetworkName` / `StorageMode` `Literal` types; `INDEXER_URLS` and `NETWORK_PRESETS` constants; `get_network(name, mode)` and `get_config(overrides)` functions with env-var fallback). The existing flat `NETWORKS` dict is preserved unchanged for backward compatibility with SDK internals that already consume it. | `0g_py_storage/tests/test_network_config.py` — 19 tests covering INDEXER_URLS exact-match, NETWORK_PRESETS chain IDs/RPC URLs, `get_network` defaults+env-fallback+overrides+validation errors, `EncryptionConfig` validation+`to_upload_opt`, `get_config` AppConfig assembly+env-var pickup+int parsing. |
| 2026-05-18 | Cross-language interop validation — actual TS↔Python round-trip via the reference `@0gfoundation/0g-ts-sdk` encryption module | Added `tests/_interop/{ts_encrypt_v1,ts_encrypt_v2,ts_decrypt}.mjs` — three small Node/tsx scripts that exercise the real TS encryption code from `.cache/0g_ts_sdk/src.ts/common/encryption.ts`. New `tests/test_ts_python_interop.py` invokes them via subprocess and verifies: (a) byte-identical v1 ciphertext when both sides share key+nonce+plaintext, (b) Python decrypts TS-encrypted v1 output, (c) Python decrypts TS-encrypted v2 ECIES output, (d) TS decrypts Python-encrypted v1 output, (e) TS decrypts Python-encrypted v2 output. Skipped automatically if Node/tsx isn't present so non-interop environments are unaffected. | `tests/test_ts_python_interop.py` — 5 tests, all pass. |
