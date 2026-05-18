"""
EncryptedFile — transparent AES-256-CTR wrapper around any AbstractFile.

Direct port of ``src.ts/file/EncryptedFile.ts``. Wraps an inner ``AbstractFile``
and prepends an ``EncryptionHeader`` (17 bytes for v1, 50 bytes for v2) to the
data stream, encrypting inner bytes on demand when ``read_from_file`` is
called. The merkle tree and segment pipelines see the wrapped size +
ciphertext transparently — no changes needed downstream.
"""

from __future__ import annotations

from typing import Tuple, Union

try:
    from .encryption import (
        EncryptionHeader,
        KeyLike,
        crypt_at,
        new_ecies_header,
        new_symmetric_header,
    )
    from .file import AbstractFile, FileIterator, MemIterator
    from ..utils.file_utils import iterator_padded_size
    from ..config import DEFAULT_CHUNK_SIZE
except ImportError:  # pragma: no cover - test runner fallback
    from core.encryption import (
        EncryptionHeader,
        KeyLike,
        crypt_at,
        new_ecies_header,
        new_symmetric_header,
    )
    from core.file import AbstractFile, FileIterator, MemIterator
    from utils.file_utils import iterator_padded_size
    from config import DEFAULT_CHUNK_SIZE


class EncryptedFile(AbstractFile):
    """
    Wrap ``inner`` so that its serialized form is ``header.to_bytes() + AES-CTR(inner)``.

    The encryption is applied on the fly per ``read_from_file`` call; nothing
    is buffered. The Merkle tree, segment iterator, and upload pipeline see
    only the wrapped bytes (header bytes for the prefix, ciphertext after).
    """

    def __init__(self, inner: AbstractFile, key: bytes, header: EncryptionHeader):
        super().__init__()
        if len(key) != 32:
            raise ValueError("key must be 32 bytes")
        self.inner = inner
        self.key = bytes(key)
        self.header = header
        self.offset = 0
        self.file_size = inner.size() + header.size()
        self.padded_size_ = iterator_padded_size(
            self.file_size, True, DEFAULT_CHUNK_SIZE
        )

    def create_fragment(
        self, offset: int, size: int, padded_size: int
    ) -> "EncryptedFileFragment":
        return EncryptedFileFragment(self, offset, size)

    def read_from_file(self, start: int, end: int) -> Tuple[int, bytes]:
        if start < 0 or start >= self.size() or start >= end:
            raise ValueError("invalid start offset")
        if end > self.size():
            end = self.size()

        total = end - start
        out = bytearray(total)
        header_size = self.header.size()
        written = 0

        # Copy any header bytes that fall in [start, end).
        if start < header_size:
            header_bytes = self.header.to_bytes()
            from_ = start
            to_ = min(header_size, end)
            chunk = header_bytes[from_:to_]
            out[0 : len(chunk)] = chunk
            written += to_ - from_

        # Copy encrypted inner data for the remainder.
        if written < total:
            inner_start = 0 if start < header_size else start - header_size
            inner_end = end - header_size
            if inner_end > inner_start:
                _, inner_buf = self.inner.read_from_file(inner_start, inner_end)
                encrypted = crypt_at(
                    self.key, self.header.nonce, inner_start, bytes(inner_buf)
                )
                out[written : written + len(encrypted)] = encrypted
                written += len(encrypted)

        return written, bytes(out)

    def iterate_with_offset_and_batch(
        self, offset: int, batch: int, flow_padding: bool
    ) -> FileIterator:
        padded_size = iterator_padded_size(self.size(), flow_padding, DEFAULT_CHUNK_SIZE)
        return MemIterator(self, offset, batch, padded_size)


class EncryptedFileFragment(AbstractFile):
    """
    Fragment of an ``EncryptedFile`` — delegates ``read_from_file`` to the
    parent with an offset adjustment.
    """

    def __init__(self, parent: EncryptedFile, offset: int, size: int):
        super().__init__()
        self.parent = parent
        self.offset = offset
        self.file_size = size
        self.padded_size_ = iterator_padded_size(size, True, DEFAULT_CHUNK_SIZE)

    def create_fragment(
        self, _offset: int, _size: int, _padded_size: int
    ) -> "EncryptedFileFragment":
        # Fragments are not further splittable; mirror the Go reference.
        return self

    def read_from_file(self, start: int, end: int) -> Tuple[int, bytes]:
        if start < 0 or start >= self.size() or start >= end:
            raise ValueError("invalid start offset")
        if end > self.size():
            end = self.size()
        return self.parent.read_from_file(self.offset + start, self.offset + end)

    def iterate_with_offset_and_batch(
        self, offset: int, batch: int, flow_padding: bool
    ) -> FileIterator:
        padded_size = iterator_padded_size(self.size(), flow_padding, DEFAULT_CHUNK_SIZE)
        return MemIterator(self, offset, batch, padded_size)


# ── Convenience constructors mirroring TS naming ───────────────────────────


def new_symmetric_encrypted_file(inner: AbstractFile, key: bytes) -> EncryptedFile:
    """v1: wrap ``inner`` with a fresh nonce + caller-supplied 32-byte AES key."""
    if len(key) != 32:
        raise ValueError("key must be 32 bytes")
    return EncryptedFile(inner, key, new_symmetric_header())


def new_ecies_encrypted_file(
    inner: AbstractFile, recipient_pub: KeyLike
) -> EncryptedFile:
    """v2: wrap ``inner`` with a fresh nonce + ephemeral keypair derived from ``recipient_pub``."""
    header, key = new_ecies_header(recipient_pub)
    return EncryptedFile(inner, key, header)
