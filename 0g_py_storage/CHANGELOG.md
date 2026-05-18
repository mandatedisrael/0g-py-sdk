# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-05-18

### Added

- **Client-side encryption.** Files can now be encrypted before
  upload and decrypted transparently on download. Two schemes are
  supported:

  | Version | Cipher | Key material |
  |---------|--------|--------------|
  | v1 | AES-256-CTR | Caller-supplied 32-byte symmetric key |
  | v2 | AES-256-CTR + ECIES on secp256k1 | Recipient's secp256k1 public key (encrypt) / private key (decrypt) |

  Encrypted upload via `Indexer.upload`:

  ```python
  indexer.upload(file, RPC, account, upload_opts={
      "encryption": {"type": "aes256", "key": os.urandom(32)},
      # or {"type": "ecies", "recipient_pub_key": "0x..."}
  })
  ```

  Encrypted download via `Indexer.download` / `Downloader.download_file`
  with `symmetric_key=` (v1) or `private_key=` (v2). Decryption is
  best-effort — files are left as ciphertext on disk if the key
  doesn't match.

- **`Indexer.peek_header(root_hash)`** — fetch just the encryption
  header for a stored file without downloading the full body. Useful
  for rendering a "this file is encrypted, supply a key" prompt
  before committing to a download.

- **`core.encryption` module** exposing the low-level primitives:
  `EncryptionHeader`, `parse_encryption_header`, `crypt_at`,
  `normalize_pub_key` / `normalize_priv_key`,
  `derive_ecies_encrypt_key` / `derive_ecies_decrypt_key`,
  `new_symmetric_header` / `new_ecies_header`, `decrypt_file`,
  `decrypt_fragment_data`, `resolve_decryption_key`.

- **`core.encrypted_file` module** with the `EncryptedFile` wrapper
  (and `EncryptedFileFragment`) that adapts any `AbstractFile` for
  transparent on-the-fly encryption so the merkle and segment
  pipelines work unchanged.

- **`core.decryption` module** with the non-throwing `try_decrypt`
  and `try_decrypt_fragments` helpers for files retrieved
  out-of-band.

- **Typed network configuration in `config.py`:**
  `NetworkName`, `StorageMode`, `NetworkConfig`,
  `EncryptionConfig`, `DecryptionConfig`, `AppConfig`,
  `ConfigOverrides` dataclasses; `INDEXER_URLS` and
  `NETWORK_PRESETS` constants covering both turbo and standard
  indexer endpoints; `get_network(name, mode)` with `NETWORK` /
  `STORAGE_MODE` env-var fallback; `get_config(overrides)` that
  also picks up `PRIVATE_KEY` / `GAS_PRICE` / `GAS_LIMIT` /
  `MAX_RETRIES` / `MAX_GAS_PRICE` from the environment. The
  existing flat `NETWORKS` dict is preserved.

### Dependencies

- New: **`cryptography>=45.0.0`** for AES-256-CTR, HKDF-SHA256, and
  secp256k1 ECDH.

### Tests

- `tests/test_encryption.py`
- `tests/test_encrypted_file.py`
- `tests/test_network_config.py`
- `tests/test_cross_language_vectors.py`
- `tests/test_ts_python_interop.py`
