"""
Pedersen hash implementation for Baby JubJub.

Implements the Pedersen hash function as specified in circomlibjs and ERC-2494.
This is a deterministic hash function that maps arbitrary data to a Baby JubJub point.

The Pedersen hash is computed as a linear combination of precomputed generator points:
    H(message) = Σ(enc(m_i) · P_i)

Where:
- enc(m_i) is the encoding of a 4-bit chunk
- P_i are precomputed generator points
- The result is a Baby JubJub point coordinate (x, y)

This implementation uses 4-bit windowing for efficiency, matching circomlibjs exactly.

Reference: iden3 Pedersen Hash documentation
"""

from .babyjub import BabyJubJub
from .field import Fr
from typing import Tuple


# Precomputed Pedersen hash generator bases
# These are derived deterministically from the Baby JubJub curve
# and must match circomlibjs exactly for compatibility.
# Will be lazily loaded on first use via pedersen_bases module
PEDERSEN_BASES = None  # Lazy-loaded on first hash operation


class PedersenHash:
    """Pedersen hash implementation."""

    @staticmethod
    def hash(data: bytes) -> str:
        """
        Compute Pedersen hash of input data.

        Args:
            data: Input data to hash (bytes)

        Returns:
            Pedersen hash as '0x' + hex string of x-coordinate

        Algorithm:
        1. Pad data to multiple of 4-bit chunks
        2. For each 4-bit chunk: compute enc(chunk) scalar
        3. Multiply each Pedersen base by its scalar: enc(m_i) * P_i
        4. Sum all points using Baby JubJub addition
        5. Return x-coordinate as hex
        """

        global PEDERSEN_BASES

        # Lazy load bases on first use
        if PEDERSEN_BASES is None:
            _load_bases()

        # Convert bytes to bit array
        bits = _bytes_to_bits(data)

        # Pad to multiple of 4 bits
        if len(bits) % 4 != 0:
            bits.extend([0] * (4 - len(bits) % 4))

        # Process 4-bit chunks
        result = BabyJubJub.NEUTRAL

        for i in range(0, len(bits), 4):
            # Extract 4-bit chunk
            chunk_bits = bits[i:i+4]
            chunk = _bits_to_int(chunk_bits)

            # Encode chunk to scalar
            scalar = _encode_chunk(chunk)

            # Get corresponding base point (wraparound if needed)
            base_index = i // 4
            if base_index >= len(PEDERSEN_BASES):
                break

            base_point = PEDERSEN_BASES[base_index]

            # Multiply base by scalar and add to result
            if scalar != 0:
                point_product = BabyJubJub.scalar_multiply(base_point, abs(scalar))

                if scalar < 0:
                    # Negate the point if scalar is negative
                    point_product = (point_product[0], Fr.neg(point_product[1]))

                result = BabyJubJub.add_points(result, point_product)

        # Return x-coordinate as 0x-prefixed hex string
        x_coord = result[0]
        x_hex = format(x_coord, '064x')
        return '0x' + x_hex


def _bytes_to_bits(data: bytes) -> list:
    """Convert bytes to list of bits (MSB first)."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def _bits_to_int(bits: list) -> int:
    """Convert bit list to integer."""
    result = 0
    for bit in bits:
        result = (result << 1) | bit
    return result


def _encode_chunk(chunk: int) -> int:
    """
    Encode a 4-bit chunk to a signed scalar.

    Formula (from Pedersen hash specification):
        enc(m) = (2*b3 - 1) * (1 + b0 + 2*b1 + 4*b2)

    Where m = [b3, b2, b1, b0] (4 bits, MSB first)

    This produces a signed value representing how to scale the Pedersen base point.
    The formula cleverly uses:
    - (2*b3 - 1): Sign (+1 if b3=1, -1 if b3=0)
    - (1 + b0 + 2*b1 + 4*b2): Magnitude (range 1-8)

    Result range: {-8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8}

    Args:
        chunk: 4-bit value (0-15)

    Returns:
        Signed scalar for Pedersen calculation
    """
    # Extract bits
    b0 = (chunk >> 0) & 1
    b1 = (chunk >> 1) & 1
    b2 = (chunk >> 2) & 1
    b3 = (chunk >> 3) & 1

    # Compute sign and magnitude
    sign = 2 * b3 - 1  # -1 or +1
    magnitude = 1 + b0 + 2 * b1 + 4 * b2  # 1-8

    return sign * magnitude


def _load_bases():
    """Load Pedersen bases using the pedersen_bases module."""
    global PEDERSEN_BASES

    try:
        from . import pedersen_bases
        PEDERSEN_BASES = pedersen_bases.get_pedersen_bases()
        print(f"✓ Loaded {len(PEDERSEN_BASES)} Pedersen bases")
    except Exception as e:
        raise RuntimeError(
            f"Failed to load Pedersen bases: {e}\n"
            "This is required for Pedersen hash computation.\n"
            "Try running: node extract_pedersen_bases.mjs"
        )


def initialize_pedersen_bases(bases: list):
    """
    Initialize Pedersen hash generator bases.

    This must be called before using PedersenHash.hash().

    Args:
        bases: List of Baby JubJub points (tuples of (x, y))
    """
    global PEDERSEN_BASES
    PEDERSEN_BASES = bases
    print(f"✓ Initialized {len(bases)} Pedersen bases")
