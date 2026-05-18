"""
EncryptedFile + best-effort decryption integration tests.

Validates that the encryption primitives compose correctly with the existing
`AbstractFile` / `MemIterator` / merkle pipeline, and that the best-effort
`try_decrypt` helpers correctly identify both real headers and false
positives.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.encryption import (
    ECIES_HEADER_SIZE,
    ECIES_VERSION,
    EncryptionHeader,
    SYMMETRIC_HEADER_SIZE,
    SYMMETRIC_VERSION,
    new_symmetric_header,
)
from core.encrypted_file import (
    EncryptedFile,
    EncryptedFileFragment,
    new_ecies_encrypted_file,
    new_symmetric_encrypted_file,
)
from core.decryption import try_decrypt, try_decrypt_fragments


# ── Minimal in-memory AbstractFile for tests ────────────────────────────────


class _MemFile:
    """A tiny shim that satisfies the bits of AbstractFile we need."""

    def __init__(self, data: bytes):
        self._data = data

    def size(self) -> int:
        return len(self._data)

    def read_from_file(self, start: int, end: int):
        if start < 0 or start >= self.size() or start >= end:
            raise ValueError("invalid start offset")
        if end > self.size():
            end = self.size()
        chunk = self._data[start:end]
        return len(chunk), chunk

    def create_fragment(self, offset, size, padded_size):
        # Tests don't go through the fragment path on the inner file.
        raise NotImplementedError

    def iterate_with_offset_and_batch(self, offset, batch, flow_padding):
        raise NotImplementedError


PRIV_HEX = "01" * 32
COMPRESSED_HEX = "031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f"


# ── EncryptedFile shape ────────────────────────────────────────────────────


def test_encrypted_file_size_includes_header_v1():
    inner = _MemFile(b"hello world")
    ef = new_symmetric_encrypted_file(inner, b"\x42" * 32)
    assert ef.size() == len(b"hello world") + SYMMETRIC_HEADER_SIZE
    assert ef.header.version == SYMMETRIC_VERSION


def test_encrypted_file_size_includes_header_v2():
    inner = _MemFile(b"hello world")
    ef = new_ecies_encrypted_file(inner, COMPRESSED_HEX)
    assert ef.size() == len(b"hello world") + ECIES_HEADER_SIZE
    assert ef.header.version == ECIES_VERSION
    assert len(ef.header.ephemeral_pub) == 33


def test_encrypted_file_read_full_stream_matches_header_plus_cipher():
    plaintext = b"the quick brown fox jumps over the lazy dog"
    inner = _MemFile(plaintext)
    ef = new_symmetric_encrypted_file(inner, b"\x77" * 32)

    bytes_read, full = ef.read_from_file(0, ef.size())
    assert bytes_read == ef.size()
    # Header must be the first N bytes.
    assert full[: ef.header.size()] == ef.header.to_bytes()
    # Body is encrypted; never equal to plaintext.
    assert full[ef.header.size():] != plaintext


def test_encrypted_file_read_partial_aligns_with_full():
    plaintext = bytes(range(256))
    inner = _MemFile(plaintext)
    key = b"\x55" * 32
    nonce = b"\x99" * 16
    header = EncryptionHeader(SYMMETRIC_VERSION, nonce)
    ef = EncryptedFile(inner, key, header)

    _, full = ef.read_from_file(0, ef.size())
    _, part_a = ef.read_from_file(0, 30)
    _, part_b = ef.read_from_file(30, ef.size())

    assert part_a == full[:30]
    assert part_b == full[30:]


def test_encrypted_file_fragment_delegates_with_offset():
    plaintext = bytes(range(100))
    inner = _MemFile(plaintext)
    ef = new_symmetric_encrypted_file(inner, b"\x33" * 32)
    full_size = ef.size()
    _, full = ef.read_from_file(0, full_size)

    frag = EncryptedFileFragment(ef, offset=10, size=full_size - 10)
    _, frag_bytes = frag.read_from_file(0, frag.size())
    assert frag_bytes == full[10:]


# ── Round-trip via try_decrypt (post-download) ──────────────────────────────


def test_try_decrypt_recovers_v1_plaintext():
    plaintext = b"sensitive payload " * 8
    inner = _MemFile(plaintext)
    key = b"\xa1" * 32
    ef = new_symmetric_encrypted_file(inner, key)
    _, encrypted = ef.read_from_file(0, ef.size())

    result = try_decrypt(encrypted, symmetric_key=key)
    assert result.decrypted is True
    assert result.bytes == plaintext


def test_try_decrypt_recovers_v2_plaintext():
    plaintext = b"ecies round trip " * 16
    recipient_priv = bytes.fromhex(PRIV_HEX)
    inner = _MemFile(plaintext)
    ef = new_ecies_encrypted_file(inner, COMPRESSED_HEX)
    _, encrypted = ef.read_from_file(0, ef.size())

    result = try_decrypt(encrypted, private_key=recipient_priv)
    assert result.decrypted is True
    assert result.bytes == plaintext


def test_try_decrypt_returns_raw_when_not_encrypted():
    plaintext = b"\xff" * 100  # very unlikely to parse as a valid header
    result = try_decrypt(plaintext, symmetric_key=b"\x00" * 32)
    assert result.decrypted is False
    assert result.bytes == plaintext


def test_try_decrypt_returns_raw_when_key_missing():
    plaintext = b"payload"
    ef = new_symmetric_encrypted_file(_MemFile(plaintext), b"\xa1" * 32)
    _, encrypted = ef.read_from_file(0, ef.size())

    # No key supplied — must return raw bytes, not throw.
    result = try_decrypt(encrypted)
    assert result.decrypted is False
    assert result.bytes == encrypted


def test_try_decrypt_returns_raw_on_wrong_key_type():
    plaintext = b"ecies payload"
    ef = new_ecies_encrypted_file(_MemFile(plaintext), COMPRESSED_HEX)
    _, encrypted = ef.read_from_file(0, ef.size())

    # v2 file but caller only supplied a symmetric key — must not throw.
    result = try_decrypt(encrypted, symmetric_key=b"\x00" * 32)
    assert result.decrypted is False
    assert result.bytes == encrypted


def test_try_decrypt_rejects_v2_with_off_curve_ephemeral():
    # Construct a v2 header whose ephemeral_pub is the wrong prefix byte
    # (e.g. 0x05) so it can't be a valid compressed point.
    bad_ephemeral = b"\x05" + b"\x11" * 32
    assert len(bad_ephemeral) == 33
    header_bytes = bytes([ECIES_VERSION]) + bad_ephemeral + b"\x00" * 16
    payload = header_bytes + b"some bytes after"

    result = try_decrypt(payload, private_key=bytes.fromhex(PRIV_HEX))
    assert result.decrypted is False
    assert result.bytes == payload


# ── Multi-fragment decrypt ──────────────────────────────────────────────────


def test_try_decrypt_fragments_recovers_v1_plaintext():
    plaintext = bytes(range(200))
    key = b"\xbb" * 32
    header = new_symmetric_header()
    ef = EncryptedFile(_MemFile(plaintext), key, header)
    _, full = ef.read_from_file(0, ef.size())

    # Split into 3 fragments: header+30, next 80, rest.
    split1 = header.size() + 30
    split2 = split1 + 80
    frags = [full[:split1], full[split1:split2], full[split2:]]

    plaintexts = try_decrypt_fragments(frags, symmetric_key=key)
    assert plaintexts is not None
    assert b"".join(plaintexts) == plaintext


def test_try_decrypt_fragments_returns_none_on_bad_header():
    frags = [b"\xff" * 50, b"more bytes"]
    assert try_decrypt_fragments(frags, symmetric_key=b"\x00" * 32) is None


def test_try_decrypt_fragments_empty_input():
    assert try_decrypt_fragments([]) == []


# ── Uploader._wrap_encryption ──────────────────────────────────────────────


def test_uploader_wrap_encryption_aes256():
    from core.uploader import Uploader

    up = Uploader.__new__(Uploader)
    wrapped = up._wrap_encryption(_MemFile(b"data"), {"type": "aes256", "key": b"\x01" * 32})
    assert isinstance(wrapped, EncryptedFile)
    assert wrapped.header.version == SYMMETRIC_VERSION


def test_uploader_wrap_encryption_ecies():
    from core.uploader import Uploader

    up = Uploader.__new__(Uploader)
    wrapped = up._wrap_encryption(
        _MemFile(b"data"),
        {"type": "ecies", "recipient_pub_key": COMPRESSED_HEX},
    )
    assert isinstance(wrapped, EncryptedFile)
    assert wrapped.header.version == ECIES_VERSION


def test_uploader_wrap_encryption_invalid_type_raises():
    from core.uploader import Uploader

    up = Uploader.__new__(Uploader)
    with pytest.raises(ValueError, match="unsupported encryption type"):
        up._wrap_encryption(_MemFile(b"data"), {"type": "rot13"})


def test_uploader_wrap_encryption_missing_aes_key_raises():
    from core.uploader import Uploader

    up = Uploader.__new__(Uploader)
    with pytest.raises(ValueError, match="requires 'key'"):
        up._wrap_encryption(_MemFile(b"data"), {"type": "aes256"})


def test_uploader_wrap_encryption_missing_ecies_pub_raises():
    from core.uploader import Uploader

    up = Uploader.__new__(Uploader)
    with pytest.raises(ValueError, match="requires 'recipient_pub_key'"):
        up._wrap_encryption(_MemFile(b"data"), {"type": "ecies"})
