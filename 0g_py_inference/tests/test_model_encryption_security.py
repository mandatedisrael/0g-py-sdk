from pathlib import Path

import pytest
from eth_keys import keys
from web3 import Web3

from zerog_py_sdk.exceptions import ModelVerificationError
from zerog_py_sdk.fine_tuning.crypto.encryption import (
    IV_LENGTH,
    aes_gcm_decrypt_to_file,
)

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PRIVATE_KEY = keys.PrivateKey(bytes.fromhex("11" * 32))
PROVIDER_SIGNER = PRIVATE_KEY.public_key.to_checksum_address()
AES_KEY = bytes.fromhex("22" * 32)
IV = bytes.fromhex("33" * IV_LENGTH)
PLAINTEXT = b"verified model artifact"


def _write_encrypted_model(
    path: Path,
    *,
    plaintext: bytes = PLAINTEXT,
    signing_key: keys.PrivateKey = PRIVATE_KEY,
) -> None:
    ciphertext_with_tag = AESGCM(AES_KEY).encrypt(IV, plaintext, None)
    encrypted_data = ciphertext_with_tag[:-16]
    auth_tag = ciphertext_with_tag[-16:]
    signature = bytearray(
        signing_key.sign_msg_hash(bytes(Web3.keccak(auth_tag))).to_bytes()
    )
    signature[64] += 27
    path.write_bytes(bytes(signature) + IV + encrypted_data + auth_tag)


def _temporary_outputs(destination: Path):
    return list(destination.parent.glob(f".{destination.name}.*.part"))


def test_decrypts_model_with_raw_ethereum_tag_signature(tmp_path):
    encrypted = tmp_path / "model.encrypted"
    decrypted = tmp_path / "model.bin"
    _write_encrypted_model(encrypted)

    aes_gcm_decrypt_to_file(
        AES_KEY.hex(),
        str(encrypted),
        str(decrypted),
        PROVIDER_SIGNER,
    )

    assert decrypted.read_bytes() == PLAINTEXT
    assert _temporary_outputs(decrypted) == []


def test_wrong_signer_preserves_existing_destination(tmp_path):
    encrypted = tmp_path / "model.encrypted"
    decrypted = tmp_path / "model.bin"
    decrypted.write_bytes(b"existing verified model")
    _write_encrypted_model(encrypted)
    wrong_signer = keys.PrivateKey(
        bytes.fromhex("44" * 32)
    ).public_key.to_checksum_address()

    with pytest.raises(ModelVerificationError, match="does not match"):
        aes_gcm_decrypt_to_file(
            AES_KEY.hex(),
            str(encrypted),
            str(decrypted),
            wrong_signer,
        )

    assert decrypted.read_bytes() == b"existing verified model"
    assert _temporary_outputs(decrypted) == []


def test_corrupt_ciphertext_is_not_published(tmp_path):
    encrypted = tmp_path / "model.encrypted"
    decrypted = tmp_path / "model.bin"
    _write_encrypted_model(encrypted)
    corrupted = bytearray(encrypted.read_bytes())
    corrupted[-1] ^= 0x01
    encrypted.write_bytes(corrupted)

    with pytest.raises(ModelVerificationError, match="authentication failed"):
        aes_gcm_decrypt_to_file(
            AES_KEY.hex(),
            str(encrypted),
            str(decrypted),
            PROVIDER_SIGNER,
        )

    assert not decrypted.exists()
    assert _temporary_outputs(decrypted) == []


@pytest.mark.parametrize(
    ("key_hex", "message"),
    [
        ("not-hex", "valid AES key"),
        ("12", "valid AES key"),
    ],
)
def test_invalid_aes_key_is_typed_verification_error(
    tmp_path, key_hex, message
):
    encrypted = tmp_path / "model.encrypted"
    _write_encrypted_model(encrypted)

    with pytest.raises(ModelVerificationError, match=message):
        aes_gcm_decrypt_to_file(
            key_hex,
            str(encrypted),
            str(tmp_path / "model.bin"),
            PROVIDER_SIGNER,
        )


def test_missing_signer_is_not_published(tmp_path):
    encrypted = tmp_path / "model.encrypted"
    decrypted = tmp_path / "model.bin"
    _write_encrypted_model(encrypted)

    with pytest.raises(ModelVerificationError, match="signer address is missing"):
        aes_gcm_decrypt_to_file(
            AES_KEY.hex(),
            str(encrypted),
            str(decrypted),
            "",
        )

    assert not decrypted.exists()
    assert _temporary_outputs(decrypted) == []
