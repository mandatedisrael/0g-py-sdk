"""
TS <-> Python interop tests.

Runs the real `@0gfoundation/0g-ts-sdk` encryption code (from
`.cache/0g_ts_sdk/`) via Node and verifies that:

1. Python's v1 encryption produces byte-identical output to TS for fixed
   key + nonce + plaintext (the canonical reference implementation).
2. Python can decrypt a v1 file produced by TS.
3. Python can decrypt a v2 (ECIES) file produced by TS (random ephemeral,
   so compare plaintext, not ciphertext).
4. TS can decrypt v1 and v2 files produced by Python.

If any test fails, Python and TS will not interoperate at the wire
layer — files encrypted in one cannot be decrypted in the other.

Tests are skipped unless `node` and the cached TS SDK with installed
dependencies are present, so normal CI runs without Node are unaffected.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.encryption import (
    SYMMETRIC_VERSION,
    EncryptionHeader,
    crypt_at,
    decrypt_file,
    derive_ecies_decrypt_key,
)
from core.encrypted_file import new_ecies_encrypted_file


INTEROP_DIR = Path(__file__).parent / "_interop"
TS_SDK_ROOT = Path(__file__).parent.parent.parent / ".cache" / "0g_ts_sdk"
TSX = TS_SDK_ROOT / "node_modules" / ".bin" / "tsx"

_skip_reason = None
if shutil.which("node") is None:
    _skip_reason = "node not on PATH"
elif not TSX.exists():
    _skip_reason = f"tsx not installed at {TSX} (run `npm install` in .cache/0g_ts_sdk)"
elif not TS_SDK_ROOT.joinpath("src.ts/common/encryption.ts").exists():
    _skip_reason = "TS SDK source not present in .cache/0g_ts_sdk"

pytestmark = pytest.mark.skipif(
    _skip_reason is not None, reason=_skip_reason or ""
)


def _run_ts(script_name: str, payload: dict) -> bytes:
    """Run a TS helper with the manifest as stdin JSON, return stdout hex bytes."""
    script = INTEROP_DIR / script_name
    result = subprocess.run(
        [str(TSX), str(script)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"TS helper {script_name} failed:\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
    return bytes.fromhex(result.stdout.decode("utf-8").strip())


# ── Determinism: identical key+nonce+plaintext → identical ciphertext ──────


def test_v1_python_matches_ts_byte_for_byte():
    """
    Strongest possible interop check: with a fixed AES key and nonce, both
    sides must produce *byte-identical* encrypted files. Any divergence
    here means a wire incompatibility.
    """
    key = bytes([0x42] * 32)
    nonce = bytes([0x13] * 16)
    plaintext = b"interop check: python and TS must agree on every byte"

    # Python side
    py_header = EncryptionHeader(SYMMETRIC_VERSION, nonce)
    py_body = crypt_at(key, nonce, 0, plaintext)
    py_encrypted = py_header.to_bytes() + py_body

    # TS side
    ts_encrypted = _run_ts(
        "ts_encrypt_v1.mjs",
        {
            "key_hex": key.hex(),
            "nonce_hex": nonce.hex(),
            "plaintext_hex": plaintext.hex(),
        },
    )

    assert py_encrypted == ts_encrypted, (
        f"v1 ciphertext divergence:\n"
        f"  python: {py_encrypted.hex()}\n"
        f"  ts:     {ts_encrypted.hex()}"
    )


# ── Round-trip: TS encrypts, Python decrypts (v1) ──────────────────────────


def test_python_decrypts_ts_v1_output():
    key = bytes([0x77] * 32)
    nonce = bytes(range(16))
    plaintext = b"a TS-encrypted v1 file that Python must read"

    ts_encrypted = _run_ts(
        "ts_encrypt_v1.mjs",
        {
            "key_hex": key.hex(),
            "nonce_hex": nonce.hex(),
            "plaintext_hex": plaintext.hex(),
        },
    )

    recovered = decrypt_file(key, ts_encrypted)
    assert recovered == plaintext


# ── Round-trip: TS encrypts (random ephemeral), Python decrypts (v2) ──────


def test_python_decrypts_ts_v2_output():
    """
    ECIES uses a random ephemeral key per encryption so ciphertext bytes
    will differ run-to-run, but Python must still recover the plaintext
    using the recipient's static private key.
    """
    recipient_priv = bytes([0x11] * 32)
    # priv = 0x11*32 -> compressed pub. Derive it the same way Python does.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    priv_obj = ec.derive_private_key(
        int.from_bytes(recipient_priv, "big"), ec.SECP256K1()
    )
    recipient_pub = priv_obj.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint,
    )

    plaintext = b"v2 ECIES handshake across the language boundary"

    ts_encrypted = _run_ts(
        "ts_encrypt_v2.mjs",
        {
            "recipient_pub_hex": recipient_pub.hex(),
            "plaintext_hex": plaintext.hex(),
        },
    )

    # Python parses the header, derives the AES key via ECDH, decrypts.
    from core.encryption import parse_encryption_header

    header = parse_encryption_header(ts_encrypted)
    aes_key = derive_ecies_decrypt_key(recipient_priv, header.ephemeral_pub)
    recovered = decrypt_file(aes_key, ts_encrypted)
    assert recovered == plaintext


# ── Round-trip: Python encrypts, TS decrypts (v1) ──────────────────────────


class _MemFile:
    def __init__(self, data):
        self._data = data

    def size(self):
        return len(self._data)

    def read_from_file(self, start, end):
        chunk = self._data[start:end]
        return len(chunk), chunk

    def create_fragment(self, *a):
        raise NotImplementedError

    def iterate_with_offset_and_batch(self, *a):
        raise NotImplementedError


def test_ts_decrypts_python_v1_output():
    from core.encrypted_file import new_symmetric_encrypted_file

    key = bytes([0x99] * 32)
    plaintext = b"python wrote this; TS must read it"

    ef = new_symmetric_encrypted_file(_MemFile(plaintext), key)
    _, py_encrypted = ef.read_from_file(0, ef.size())

    recovered = _run_ts(
        "ts_decrypt.mjs",
        {
            "encrypted_hex": py_encrypted.hex(),
            "symmetric_key_hex": key.hex(),
        },
    )
    assert recovered == plaintext


# ── Round-trip: Python encrypts, TS decrypts (v2) ──────────────────────────


def test_ts_decrypts_python_v2_output():
    recipient_priv_hex = "01" * 32
    recipient_pub_hex = (
        "031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f"
    )
    plaintext = b"python ECIES wrote this; TS recovers it"

    ef = new_ecies_encrypted_file(_MemFile(plaintext), recipient_pub_hex)
    _, py_encrypted = ef.read_from_file(0, ef.size())

    recovered = _run_ts(
        "ts_decrypt.mjs",
        {
            "encrypted_hex": py_encrypted.hex(),
            "private_key_hex": "0x" + recipient_priv_hex,
        },
    )
    assert recovered == plaintext
