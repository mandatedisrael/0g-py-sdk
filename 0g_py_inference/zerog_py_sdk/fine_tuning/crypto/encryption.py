import logging
from typing import Optional

from web3 import Web3
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)

IV_LENGTH = 12
TAG_LENGTH = 16
SIG_LENGTH = 65
CHUNK_LENGTH = 64 * 1024 * 1024 + TAG_LENGTH  # ~64MB encrypted chunk + auth tag


def ecies_decrypt(private_key_hex: str, encrypted_data: bytes) -> bytes:
    """
    Decrypt data using ECIES with the user's private key.

    Args:
        private_key_hex: Hex-encoded private key (with or without 0x prefix)
        encrypted_data: ECIES-encrypted ciphertext

    Returns:
        Decrypted plaintext bytes (typically a hex-encoded AES key)
    """
    try:
        from ecies import decrypt as _ecies_decrypt
    except ImportError:
        raise ImportError(
            "eciespy is required for model decryption. "
            "Install with: pip install eciespy"
        )

    pk = private_key_hex
    if pk.startswith("0x") or pk.startswith("0X"):
        pk = pk[2:]

    private_key_bytes = bytes.fromhex(pk)
    return _ecies_decrypt(private_key_bytes, encrypted_data)


def aes_gcm_decrypt_to_file(
    key_hex: str,
    encrypted_path: str,
    decrypted_path: str,
    provider_signer: Optional[str] = None,
) -> None:
    """
    Decrypt an AES-GCM encrypted model file with chunked processing.

    File format:
        [tag_signature: 65 bytes][iv: 12 bytes][chunk1][chunk2]...[chunkN]

    Each chunk:
        [encrypted_data][auth_tag: 16 bytes]

    The IV increments (big-endian) for each successive chunk.
    After decryption, the concatenated auth tags are verified against
    the tag_signature using the provider's TEE signer address.

    Args:
        key_hex: Hex-encoded AES-256 key
        encrypted_path: Path to encrypted model file
        decrypted_path: Path to write decrypted output
        provider_signer: Expected signer address for tag verification (optional)
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError(
            "cryptography is required for model decryption. "
            "Install with: pip install cryptography"
        )

    key = bytes.fromhex(key_hex.lstrip("0x").lstrip("0X"))
    aesgcm = AESGCM(key)

    with open(encrypted_path, "rb") as f_in, open(decrypted_path, "wb") as f_out:
        tag_sig = f_in.read(SIG_LENGTH)
        if len(tag_sig) < SIG_LENGTH:
            raise ValueError("Encrypted file too small: missing tag signature")

        iv = bytearray(f_in.read(IV_LENGTH))
        if len(iv) < IV_LENGTH:
            raise ValueError("Encrypted file too small: missing IV")

        all_tags = b""

        while True:
            chunk = f_in.read(CHUNK_LENGTH)
            if not chunk:
                break

            if len(chunk) <= TAG_LENGTH:
                raise ValueError("Invalid chunk: smaller than auth tag")

            encrypted_data = chunk[:-TAG_LENGTH]
            auth_tag = chunk[-TAG_LENGTH:]
            all_tags += auth_tag

            # AES-GCM expects nonce + ciphertext+tag combined
            ciphertext_with_tag = encrypted_data + auth_tag
            decrypted = aesgcm.decrypt(bytes(iv), ciphertext_with_tag, None)
            f_out.write(decrypted)

            # Increment IV (big-endian counter)
            _increment_iv(iv)

    # Verify tag signature if provider signer is given
    if provider_signer and tag_sig and all_tags:
        _verify_tag_signature(all_tags, tag_sig, provider_signer)


def _increment_iv(iv: bytearray) -> None:
    for i in range(len(iv) - 1, -1, -1):
        iv[i] = (iv[i] + 1) & 0xFF
        if iv[i] != 0:
            break


def _verify_tag_signature(
    all_tags: bytes, tag_sig: bytes, expected_signer: str
) -> None:
    try:
        tags_hash = Web3.keccak(all_tags)
        signable = encode_defunct(primitive=tags_hash)
        from eth_account import Account

        recovered = Account.recover_message(signable, signature=tag_sig)
        if recovered.lower() != expected_signer.lower():
            logger.warning(
                "Tag signature signer mismatch. "
                "Expected: %s, Recovered: %s",
                expected_signer,
                recovered,
            )
        else:
            logger.info("Tag signature verified successfully")
    except Exception as e:
        logger.warning("Could not verify tag signature: %s", e)
