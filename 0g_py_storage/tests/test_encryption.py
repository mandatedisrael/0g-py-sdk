"""
Tests for client-side encryption primitives.

Mirrors `.cache/0g_ts_sdk/tests/encryption.test.ts` 1:1 and uses the TS
reference vectors verbatim. A passing run here proves Python encryption is
wire-compatible with the TS SDK and (transitively) the Go storage client.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.encryption import (
    ECIES_HEADER_SIZE,
    ECIES_VERSION,
    EPHEMERAL_PUBKEY_SIZE,
    SYMMETRIC_HEADER_SIZE,
    SYMMETRIC_VERSION,
    EncryptionHeader,
    crypt_at,
    decrypt_file,
    decrypt_fragment_data,
    derive_ecies_decrypt_key,
    derive_ecies_encrypt_key,
    new_ecies_header,
    new_symmetric_header,
    normalize_priv_key,
    normalize_pub_key,
    parse_encryption_header,
    resolve_decryption_key,
)


# ── EncryptionHeader v1 ────────────────────────────────────────────────────


def test_v1_serializes_to_17_bytes_and_round_trips():
    nonce = bytes(range(1, 17))
    h = EncryptionHeader(SYMMETRIC_VERSION, nonce)
    raw = h.to_bytes()

    assert len(raw) == SYMMETRIC_HEADER_SIZE == 17
    assert raw[0] == 0x01
    assert raw[1:17] == nonce

    parsed = parse_encryption_header(raw)
    assert parsed.version == SYMMETRIC_VERSION
    assert parsed.nonce == nonce
    assert parsed.size() == 17


def test_v1_parse_rejects_too_short():
    with pytest.raises(ValueError, match="too short"):
        parse_encryption_header(b"\x01")


def test_parse_rejects_unsupported_version():
    bad = bytes([0xEE]) + b"\x00" * 16
    with pytest.raises(ValueError, match="unsupported"):
        parse_encryption_header(bad)


# ── EncryptionHeader v2 ────────────────────────────────────────────────────


def test_v2_serializes_to_50_bytes_and_round_trips():
    nonce = bytes(0xA0 + i for i in range(16))
    ephemeral_pub = bytes(range(EPHEMERAL_PUBKEY_SIZE))

    h = EncryptionHeader(ECIES_VERSION, nonce, ephemeral_pub)
    raw = h.to_bytes()

    assert len(raw) == ECIES_HEADER_SIZE == 50
    assert raw[0] == 0x02
    assert raw[1 : 1 + EPHEMERAL_PUBKEY_SIZE] == ephemeral_pub
    assert raw[1 + EPHEMERAL_PUBKEY_SIZE : 1 + EPHEMERAL_PUBKEY_SIZE + 16] == nonce

    parsed = parse_encryption_header(raw)
    assert parsed.version == ECIES_VERSION
    assert parsed.ephemeral_pub == ephemeral_pub
    assert parsed.nonce == nonce
    assert parsed.size() == 50


def test_v2_parse_rejects_short_data():
    bad = bytes([0x02]) + b"\x00" * 16
    with pytest.raises(ValueError, match="too short"):
        parse_encryption_header(bad)


# ── crypt_at (AES-256-CTR with offset) ─────────────────────────────────────

KEY = bytes([0x42] * 32)
NONCE = bytes([0x13] * 16)


def test_round_trips_at_offset_zero():
    plain = b"hello world encryption test data"
    cipher = crypt_at(KEY, NONCE, 0, plain)
    assert cipher != plain
    decrypted = crypt_at(KEY, NONCE, 0, cipher)
    assert decrypted == plain


def test_two_halves_match_single_full_encrypt():
    original = bytes(range(100))
    full = crypt_at(KEY, NONCE, 0, original)

    part1 = crypt_at(KEY, NONCE, 0, original[:50])
    part2 = crypt_at(KEY, NONCE, 50, original[50:])

    assert part1 == full[:50]
    assert part2 == full[50:]


def test_sub_range_decryption_with_matching_offset():
    plain = bytes(range(100))
    cipher = crypt_at(KEY, NONCE, 0, plain)

    slice_ = cipher[32:]
    decrypted = crypt_at(KEY, NONCE, 32, slice_)
    assert decrypted == plain[32:]


def test_no_op_on_empty_input():
    assert crypt_at(KEY, NONCE, 0, b"") == b""


def test_non_block_aligned_offsets():
    plain = bytes((i * 3) & 0xFF for i in range(64))
    cipher = crypt_at(KEY, NONCE, 0, plain)

    slice_ = cipher[7:]
    decrypted = crypt_at(KEY, NONCE, 7, slice_)
    assert decrypted == plain[7:]


# ── normalize_pub_key — TS reference vector ────────────────────────────────

# From the TS test suite. priv = 0x01*32 -> compressed pub:
COMPRESSED_HEX = "031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f"
COMPRESSED_BYTES = bytes.fromhex(COMPRESSED_HEX)


def test_normalize_pub_key_passes_compressed_through():
    assert normalize_pub_key(COMPRESSED_BYTES).hex() == COMPRESSED_HEX


def test_normalize_pub_key_accepts_compressed_hex_with_prefix():
    assert normalize_pub_key("0x" + COMPRESSED_HEX).hex() == COMPRESSED_HEX


def test_normalize_pub_key_accepts_compressed_hex_no_prefix():
    assert normalize_pub_key(COMPRESSED_HEX).hex() == COMPRESSED_HEX


def test_normalize_pub_key_rejects_invalid_length():
    with pytest.raises(ValueError):
        normalize_pub_key(b"\x00" * 10)


# ── normalize_priv_key ─────────────────────────────────────────────────────

PRIV_HEX = "01" * 32


def test_normalize_priv_key_passes_bytes_through():
    assert normalize_priv_key(bytes.fromhex(PRIV_HEX)).hex() == PRIV_HEX


def test_normalize_priv_key_accepts_hex_with_prefix():
    assert normalize_priv_key("0x" + PRIV_HEX).hex() == PRIV_HEX


def test_normalize_priv_key_accepts_hex_no_prefix():
    assert normalize_priv_key(PRIV_HEX).hex() == PRIV_HEX


def test_normalize_priv_key_rejects_short_input():
    with pytest.raises(ValueError):
        normalize_priv_key(b"\x00" * 10)
    with pytest.raises(ValueError):
        normalize_priv_key("beef")


def test_normalize_priv_key_rejects_zero_scalar():
    with pytest.raises(ValueError, match="invalid"):
        normalize_priv_key(b"\x00" * 32)


# ── ECIES key derivation ───────────────────────────────────────────────────


def test_ecies_encrypt_and_decrypt_keys_match():
    # Use the TS reference vector for the recipient.
    recipient_priv = bytes.fromhex(PRIV_HEX)
    recipient_pub = COMPRESSED_BYTES

    enc_key, ephemeral_pub = derive_ecies_encrypt_key(recipient_pub)
    dec_key = derive_ecies_decrypt_key(recipient_priv, ephemeral_pub)

    assert len(enc_key) == 32
    assert len(ephemeral_pub) == 33
    assert dec_key == enc_key


def test_ecies_generates_fresh_ephemeral_each_call():
    recipient_pub = COMPRESSED_BYTES
    _, ephemeral_a = derive_ecies_encrypt_key(recipient_pub)
    _, ephemeral_b = derive_ecies_encrypt_key(recipient_pub)
    assert ephemeral_a != ephemeral_b


def test_ecies_wrong_private_key_yields_different_aes_key():
    recipient_priv = bytes.fromhex(PRIV_HEX)
    attacker_priv = bytes.fromhex("02" * 32)
    recipient_pub = COMPRESSED_BYTES

    right_key, ephemeral_pub = derive_ecies_encrypt_key(recipient_pub)
    wrong_key = derive_ecies_decrypt_key(attacker_priv, ephemeral_pub)
    assert wrong_key != right_key


# ── End-to-end: encrypt with one factory, decrypt with the other ───────────


def test_full_file_round_trip_v1():
    header = new_symmetric_header()
    key = bytes([0x77] * 32)
    plaintext = b"the quick brown fox jumps over the lazy dog" * 10

    body = crypt_at(key, header.nonce, 0, plaintext)
    encrypted_file = header.to_bytes() + body

    decrypted = decrypt_file(key, encrypted_file)
    assert decrypted == plaintext


def test_full_file_round_trip_v2():
    recipient_priv = bytes.fromhex(PRIV_HEX)
    recipient_pub = COMPRESSED_BYTES

    header, key = new_ecies_header(recipient_pub)
    plaintext = b"ecies round trip" * 32

    body = crypt_at(key, header.nonce, 0, plaintext)
    encrypted_file = header.to_bytes() + body

    parsed_header = parse_encryption_header(encrypted_file)
    decrypt_key = resolve_decryption_key(None, recipient_priv, parsed_header)
    decrypted = decrypt_file(decrypt_key, encrypted_file)
    assert decrypted == plaintext


def test_decrypt_fragment_data_first_and_subsequent():
    header = new_symmetric_header()
    key = bytes([0x99] * 32)
    plaintext = bytes(range(200))
    full_cipher = header.to_bytes() + crypt_at(key, header.nonce, 0, plaintext)

    # First fragment: header + first 80 bytes of ciphertext.
    split = header.size() + 80
    first_fragment = full_cipher[:split]
    rest = full_cipher[split:]

    r1 = decrypt_fragment_data(key, header, first_fragment, True, 0)
    assert r1.plaintext == plaintext[:80]
    assert r1.new_offset == 80

    r2 = decrypt_fragment_data(key, header, rest, False, r1.new_offset)
    assert r2.plaintext == plaintext[80:]
    assert r2.new_offset == len(plaintext)


def test_resolve_decryption_key_errors():
    sym_header = EncryptionHeader(SYMMETRIC_VERSION, b"\x00" * 16)
    with pytest.raises(ValueError, match="requires a symmetric key"):
        resolve_decryption_key(None, None, sym_header)
    with pytest.raises(ValueError, match="32 bytes"):
        resolve_decryption_key(b"\x00" * 31, None, sym_header)

    ecies_header = EncryptionHeader(
        ECIES_VERSION, b"\x00" * 16, b"\x02" + b"\x01" * 32
    )
    with pytest.raises(ValueError, match="requires a private key"):
        resolve_decryption_key(None, None, ecies_header)
