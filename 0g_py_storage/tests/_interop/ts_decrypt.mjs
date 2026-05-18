// Decryption helper: reads { encrypted_hex, symmetric_key_hex?, private_key_hex? }
// on stdin and writes the plaintext to stdout as hex. Used to verify that
// Python-encrypted files decrypt cleanly in the reference TS SDK.

import {
  parseEncryptionHeader,
  resolveDecryptionKey,
  decryptFile,
} from "../../../.cache/0g_ts_sdk/src.ts/common/encryption.ts";

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const manifest = JSON.parse(Buffer.concat(chunks).toString("utf8"));

const encrypted = new Uint8Array(Buffer.from(manifest.encrypted_hex, "hex"));
const symKey = manifest.symmetric_key_hex
  ? new Uint8Array(Buffer.from(manifest.symmetric_key_hex, "hex"))
  : undefined;
const privKey = manifest.private_key_hex;

const header = parseEncryptionHeader(encrypted);
const key = resolveDecryptionKey(symKey, privKey, header);
const plaintext = decryptFile(key, encrypted);

process.stdout.write(Buffer.from(plaintext).toString("hex"));
