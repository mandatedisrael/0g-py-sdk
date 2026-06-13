import logging

from eth_keys import keys
from web3 import Web3

from ...exceptions import ModelVerificationError

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
    provider_signer: str,
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
        provider_signer: Expected signer address for tag verification
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

    if not all_tags:
        raise ModelVerificationError("Encrypted model contains no authenticated chunks")
    _verify_tag_signature(all_tags, tag_sig, provider_signer)


def _increment_iv(iv: bytearray) -> None:
    for i in range(len(iv) - 1, -1, -1):
        iv[i] = (iv[i] + 1) & 0xFF
        if iv[i] != 0:
            break


def _verify_tag_signature(
    all_tags: bytes, tag_sig: bytes, expected_signer: str
) -> None:
    if not expected_signer:
        raise ModelVerificationError("Provider TEE signer address is missing")
    if len(tag_sig) != SIG_LENGTH:
        raise ModelVerificationError(
            f"Tag signature must be {SIG_LENGTH} bytes, got {len(tag_sig)}"
        )

    try:
        tags_hash = Web3.keccak(all_tags)
        normalized_signature = bytearray(tag_sig)
        if normalized_signature[64] in (27, 28):
            normalized_signature[64] -= 27
        signature = keys.Signature(signature_bytes=bytes(normalized_signature))
        recovered = signature.recover_public_key_from_msg_hash(
            bytes(tags_hash)
        ).to_checksum_address()
        expected = Web3.to_checksum_address(expected_signer)
        if recovered.lower() != expected_signer.lower():
            raise ModelVerificationError(
                "TEE tag signer does not match the provider signer",
                expected_signer=expected,
                recovered_signer=recovered,
            )
        logger.info("Tag signature verified successfully")
    except ModelVerificationError:
        raise
    except Exception as e:
        raise ModelVerificationError(
            f"Invalid TEE tag signature: {e}",
            expected_signer=expected_signer,
        ) from e
