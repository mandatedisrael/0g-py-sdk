#!/usr/bin/env python3
"""
Simple test runner for merkle tree implementation.
Run from this directory: python3 test_runner.py
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.merkle import MerkleTree, LeafNode, Proof, ProofErrors
from config import EMPTY_CHUNK_HASH, EMPTY_CHUNK, DEFAULT_CHUNK_SIZE
from utils.crypto import keccak256_hash

def test_imports():
    """Test that imports work."""
    print("✓ Imports successful")

def test_leaf_node():
    """Test LeafNode basic functionality."""
    # Create from hash
    node = LeafNode("0x123")
    assert node.hash == "0x123"

    # Create from content
    node2 = LeafNode.from_content(b"test")
    assert node2.hash.startswith("0x")

    # Create parent
    left = LeafNode.from_content(b"left")
    right = LeafNode.from_content(b"right")
    parent = LeafNode.from_left_and_right(left, right)
    assert parent.left is left
    assert parent.right is right
    assert left.is_left_side() is True
    assert right.is_left_side() is False

    print("✓ LeafNode tests passed")

def test_single_leaf():
    """Test tree with single leaf."""
    tree = MerkleTree()
    tree.add_leaf(b"hello world")
    tree.build()

    assert tree.root_hash() is not None
    assert tree.root is not None
    print(f"  Single leaf root: {tree.root_hash()}")
    print("✓ Single leaf test passed")

def test_two_leaves():
    """Test tree with two leaves."""
    tree = MerkleTree()
    tree.add_leaf(b"chunk1")
    tree.add_leaf(b"chunk2")
    tree.build()

    assert tree.root_hash() is not None
    assert tree.root.left is tree.leaves[0]
    assert tree.root.right is tree.leaves[1]
    print(f"  Two leaves root: {tree.root_hash()}")
    print("✓ Two leaves test passed")

def test_three_leaves():
    """Test tree with odd number of leaves."""
    tree = MerkleTree()
    tree.add_leaf(b"chunk1")
    tree.add_leaf(b"chunk2")
    tree.add_leaf(b"chunk3")
    tree.build()

    assert tree.root_hash() is not None
    print(f"  Three leaves root: {tree.root_hash()}")
    print("✓ Three leaves test passed")

def test_proof_generation():
    """Test proof generation and validation."""
    tree = MerkleTree()
    tree.add_leaf(b"chunk1")
    tree.add_leaf(b"chunk2")
    tree.build()

    root_hash = tree.root_hash()

    # Get proof for first leaf
    proof = tree.proof_at(0)
    assert proof.validate_format() is None
    assert proof.validate_root() is True

    # Validate complete proof
    error = proof.validate(root_hash, b"chunk1", 0, 2)
    assert error is None

    print("✓ Proof generation and validation passed")

def test_deterministic():
    """Test that same content produces same merkle root."""
    tree1 = MerkleTree()
    tree1.add_leaf(b"chunk1")
    tree1.add_leaf(b"chunk2")
    tree1.add_leaf(b"chunk3")
    tree1.build()

    tree2 = MerkleTree()
    tree2.add_leaf(b"chunk1")
    tree2.add_leaf(b"chunk2")
    tree2.add_leaf(b"chunk3")
    tree2.build()

    assert tree1.root_hash() == tree2.root_hash()
    print(f"  Deterministic root: {tree1.root_hash()}")
    print("✓ Deterministic hash test passed")

def test_empty_chunk_hash():
    """Test EMPTY_CHUNK_HASH constant."""
    assert len(EMPTY_CHUNK) == DEFAULT_CHUNK_SIZE
    expected = keccak256_hash(EMPTY_CHUNK)
    assert EMPTY_CHUNK_HASH == expected
    print(f"  Empty chunk hash: {EMPTY_CHUNK_HASH}")
    print("✓ Empty chunk hash test passed")

def test_many_leaves():
    """Test tree with many leaves."""
    tree = MerkleTree()
    for i in range(10):
        tree.add_leaf(f"chunk{i}".encode())
    tree.build()

    assert tree.root_hash() is not None
    assert len(tree.leaves) == 10
    print(f"  10 leaves root: {tree.root_hash()}")
    print("✓ Many leaves test passed")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running Merkle Tree Tests")
    print("="*60 + "\n")

    try:
        test_imports()
        test_leaf_node()
        test_single_leaf()
        test_two_leaves()
        test_three_leaves()
        test_proof_generation()
        test_deterministic()
        test_empty_chunk_hash()
        test_many_leaves()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
