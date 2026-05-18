"""
Client-side encryption primitives for 0G storage.

Direct port of ``src.ts/common/encryption.ts`` from
``github.com/0gfoundation/0g-ts-sdk``. Wire-compatible with the Go client.

Header formats:
- v1 (symmetric, AES-256-CTR):  [0x01][nonce:16]                     = 17 bytes
- v2 (ECIES, AES-256-CTR):      [0x02][ephemeral_pub:33][nonce:16]   = 50 bytes

ECIES derivation: secp256k1 ECDH -> raw 32-byte shared X (no prefix) ->
HKDF-SHA256 with empty salt and info ``b"0g-storage-client/ecies/v1/aes-256"``
-> 32-byte AES key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


SYMMETRIC_VERSION = 1
ECIES_VERSION = 2

NONCE_SIZE = 16
EPHEMERAL_PUBKEY_SIZE = 33
SYMMETRIC_HEADER_SIZE = 1 + NONCE_SIZE          # 17
ECIES_HEADER_SIZE = 1 + EPHEMERAL_PUBKEY_SIZE + NONCE_SIZE  # 50

# Domain-separation string. MUST match the Go client byte-for-byte for interop.
ECIES_HKDF_INFO = b"0g-storage-client/ecies/v1/aes-256"

_SECP256K1 = ec.SECP256K1()


KeyLike = Union[bytes, bytearray, str]


@dataclass
class EncryptionHeader:
    """
    Wire header prepended to encrypted uploads.

    v1 carries only the AES-CTR nonce; v2 also carries the sender's ephemeral
    secp256k1 public key (compressed, 33 bytes) needed to recompute the AES
    key on download.
    """

    version: int
    nonce: bytes
    ephemeral_pub: bytes = b"\x00" * EPHEMERAL_PUBKEY_SIZE

    def __post_init__(self) -> None:
        if len(self.nonce) != NONCE_SIZE:
            raise ValueError(f"nonce must be {NONCE_SIZE} bytes, got {len(self.nonce)}")
        if len(self.ephemeral_pub) != EPHEMERAL_PUBKEY_SIZE:
            raise ValueError(
                f"ephemeral_pub must be {EPHEMERAL_PUBKEY_SIZE} bytes, "
                f"got {len(self.ephemeral_pub)}"
            )

    def size(self) -> int:
        return (
            ECIES_HEADER_SIZE
            if self.version == ECIES_VERSION
            else SYMMETRIC_HEADER_SIZE
        )

    def to_bytes(self) -> bytes:
        if self.version == ECIES_VERSION:
            buf = bytearray(ECIES_HEADER_SIZE)
            buf[0] = self.version
            buf[1 : 1 + EPHEMERAL_PUBKEY_SIZE] = self.ephemeral_pub
            buf[1 + EPHEMERAL_PUBKEY_SIZE : ECIES_HEADER_SIZE] = self.nonce
            return bytes(buf)
        buf = bytearray(SYMMETRIC_HEADER_SIZE)
        buf[0] = self.version
        buf[1:SYMMETRIC_HEADER_SIZE] = self.nonce
        return bytes(buf)


def parse_encryption_header(data: bytes) -> EncryptionHeader:
    """Inverse of ``EncryptionHeader.to_bytes``."""
    if len(data) < 1:
        raise ValueError(f"data too short for encryption header: {len(data)}")
    version = data[0]
    if version == SYMMETRIC_VERSION:
        if len(data) < SYMMETRIC_HEADER_SIZE:
            raise ValueError(
                f"data too short for v1 encryption header: "
                f"{len(data)} < {SYMMETRIC_HEADER_SIZE}"
            )
        return EncryptionHeader(version, bytes(data[1:SYMMETRIC_HEADER_SIZE]))
    if version == ECIES_VERSION:
        if len(data) < ECIES_HEADER_SIZE:
            raise ValueError(
                f"data too short for v2 encryption header: "
                f"{len(data)} < {ECIES_HEADER_SIZE}"
            )
        return EncryptionHeader(
            version,
            bytes(
                data[
                    1 + EPHEMERAL_PUBKEY_SIZE : 1 + EPHEMERAL_PUBKEY_SIZE + NONCE_SIZE
                ]
            ),
            bytes(data[1 : 1 + EPHEMERAL_PUBKEY_SIZE]),
        )
    raise ValueError(f"unsupported encryption version: {version}")


def _add_to_counter(counter: bytearray, val: int) -> None:
    """In-place big-endian 128-bit add of ``val`` into the 16-byte counter."""
    carry = val
    for i in range(15, -1, -1):
        if carry == 0:
            return
        total = counter[i] + (carry & 0xFF)
        counter[i] = total & 0xFF
        carry = (carry >> 8) + (1 if total > 0xFF else 0)


def crypt_at(key: bytes, nonce: bytes, offset: int, data: bytes) -> bytes:
    """
    AES-256-CTR encrypt/decrypt a buffer at plaintext byte ``offset``.

    CTR is symmetric, so encrypt and decrypt are the same XOR. The counter is
    ``nonce + floor(offset/16)`` big-endian; ``offset % 16`` bytes of keystream
    are discarded before the XOR so fragment-offset decryption produces
    bit-identical output to a full-file decrypt.

    Returns the transformed bytes (a new buffer, unlike the TS version which
    mutates in place — Python ``bytes`` is immutable).
    """
    if len(key) != 32:
        raise ValueError("key must be 32 bytes")
    if len(nonce) != NONCE_SIZE:
        raise ValueError(f"nonce must be {NONCE_SIZE} bytes")
    if len(data) == 0:
        return b""

    block_size = 16
    block_offset, byte_offset = divmod(offset, block_size)

    counter = bytearray(nonce)
    _add_to_counter(counter, block_offset)

    # AES-CTR doesn't support mid-block resume natively in `cryptography`.
    # Mirror the TS impl: pad ``byte_offset`` zero bytes at the front,
    # encrypt the padded buffer once, then discard the prefix.
    padded = b"\x00" * byte_offset + bytes(data)
    cipher = Cipher(algorithms.AES(key), modes.CTR(bytes(counter)))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return encrypted[byte_offset:]


def _hex_to_bytes(h: str) -> bytes:
    clean = h[2:] if h.startswith("0x") or h.startswith("0X") else h
    if len(clean) % 2 != 0:
        raise ValueError(f"invalid hex string (odd length): {h}")
    try:
        return bytes.fromhex(clean)
    except ValueError as e:
        raise ValueError(f"invalid hex string: {h}") from e


def _coerce_bytes(input_: KeyLike) -> bytes:
    if isinstance(input_, str):
        return _hex_to_bytes(input_)
    return bytes(input_)


def normalize_pub_key(input_: KeyLike) -> bytes:
    """
    Return the 33-byte compressed secp256k1 public key for any common form:
    33-byte compressed, 65-byte uncompressed (0x04 prefix), 64-byte raw (x||y),
    or a hex string of any of the above (with or without ``0x`` prefix).
    """
    raw = _coerce_bytes(input_)
    if len(raw) == 33:
        # Validate it's on the curve by round-tripping through the library.
        pub = ec.EllipticCurvePublicKey.from_encoded_point(_SECP256K1, raw)
    elif len(raw) == 65:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(_SECP256K1, raw)
    elif len(raw) == 64:
        pub = ec.EllipticCurvePublicKey.from_encoded_point(_SECP256K1, b"\x04" + raw)
    else:
        raise ValueError(f"invalid pubkey byte length: {len(raw)}")
    return pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint,
    )


def _curve_order() -> int:
    # secp256k1 group order n
    return 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def normalize_priv_key(input_: KeyLike) -> bytes:
    """
    Validate and return a 32-byte raw secp256k1 private key. Accepts either
    32 bytes or a hex string. Rejects zero and out-of-range scalars.
    """
    raw = _coerce_bytes(input_)
    if len(raw) != 32:
        raise ValueError(f"private key must be 32 bytes, got {len(raw)}")
    n = int.from_bytes(raw, "big")
    if n == 0 or n >= _curve_order():
        raise ValueError("invalid secp256k1 private key")
    return raw


# ── ECIES key derivation ────────────────────────────────────────────────────


def _ecdh_shared_x(priv_key: bytes, pub_key_compressed: bytes) -> bytes:
    """
    secp256k1 ECDH returning the raw 32-byte shared X coordinate.

    TS does ``secp256k1.getSharedSecret(priv, pub, true).slice(1)`` to drop
    the 0x02/0x03 compressed-point prefix; this returns just X.
    ``cryptography``'s ``ECDH().exchange()`` already returns just X.
    """
    private_value = int.from_bytes(priv_key, "big")
    priv = ec.derive_private_key(private_value, _SECP256K1)
    peer = ec.EllipticCurvePublicKey.from_encoded_point(
        _SECP256K1, pub_key_compressed
    )
    return priv.exchange(ec.ECDH(), peer)


def _derive_aes_key(shared_x: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # equivalent to empty salt per RFC 5869
        info=ECIES_HKDF_INFO,
    ).derive(shared_x)


def derive_ecies_encrypt_key(recipient_pub: KeyLike) -> Tuple[bytes, bytes]:
    """
    Generate a fresh ephemeral keypair and derive the AES key for encryption.

    Returns ``(aes_key_32, ephemeral_pub_33)``.
    """
    recipient_compressed = normalize_pub_key(recipient_pub)

    ephemeral_priv_obj = ec.generate_private_key(_SECP256K1)
    ephemeral_priv = ephemeral_priv_obj.private_numbers().private_value.to_bytes(
        32, "big"
    )
    ephemeral_pub = ephemeral_priv_obj.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint,
    )

    shared_x = _ecdh_shared_x(ephemeral_priv, recipient_compressed)
    key = _derive_aes_key(shared_x)
    return key, ephemeral_pub


def derive_ecies_decrypt_key(recipient_priv: KeyLike, ephemeral_pub: bytes) -> bytes:
    """Recompute the AES key on the recipient side."""
    priv = normalize_priv_key(recipient_priv)
    shared_x = _ecdh_shared_x(priv, ephemeral_pub)
    return _derive_aes_key(shared_x)


# ── Header factories ───────────────────────────────────────────────────────


def new_symmetric_header() -> EncryptionHeader:
    """Create a v1 header with a fresh 16-byte nonce."""
    return EncryptionHeader(SYMMETRIC_VERSION, os.urandom(NONCE_SIZE))


def new_ecies_header(recipient_pub: KeyLike) -> Tuple[EncryptionHeader, bytes]:
    """
    Create a v2 header with a fresh nonce + ephemeral keypair and return it
    together with the derived AES key.
    """
    nonce = os.urandom(NONCE_SIZE)
    key, ephemeral_pub = derive_ecies_encrypt_key(recipient_pub)
    return EncryptionHeader(ECIES_VERSION, nonce, ephemeral_pub), key


# ── Decrypt helpers ────────────────────────────────────────────────────────


def decrypt_file(key: bytes, encrypted: bytes) -> bytes:
    """
    Decrypt a full downloaded file: parse the header, strip it, and decrypt
    the remaining bytes at CTR offset 0.
    """
    header = parse_encryption_header(encrypted)
    header_size = header.size()
    body = encrypted[header_size:]
    return crypt_at(key, header.nonce, 0, body)


@dataclass
class FragmentDecryptResult:
    plaintext: bytes
    new_offset: int


def decrypt_fragment_data(
    key: bytes,
    header: EncryptionHeader,
    fragment_data: bytes,
    is_first_fragment: bool,
    data_offset: int,
) -> FragmentDecryptResult:
    """
    Decrypt one fragment of a multi-fragment stream.

    - ``is_first_fragment=True``: fragment contains the encryption header at
      the start; strip it, decrypt the remainder starting at CTR offset 0,
      and return the plaintext plus its length as the new cumulative offset.
    - ``is_first_fragment=False``: fragment is pure ciphertext; decrypt
      starting at ``data_offset`` and return plaintext + advanced offset.
    """
    if is_first_fragment:
        header_size = header.size()
        if len(fragment_data) < header_size:
            raise ValueError(
                f"first fragment too short for encryption header: "
                f"{len(fragment_data)} bytes"
            )
        body = fragment_data[header_size:]
        plaintext = crypt_at(key, header.nonce, 0, body)
        return FragmentDecryptResult(plaintext=plaintext, new_offset=len(plaintext))

    plaintext = crypt_at(key, header.nonce, data_offset, fragment_data)
    return FragmentDecryptResult(
        plaintext=plaintext, new_offset=data_offset + len(plaintext)
    )


def resolve_decryption_key(
    symmetric_key: Optional[bytes],
    private_key: Optional[KeyLike],
    header: EncryptionHeader,
) -> bytes:
    """
    Pick the correct AES key for ``header.version`` from the optional
    materials. Errors cleanly if the required material is missing or malformed.
    """
    if header.version == SYMMETRIC_VERSION:
        if symmetric_key is None or len(symmetric_key) == 0:
            raise ValueError(
                "v1 encrypted file requires a symmetric key"
            )
        if len(symmetric_key) != 32:
            raise ValueError(
                f"symmetric key must be 32 bytes, got {len(symmetric_key)}"
            )
        return bytes(symmetric_key)
    if header.version == ECIES_VERSION:
        if private_key is None:
            raise ValueError("v2 encrypted file requires a private key")
        return derive_ecies_decrypt_key(private_key, header.ephemeral_pub)
    raise ValueError(f"unsupported encryption version: {header.version}")
