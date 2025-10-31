"""
EdDSA signature implementation for Baby JubJub.

Implements the EdDSA (Edwards-curve Digital Signature Algorithm) using:
- Baby JubJub twisted Edwards curve
- Pedersen hash for the hash function
- Little-endian serialization for compatibility

This creates signatures suitable for zero-knowledge proof verification.

Reference: RFC 8032 (with modifications for Baby JubJub)
"""

import hashlib
from typing import Dict, Tuple, List
from .babyjub import BabyJubJub
from .field import Fr
from .pedersen import PedersenHash


class EdDSA:
    """EdDSA signature operations for Baby JubJub."""

    @staticmethod
    def gen_key_pair() -> Dict:
        """
        Generate a random EdDSA key pair on Baby JubJub.

        Returns:
            Dictionary with:
            {
                "packedPrivkey": [upper_16_bytes_as_int, lower_16_bytes_as_int],
                "doublePackedPubkey": [packed_x_16_bytes, packed_y_16_bytes]
            }

        The format matches the TypeScript SDK exactly for compatibility.
        """
        # Generate random private key in F_r
        privkey = Fr.random()

        # Derive public key from private key
        # pubkey = privkey * G (scalar multiplication of generator)
        pubkey = BabyJubJub.scalar_multiply(BabyJubJub.GENERATOR, privkey)

        # Convert to bytes for packing
        privkey_bytes = _bigint_to_le_bytes(privkey, 32)
        pubkey_packed = BabyJubJub.pack_point(pubkey)

        # Pack into 2x16 byte format for 0G protocol
        packed_privkey = [
            _le_bytes_to_bigint(privkey_bytes[0:16]),
            _le_bytes_to_bigint(privkey_bytes[16:32])
        ]

        packed_pubkey = [
            _le_bytes_to_bigint(pubkey_packed[0:16]),
            _le_bytes_to_bigint(pubkey_packed[16:32])
        ]

        return {
            "packedPrivkey": packed_privkey,
            "doublePackedPubkey": packed_pubkey
        }

    @staticmethod
    def prv2pub(privkey: bytes) -> Tuple[int, int]:
        """
        Derive public key from private key.

        Args:
            privkey: Private key (32 bytes, little-endian)

        Returns:
            Public key point (x, y) on Baby JubJub
        """
        # Convert bytes to integer (little-endian)
        privkey_int = _le_bytes_to_bigint(privkey)

        # Compute public key: A = privkey * B
        return BabyJubJub.scalar_multiply(BabyJubJub.GENERATOR, privkey_int)

    @staticmethod
    def sign_pedersen(privkey: bytes, message: bytes) -> Dict:
        """
        Sign a message using EdDSA with Pedersen hash.

        This implements the EdDSA signature algorithm with Pedersen hash
        as the underlying hash function, matching circomlibjs behavior.

        Args:
            privkey: Private key (32 bytes, little-endian)
            message: Message to sign (bytes)

        Returns:
            Dictionary with signature:
            {
                "R": (x, y) point on Baby JubJub,
                "S": scalar value
            }

        Algorithm:
        1. Hash private key with SHA-512: hash_bytes = SHA512(privkey)
        2. Extract prefix from second half: prefix = hash_bytes[32:64]
        3. Compute nonce: r = Pedersen(prefix || message) mod order
        4. Compute point: R = r * G
        5. Compute public key: A = privkey * G
        6. Compute challenge: H = Pedersen(R || A || message) mod order
        7. Compute signature: S = (r + H * privkey) mod order
        8. Return (R, S)
        """

        # Convert private key from bytes to integer
        privkey_int = _le_bytes_to_bigint(privkey)

        # 1. Hash the private key (SHA-512)
        privkey_hash = hashlib.sha512(privkey).digest()
        # Extract prefix (second half of hash, bytes 32-64)
        prefix = privkey_hash[32:64]

        # 2. Compute nonce from prefix and message
        # r = Pedersen(prefix || message) mod order
        nonce_data = prefix + message
        r_hash = PedersenHash.hash(nonce_data)
        r_value = int(r_hash, 16) % BabyJubJub.order

        # 3. Compute R point
        # R = r * G
        R = BabyJubJub.scalar_multiply(BabyJubJub.GENERATOR, r_value)

        # 4. Compute public key
        # A = privkey * G
        A = BabyJubJub.scalar_multiply(BabyJubJub.GENERATOR, privkey_int)

        # 5. Compute challenge (Pedersen hash of R, A, and message)
        # Serialize R and A points
        R_packed = BabyJubJub.pack_point(R)
        A_packed = BabyJubJub.pack_point(A)

        # H = Pedersen(R_packed || A_packed || message) mod order
        challenge_data = R_packed + A_packed + message
        H_hash = PedersenHash.hash(challenge_data)
        H_value = int(H_hash, 16) % BabyJubJub.order

        # 6. Compute signature scalar
        # S = (r + H * privkey) mod order
        S = (r_value + H_value * privkey_int) % BabyJubJub.order

        return {
            "R": R,
            "S": S
        }

    @staticmethod
    def pack_signature(signature: Dict) -> bytes:
        """
        Pack EdDSA signature to 64 bytes.

        Format:
        - Bytes 0-31: R point x-coordinate (little-endian)
        - Bytes 32-63: S scalar (little-endian)

        Args:
            signature: Dictionary with "R": (x, y) and "S": scalar

        Returns:
            64-byte packed signature
        """
        R_point = signature["R"]
        S_scalar = signature["S"]

        # Pack R point (32 bytes)
        R_packed = BabyJubJub.pack_point(R_point)

        # Pack S scalar (32 bytes, little-endian)
        S_packed = _bigint_to_le_bytes(S_scalar, 32)

        # Concatenate
        return R_packed + S_packed

    @staticmethod
    def verify_signature(pubkey: Tuple[int, int], message: bytes, signature: Dict) -> bool:
        """
        Verify an EdDSA signature.

        Args:
            pubkey: Public key point (x, y)
            message: Original message
            signature: Signature dictionary with "R" and "S"

        Returns:
            True if signature is valid, False otherwise

        The verification equation (from EdDSA spec):
            [8][S]B = [8]R + [8][H]A
            where H = Pedersen(R || A || message)

        This check ensures only the holder of the private key could have
        created the signature without revealing the private key.
        """
        try:
            R = signature["R"]
            S = signature["S"]

            # Verify points are on curve
            if not BabyJubJub.is_on_curve(pubkey):
                return False
            if not BabyJubJub.is_on_curve(R):
                return False

            # Compute challenge
            R_packed = BabyJubJub.pack_point(R)
            A_packed = BabyJubJub.pack_point(pubkey)
            challenge_data = R_packed + A_packed + message
            H_hash = PedersenHash.hash(challenge_data)
            H_value = int(H_hash, 16) % BabyJubJub.order

            # Verify equation: [8][S]B = [8]R + [8][H]A
            # Left side: 8 * S * B
            left = BabyJubJub.scalar_multiply(BabyJubJub.GENERATOR, (8 * S) % BabyJubJub.order)

            # Right side: 8 * R + 8 * H * A
            right_term1 = BabyJubJub.scalar_multiply(R, 8)
            right_term2 = BabyJubJub.scalar_multiply(pubkey, (8 * H_value) % BabyJubJub.order)
            right = BabyJubJub.add_points(right_term1, right_term2)

            # Compare
            return left == right

        except Exception as e:
            print(f"Signature verification error: {e}")
            return False


# Utility functions for byte conversion

def _bigint_to_le_bytes(value: int, length: int) -> bytes:
    """Convert integer to little-endian bytes."""
    result = bytearray(length)
    for i in range(length):
        result[i] = (value >> (8 * i)) & 0xff
    return bytes(result)


def _le_bytes_to_bigint(data: bytes) -> int:
    """Convert little-endian bytes to integer."""
    result = 0
    for i, byte in enumerate(data):
        result |= byte << (8 * i)
    return result


def _be_bytes_to_bigint(data: bytes) -> int:
    """Convert big-endian bytes to integer."""
    result = 0
    for byte in data:
        result = (result << 8) | byte
    return result
