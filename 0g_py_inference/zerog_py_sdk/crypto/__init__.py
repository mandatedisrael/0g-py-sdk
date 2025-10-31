"""
0G Protocol Cryptographic Primitives

Pure Python implementation of Baby JubJub + Pedersen + EdDSA cryptography
for the 0G Compute Network SDK.

This module eliminates the Node.js dependency by providing native Python
implementations of all cryptographic operations required for request
authentication and validation.

Components:
- field.py: Modular arithmetic in F_r (BN256 scalar field)
- babyjub.py: Baby JubJub twisted Edwards curve operations
- pedersen.py: Pedersen hash function
- eddsa.py: EdDSA signature scheme

Usage:
    from zerog_py_sdk.crypto import (
        gen_key_pair,
        sign_pedersen,
        pack_signature,
        pedersen_hash,
        initialize_pedersen_bases
    )

    # Generate key pair
    keys = gen_key_pair()
    privkey = keys['packedPrivkey']

    # Sign a message
    message = b'Hello, 0G!'
    signature = sign_pedersen(privkey, message)
    packed = pack_signature(signature)
"""

# Import main functions for public API
from .eddsa import EdDSA
from .pedersen import PedersenHash, initialize_pedersen_bases
from .babyjub import BabyJubJub
from .field import Fr

# Convenience functions that match TypeScript SDK API
def gen_key_pair():
    """Generate a random Baby JubJub key pair."""
    return EdDSA.gen_key_pair()


def prv2pub(privkey):
    """Derive public key from private key."""
    return EdDSA.prv2pub(privkey)


def sign_pedersen(privkey, message):
    """Sign a message using EdDSA with Pedersen hash."""
    return EdDSA.sign_pedersen(privkey, message)


def pack_signature(signature):
    """Pack EdDSA signature to 64 bytes."""
    return EdDSA.pack_signature(signature)


def verify_signature(pubkey, message, signature):
    """Verify an EdDSA signature."""
    return EdDSA.verify_signature(pubkey, message, signature)


def pedersen_hash(data):
    """Compute Pedersen hash of data."""
    return PedersenHash.hash(data)


__all__ = [
    'gen_key_pair',
    'prv2pub',
    'sign_pedersen',
    'pack_signature',
    'verify_signature',
    'pedersen_hash',
    'initialize_pedersen_bases',
    'EdDSA',
    'PedersenHash',
    'BabyJubJub',
    'Fr',
]

__version__ = '1.0.0'
