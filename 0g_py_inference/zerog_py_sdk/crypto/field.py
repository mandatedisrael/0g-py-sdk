"""
Field arithmetic for Baby JubJub cryptography.

Implements modular arithmetic operations in F_r, the BN256 scalar field.
All operations work modulo the field prime p = 2^256 - 2^32 - 977.

Reference: ERC-2494 Baby JubJub specification
"""

import secrets
from typing import Tuple


class Fr:
    """
    Represents the scalar field F_r of the BN256 curve.

    This is the field in which Baby JubJub operates. All arithmetic
    operations are done modulo the field prime p.
    """

    # Field prime (BN256 scalar field) - ERC-2494 specification
    p = 21888242871839275222246405745257275088548364400416034343698204186575808495617

    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two field elements: (a + b) mod p."""
        return (a + b) % Fr.p

    @staticmethod
    def sub(a: int, b: int) -> int:
        """Subtract two field elements: (a - b) mod p."""
        return (a - b) % Fr.p

    @staticmethod
    def mul(a: int, b: int) -> int:
        """Multiply two field elements: (a * b) mod p."""
        return (a * b) % Fr.p

    @staticmethod
    def neg(a: int) -> int:
        """Negate a field element: (-a) mod p."""
        return (-a) % Fr.p

    @staticmethod
    def inv(a: int) -> int:
        """
        Compute modular inverse of a field element.

        Uses Fermat's Little Theorem: a^(p-1) ≡ 1 (mod p)
        Therefore: a^(-1) ≡ a^(p-2) (mod p)

        Args:
            a: Field element to invert

        Returns:
            Multiplicative inverse of a modulo p

        Raises:
            ValueError: If a is 0 (not invertible)
        """
        if a == 0:
            raise ValueError("Cannot invert zero element")
        return pow(a, Fr.p - 2, Fr.p)

    @staticmethod
    def div(a: int, b: int) -> int:
        """
        Divide two field elements: (a / b) mod p.

        Equivalent to (a * b^(-1)) mod p.
        """
        return Fr.mul(a, Fr.inv(b))

    @staticmethod
    def random() -> int:
        """
        Generate random field element using cryptographically secure random.

        Returns:
            Random integer in range [0, p)
        """
        return secrets.randbelow(Fr.p)

    @staticmethod
    def is_zero(a: int) -> bool:
        """Check if field element is zero."""
        return a % Fr.p == 0

    @staticmethod
    def is_valid(a: int) -> bool:
        """Check if integer is a valid field element (0 <= a < p)."""
        return 0 <= a < Fr.p
