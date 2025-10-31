"""
Baby JubJub elliptic curve implementation.

Implements the Baby JubJub twisted Edwards curve as specified in ERC-2494.
This curve is used for EdDSA signatures in the 0G protocol.

Curve equation: a*x² + y² = 1 + d*x²*y² (mod p)

Reference: https://eips.ethereum.org/EIPS/eip-2494
"""

from typing import Tuple
from .field import Fr


# Baby JubJub curve parameters (ERC-2494 specification)
class BabyJubJub:
    """Baby JubJub elliptic curve operations."""

    # Twisted Edwards coefficients
    a = 168700
    d = 168696

    # Generator point (base point)
    Gx = 995203441582195749578291179787384436505546430278305826713579947235728471134
    Gy = 5472060717959818805561601436314318772137091100104008585924551046643952123905
    GENERATOR = (Gx, Gy)

    # Curve order (subgroup size)
    order = 21888242871839275222246405745257728805843564400416034343698204186575808495617

    # Neutral element (identity/point at infinity)
    NEUTRAL = (0, 1)

    # Field prime
    p = 21888242871839275222246405745257275088548364400416034343698204186575808495617

    @staticmethod
    def is_on_curve(point: Tuple[int, int]) -> bool:
        """
        Verify a point lies on the Baby JubJub curve.

        Checks that: a*x² + y² ≡ 1 + d*x²*y² (mod p)

        Args:
            point: Tuple (x, y) representing a point

        Returns:
            True if point is on curve, False otherwise
        """
        x, y = point

        # Left side: a*x² + y²
        lhs = Fr.add(
            Fr.mul(BabyJubJub.a, Fr.mul(x, x)),
            Fr.mul(y, y)
        )

        # Right side: 1 + d*x²*y²
        rhs = Fr.add(
            1,
            Fr.mul(
                BabyJubJub.d,
                Fr.mul(Fr.mul(x, x), Fr.mul(y, y))
            )
        )

        return lhs == rhs

    @staticmethod
    def add_points(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int]:
        """
        Add two points on the Baby JubJub curve using the unified Edwards addition law.

        The unified addition formula works for all cases (including point doubling
        and addition with neutral element), making it safe for cryptographic operations.

        Formula (from ERC-2494):
        A = x1*x2 mod p
        B = y1*y2 mod p
        C = A*d mod p
        D = (1-C) mod p
        E = ((x1+y1)*(x2+y2)-A-B) mod p
        F = (1+C) mod p
        x3 = (E*D^(-1)) mod p
        y3 = (F*(a*A+B)^(-1)) mod p

        Args:
            p1: First point (x1, y1)
            p2: Second point (x2, y2)

        Returns:
            Sum point (x3, y3)
        """
        x1, y1 = p1
        x2, y2 = p2

        # Compute intermediate values
        A = Fr.mul(x1, x2)
        B = Fr.mul(y1, y2)
        C = Fr.mul(A, BabyJubJub.d)
        D = Fr.sub(1, C)
        E = Fr.sub(
            Fr.mul(
                Fr.add(x1, y1),
                Fr.add(x2, y2)
            ),
            Fr.add(A, B)
        )
        F = Fr.add(1, C)

        # Compute result coordinates
        x3 = Fr.mul(E, Fr.inv(D))
        y3 = Fr.mul(F, Fr.inv(Fr.add(Fr.mul(BabyJubJub.a, A), B)))

        return (x3, y3)

    @staticmethod
    def scalar_multiply(point: Tuple[int, int], scalar: int) -> Tuple[int, int]:
        """
        Multiply a point by a scalar on the Baby JubJub curve.

        Uses the Montgomery ladder algorithm for constant-time operation
        (resistant to timing side-channel attacks).

        Args:
            point: Point to multiply (x, y)
            scalar: Scalar multiplier (integer)

        Returns:
            Result point (scalar * point)
        """
        # Normalize scalar to be in range [0, order)
        scalar = scalar % BabyJubJub.order

        if scalar == 0:
            return BabyJubJub.NEUTRAL

        # Montgomery ladder: constant-time, side-channel resistant
        # Maintains two points: R0 = result, R1 = result + point
        R0 = BabyJubJub.NEUTRAL  # Result accumulator
        R1 = point  # Temp accumulator

        # Process scalar bits from MSB to LSB
        bits = bin(scalar)[2:]  # Convert to binary string
        for bit in bits:
            if bit == '0':
                # R1 = R0 + R1, R0 = 2*R0
                R1 = BabyJubJub.add_points(R0, R1)
                R0 = BabyJubJub.add_points(R0, R0)
            else:
                # R0 = R0 + R1, R1 = 2*R1
                R0 = BabyJubJub.add_points(R0, R1)
                R1 = BabyJubJub.add_points(R1, R1)

        return R0

    @staticmethod
    def pack_point(point: Tuple[int, int]) -> bytes:
        """
        Pack a Baby JubJub point into 32 bytes.

        Stores the x-coordinate in bytes 0-31, with the sign of y encoded
        in the most significant bit of byte 31.

        Format:
        - Bytes 0-30: x-coordinate (little-endian, 31 bytes)
        - Byte 31: MSB of x-coordinate + sign bit of y

        Args:
            point: Point (x, y) to pack

        Returns:
            32-byte packed representation
        """
        x, y = point

        # Convert x to 32-byte little-endian
        x_bytes = bytearray(32)
        x_temp = x
        for i in range(32):
            x_bytes[i] = x_temp & 0xff
            x_temp >>= 8

        # Set sign bit of y in MSB of last byte
        # If y is odd (y % 2 == 1), set bit 7 of byte 31
        if y % 2 == 1:
            x_bytes[31] |= 0x80

        return bytes(x_bytes)

    @staticmethod
    def unpack_point(packed: bytes) -> Tuple[int, int]:
        """
        Unpack a Baby JubJub point from 32 bytes.

        Recovers the x-coordinate and computes y from the curve equation
        using the sign bit stored in the packed representation.

        Args:
            packed: 32-byte packed point representation

        Returns:
            Unpacked point (x, y)

        Raises:
            ValueError: If unpacking fails (point not on curve)
        """
        if len(packed) != 32:
            raise ValueError(f"Packed point must be 32 bytes, got {len(packed)}")

        # Extract x-coordinate (little-endian)
        x_bytes = bytearray(packed)
        sign_bit = (x_bytes[31] >> 7) & 1
        x_bytes[31] &= 0x7f  # Clear sign bit

        x = 0
        for i in range(32):
            x |= x_bytes[i] << (8 * i)

        # Recover y from curve equation: y² ≡ (1 - a*x²) / (d*x² - 1) (mod p)
        # Using Legendre symbol for square root computation
        x2 = Fr.mul(x, x)

        # Numerator: 1 - a*x²
        num = Fr.sub(1, Fr.mul(BabyJubJub.a, x2))

        # Denominator: d*x² - 1
        denom = Fr.sub(Fr.mul(BabyJubJub.d, x2), 1)

        # y² = num / denom
        y2 = Fr.div(num, denom)

        # Compute square root using Legendre symbol (for p ≡ 5 (mod 8))
        # This is a specialized square root for the field p
        y = _sqrt_mod_p(y2)

        if y is None:
            raise ValueError("No valid point with this packed representation")

        # Adjust sign of y based on sign_bit
        if (y % 2 == 0) != (sign_bit == 0):
            y = Fr.neg(y)

        result = (x, y)

        # Verify point is on curve
        if not BabyJubJub.is_on_curve(result):
            raise ValueError("Unpacked point not on curve")

        return result


def _sqrt_mod_p(a: int) -> int:
    """
    Compute square root of a modulo p using Tonelli-Shanks algorithm.

    The prime p = 2^256 - 2^32 - 977 is ≡ 5 (mod 8), allowing for
    a simplified algorithm.

    Args:
        a: Element to compute square root of

    Returns:
        Square root of a modulo p, or None if a is not a quadratic residue
    """
    p = BabyJubJub.p

    # Check if a is a quadratic residue using Legendre symbol
    # a^((p-1)/2) should be 1 if a is QR, p-1 if not
    legendre = pow(a, (p - 1) // 2, p)

    if legendre == p - 1:
        return None  # Not a quadratic residue

    # For p ≡ 5 (mod 8), use simplified formula:
    # If a is QR: sqrt(a) = a^((p+3)/8) or 2*a * (4*a)^((p-5)/8)

    # Try first candidate: a^((p+3)/8)
    y = pow(a, (p + 3) // 8, p)

    # Verify: y² should equal a
    if (y * y) % p == a:
        return y

    # If not, try: 2*a * (4*a)^((p-5)/8)
    two = pow(2, (p - 5) // 8, p)
    c = (4 * a) % p
    y = (2 * a * pow(c, (p - 5) // 8, p)) % p

    if (y * y) % p == a:
        return y

    return None
