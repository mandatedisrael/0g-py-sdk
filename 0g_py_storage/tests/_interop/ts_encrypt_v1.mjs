// Deterministic v1 (AES-256-CTR symmetric) encryption helper.
// Reads a JSON manifest on stdin with { key_hex, nonce_hex, plaintext_hex }
// and writes the resulting EncryptionHeader + ciphertext to stdout as hex.
//
// Used by tests/test_interop.py to verify Python's encryption produces
// byte-identical output to the TS SDK (which itself wraps @noble/ciphers).

import { cryptAt, EncryptionHeader, SYMMETRIC_VERSION } from
  "../../../.cache/0g_ts_sdk/src.ts/common/encryption.ts";

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const manifest = JSON.parse(Buffer.concat(chunks).toString("utf8"));

const key = Buffer.from(manifest.key_hex, "hex");
const nonce = Buffer.from(manifest.nonce_hex, "hex");
const plaintext = Buffer.from(manifest.plaintext_hex, "hex");

if (key.length !== 32) throw new Error("key must be 32 bytes");
if (nonce.length !== 16) throw new Error("nonce must be 16 bytes");

const body = new Uint8Array(plaintext);
cryptAt(new Uint8Array(key), new Uint8Array(nonce), 0, body);

const header = new EncryptionHeader(SYMMETRIC_VERSION, new Uint8Array(nonce));
const headerBytes = header.toBytes();

const out = new Uint8Array(headerBytes.length + body.length);
out.set(headerBytes, 0);
out.set(body, headerBytes.length);

process.stdout.write(Buffer.from(out).toString("hex"));
