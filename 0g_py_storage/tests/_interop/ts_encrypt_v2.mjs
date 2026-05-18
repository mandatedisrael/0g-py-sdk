// v2 (ECIES) encryption helper.
// Reads { recipient_pub_hex, plaintext_hex } on stdin, generates an
// ephemeral keypair, derives the AES key, and writes the full encrypted
// file (50-byte v2 header + ciphertext) to stdout as hex.

import {
  cryptAt,
  newEciesHeader,
} from "../../../.cache/0g_ts_sdk/src.ts/common/encryption.ts";

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const manifest = JSON.parse(Buffer.concat(chunks).toString("utf8"));

const recipientPubHex = manifest.recipient_pub_hex;
const plaintext = Buffer.from(manifest.plaintext_hex, "hex");

const { header, key } = newEciesHeader(recipientPubHex);
const body = new Uint8Array(plaintext);
cryptAt(key, header.nonce, 0, body);

const headerBytes = header.toBytes();
const out = new Uint8Array(headerBytes.length + body.length);
out.set(headerBytes, 0);
out.set(body, headerBytes.length);

process.stdout.write(Buffer.from(out).toString("hex"));
