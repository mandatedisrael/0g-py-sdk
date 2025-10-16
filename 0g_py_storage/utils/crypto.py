"""
Cryptographic utilities for merkle tree and hashing.

Ported from official TypeScript SDK which uses:
- @ethersproject/keccak256 for hashing
- @ethersproject/bytes for hex operations
"""
from typing import List
from Crypto.Hash import keccak


def keccak256_hash(data: bytes) -> str:
    """
    Compute Keccak256 hash of data.

    Returns hex string with 0x prefix (matching ethers.js behavior).
    """
    k = keccak.new(digest_bits=256)
    k.update(data)
    return '0x' + k.hexdigest()


def keccak256_hash_bytes(data: bytes) -> bytes:
    """
    Compute Keccak256 hash of data.

    Returns raw bytes (for internal use).
    """
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()


def hex_concat(hex_strings: List[str]) -> bytes:
    """
    Concatenate multiple hex strings into bytes.

    Matches @ethersproject/bytes hexConcat behavior.
    """
    result = b''
    for hex_str in hex_strings:
        result += hex_to_bytes(hex_str)
    return result


def keccak256_hash_combine(*hashes: str) -> str:
    """
    Combine multiple hashes by concatenating then hashing.

    Matches TS implementation:
    function keccak256Hash(...hashes) {
        return keccak256(hexConcat(hashes));
    }
    """
    combined = hex_concat(list(hashes))
    return keccak256_hash(combined)


def bytes_to_hex(data: bytes) -> str:
    """Convert bytes to hex string with 0x prefix."""
    return '0x' + data.hex()


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string to bytes."""
    if hex_str.startswith('0x'):
        hex_str = hex_str[2:]
    return bytes.fromhex(hex_str)
