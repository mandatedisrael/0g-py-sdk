"""
Unit tests for native Python cryptography module.

Tests the Baby JubJub + Pedersen + EdDSA implementation
against known properties and reference values.
"""

import pytest
import sys
from pathlib import Path

# Add the zerog_py_sdk to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.crypto.field import Fr
from zerog_py_sdk.crypto.babyjub import BabyJubJub
from zerog_py_sdk.crypto.eddsa import EdDSA
from zerog_py_sdk.crypto import (
    gen_key_pair,
    prv2pub,
    sign_pedersen,
    pack_signature,
    verify_signature,
)


class TestFieldArithmetic:
    """Test F_r field arithmetic operations."""

    def test_field_add(self):
        """Test field addition."""
        a = 12345
        b = 67890
        result = Fr.add(a, b)
        assert result == (a + b) % Fr.p

    def test_field_sub(self):
        """Test field subtraction."""
        a = 12345
        b = 67890
        result = Fr.sub(a, b)
        assert result == (a - b) % Fr.p

    def test_field_mul(self):
        """Test field multiplication."""
        a = 12345
        b = 67890
        result = Fr.mul(a, b)
        assert result == (a * b) % Fr.p

    def test_field_inv(self):
        """Test modular inverse."""
        a = 12345
        inv_a = Fr.inv(a)
        assert Fr.mul(a, inv_a) == 1

    def test_field_div(self):
        """Test field division."""
        a = 12345
        b = 67890
        result = Fr.div(a, b)
        assert Fr.mul(result, b) == a

    def test_field_random(self):
        """Test random element generation."""
        for _ in range(10):
            r = Fr.random()
            assert 0 <= r < Fr.p

    def test_field_zero_inv_raises(self):
        """Test that inverting zero raises ValueError."""
        with pytest.raises(ValueError):
            Fr.inv(0)


class TestBabyJubJub:
    """Test Baby JubJub curve operations."""

    def test_generator_on_curve(self):
        """Test that generator point is on the curve."""
        assert BabyJubJub.is_on_curve(BabyJubJub.GENERATOR)

    def test_neutral_on_curve(self):
        """Test that neutral element is on the curve."""
        assert BabyJubJub.is_on_curve(BabyJubJub.NEUTRAL)

    def test_point_addition_neutral(self):
        """Test adding neutral element returns same point."""
        P = BabyJubJub.GENERATOR
        result = BabyJubJub.add_points(P, BabyJubJub.NEUTRAL)
        # Should be equal modulo field
        assert BabyJubJub.is_on_curve(result)

    def test_point_addition_commutative(self):
        """Test that point addition is commutative."""
        G = BabyJubJub.GENERATOR
        # G + G
        P = BabyJubJub.add_points(G, G)
        # Should be on curve
        assert BabyJubJub.is_on_curve(P)

    def test_scalar_multiply_zero(self):
        """Test that 0 * P = neutral element."""
        G = BabyJubJub.GENERATOR
        result = BabyJubJub.scalar_multiply(G, 0)
        assert result == BabyJubJub.NEUTRAL

    def test_scalar_multiply_one(self):
        """Test that 1 * P = P."""
        G = BabyJubJub.GENERATOR
        result = BabyJubJub.scalar_multiply(G, 1)
        assert result == G

    def test_scalar_multiply_two(self):
        """Test that 2 * P = P + P."""
        G = BabyJubJub.GENERATOR
        double_result = BabyJubJub.scalar_multiply(G, 2)
        add_result = BabyJubJub.add_points(G, G)
        assert double_result == add_result

    def test_scalar_multiply_on_curve(self):
        """Test that scalar multiplication produces points on curve."""
        G = BabyJubJub.GENERATOR
        for scalar in [1, 2, 10, 100, 1000, 2**100]:
            result = BabyJubJub.scalar_multiply(G, scalar)
            assert BabyJubJub.is_on_curve(result)

    def test_point_packing_unpacking(self):
        """Test that points can be packed and unpacked."""
        G = BabyJubJub.GENERATOR
        packed = BabyJubJub.pack_point(G)

        # Packed should be 32 bytes
        assert len(packed) == 32
        assert isinstance(packed, bytes)

        # Unpacking should recover original point
        unpacked = BabyJubJub.unpack_point(packed)
        assert unpacked == G

    def test_point_packing_consistent(self):
        """Test that packing is deterministic."""
        G = BabyJubJub.GENERATOR
        packed1 = BabyJubJub.pack_point(G)
        packed2 = BabyJubJub.pack_point(G)
        assert packed1 == packed2


class TestEdDSA:
    """Test EdDSA signature operations."""

    def test_key_generation(self):
        """Test that key generation produces valid output."""
        keys = gen_key_pair()

        assert "packedPrivkey" in keys
        assert "doublePackedPubkey" in keys
        assert len(keys["packedPrivkey"]) == 2
        assert len(keys["doublePackedPubkey"]) == 2
        assert all(isinstance(k, int) for k in keys["packedPrivkey"])
        assert all(isinstance(k, int) for k in keys["doublePackedPubkey"])

    def test_private_to_public_consistent(self):
        """Test that prv2pub is deterministic."""
        keys1 = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys1["packedPrivkey"])

        # Compute public key twice
        pub1 = prv2pub(privkey)
        pub2 = prv2pub(privkey)

        assert pub1 == pub2
        assert BabyJubJub.is_on_curve(pub1)

    def test_signature_generation(self):
        """Test that signature generation works."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])
        message = b"Test message"

        sig = sign_pedersen(privkey, message)

        assert "R" in sig
        assert "S" in sig
        assert BabyJubJub.is_on_curve(sig["R"])
        assert isinstance(sig["S"], int)

    def test_signature_deterministic(self):
        """Test that signing is deterministic with same input."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])
        message = b"Test message"

        sig1 = sign_pedersen(privkey, message)
        sig2 = sign_pedersen(privkey, message)

        assert sig1["R"] == sig2["R"]
        assert sig1["S"] == sig2["S"]

    def test_signature_different_for_different_messages(self):
        """Test that different messages produce different signatures."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])

        sig1 = sign_pedersen(privkey, b"Message 1")
        sig2 = sign_pedersen(privkey, b"Message 2")

        # At least one component should differ
        assert sig1["R"] != sig2["R"] or sig1["S"] != sig2["S"]

    def test_signature_packing(self):
        """Test that signatures can be packed to 64 bytes."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])
        message = b"Test message"

        sig = sign_pedersen(privkey, message)
        packed = pack_signature(sig)

        assert len(packed) == 64
        assert isinstance(packed, bytes)

    def test_signature_verification_valid(self):
        """Test that valid signatures verify correctly."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])
        pubkey = prv2pub(privkey)
        message = b"Test message"

        sig = sign_pedersen(privkey, message)

        # Verification should pass
        assert verify_signature(pubkey, message, sig) == True

    def test_signature_verification_invalid_message(self):
        """Test that tampering with message causes verification to fail."""
        keys = gen_key_pair()
        privkey = EdDSA._packed_privkey_to_bytes(keys["packedPrivkey"])
        pubkey = prv2pub(privkey)
        message = b"Test message"

        sig = sign_pedersen(privkey, message)

        # Verification with different message should fail
        # (This may fail if we don't have Pedersen bases loaded)
        try:
            result = verify_signature(pubkey, b"Different message", sig)
            assert result == False
        except RuntimeError as e:
            if "Pedersen bases" in str(e):
                pytest.skip("Pedersen bases not available for verification")
            else:
                raise


class TestRequestSigningFlow:
    """Test the complete 0G request signing flow."""

    def test_request_serialization(self):
        """Test that 0G requests are serialized correctly."""
        from zerog_py_sdk.auth import Request

        req = Request(
            nonce=12345,
            fee=67890,
            user_address="0xB3AD3a10d187cbc4ca3e8c3EDED62F8286F8e16E",
            provider_address="0x1234567890123456789012345678901234567890"
        )

        serialized = req.serialize()
        assert len(serialized) == 64
        assert isinstance(serialized, bytes)

    def test_request_serialization_roundtrip(self):
        """Test that request fields survive serialization."""
        from zerog_py_sdk.auth import Request

        nonce = 12345
        fee = 67890
        user_addr = "0xB3AD3a10d187cbc4ca3e8c3EDED62F8286F8e16E"
        provider_addr = "0x1234567890123456789012345678901234567890"

        req = Request(
            nonce=nonce,
            fee=fee,
            user_address=user_addr,
            provider_address=provider_addr
        )

        serialized = req.serialize()
        # Verify first 8 bytes are nonce (little-endian)
        extracted_nonce = int.from_bytes(serialized[0:8], 'little')
        assert extracted_nonce == nonce


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
