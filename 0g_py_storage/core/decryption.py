"""
Best-effort post-download decryption helpers.

Direct port of ``src.ts/indexer/decryption.ts``. Both helpers are
intentionally non-throwing for decryption-related reasons: if the file
isn't actually encrypted, the embedded ephemeral pubkey isn't on-curve,
or the wrong key material was supplied, they return the raw bytes
unchanged with ``decrypted=False`` so the caller can fall back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

try:
    from .encryption import (
        ECIES_VERSION,
        EncryptionHeader,
        KeyLike,
        decrypt_file,
        decrypt_fragment_data,
        parse_encryption_header,
        resolve_decryption_key,
    )
except ImportError:  # pragma: no cover - test runner fallback
    from core.encryption import (
        ECIES_VERSION,
        EncryptionHeader,
        KeyLike,
        decrypt_file,
        decrypt_fragment_data,
        parse_encryption_header,
        resolve_decryption_key,
    )

from cryptography.hazmat.primitives.asymmetric import ec


_SECP256K1 = ec.SECP256K1()


@dataclass
class TryDecryptResult:
    bytes: bytes
    decrypted: bool


def _ephemeral_on_curve(ephemeral_pub: bytes) -> bool:
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(_SECP256K1, ephemeral_pub)
        return True
    except Exception:
        return False


def try_decrypt(
    encrypted: bytes,
    symmetric_key: Optional[bytes] = None,
    private_key: Optional[KeyLike] = None,
) -> TryDecryptResult:
    """
    Best-effort decrypt. Returns ``(bytes, decrypted)``. Never throws for
    decryption-related reasons — any failure returns the raw bytes with
    ``decrypted=False``.
    """
    if len(encrypted) < 1:
        return TryDecryptResult(bytes=encrypted, decrypted=False)

    try:
        header = parse_encryption_header(encrypted)
    except Exception:
        return TryDecryptResult(bytes=encrypted, decrypted=False)

    # AES-CTR is unauthenticated; without the on-curve check a plaintext
    # file that happens to start with 0x02 would "decrypt" to garbage.
    if header.version == ECIES_VERSION and not _ephemeral_on_curve(
        header.ephemeral_pub
    ):
        return TryDecryptResult(bytes=encrypted, decrypted=False)

    try:
        aes_key = resolve_decryption_key(symmetric_key, private_key, header)
    except Exception:
        return TryDecryptResult(bytes=encrypted, decrypted=False)

    try:
        plaintext = decrypt_file(aes_key, encrypted)
    except Exception:
        return TryDecryptResult(bytes=encrypted, decrypted=False)
    return TryDecryptResult(bytes=plaintext, decrypted=True)


def try_decrypt_fragments(
    fragments: List[bytes],
    symmetric_key: Optional[bytes] = None,
    private_key: Optional[KeyLike] = None,
) -> Optional[List[bytes]]:
    """
    Best-effort multi-fragment decrypt. Mirrors 0g-storage-client's
    ``indexer/client.go::downloadEncryptedFragments``: parse the header from
    fragment 0, resolve the AES key, then decrypt each subsequent fragment at
    the correct CTR offset so mid-stream fragments decrypt identically to a
    full-file decrypt.

    Returns a list of plaintext fragments, or ``None`` on any failure so the
    caller can fall back to the raw concatenation.
    """
    if len(fragments) == 0:
        return []

    try:
        header = parse_encryption_header(fragments[0])
    except Exception:
        return None

    if header.version == ECIES_VERSION and not _ephemeral_on_curve(
        header.ephemeral_pub
    ):
        return None

    try:
        aes_key = resolve_decryption_key(symmetric_key, private_key, header)
    except Exception:
        return None

    plaintexts: List[bytes] = []
    cumulative_offset = 0
    for i, fragment in enumerate(fragments):
        try:
            result = decrypt_fragment_data(
                aes_key,
                header,
                fragment,
                i == 0,
                cumulative_offset,
            )
        except Exception:
            return None
        plaintexts.append(result.plaintext)
        cumulative_offset = result.new_offset
    return plaintexts
