"""
Test merkle tree implementation against known values.

Tests ported functionality from TypeScript SDK.
"""
import pytest
from core.merkle import MerkleTree, LeafNode, Proof, ProofErrors
from config import EMPTY_CHUNK_HASH
from utils.crypto import keccak256_hash


class TestLeafNode:
    """Test LeafNode class."""

    def test_create_from_hash(self):
        """Test creating leaf node from hash."""
        hash_val = "0x1234567890abcdef"
        node = LeafNode(hash_val)
        assert node.hash == hash_val
        assert node.parent is None
        assert node.left is None
        assert node.right is None

    def test_from_content(self):
        """Test creating leaf node from content."""
        content = b"hello world"
        node = LeafNode.from_content(content)
        expected_hash = keccak256_hash(content)
        assert node.hash == expected_hash

    def test_from_left_and_right(self):
        """Test creating parent node from children."""
        left = LeafNode.from_content(b"left")
        right = LeafNode.from_content(b"right")

        parent = LeafNode.from_left_and_right(left, right)

        # Check parent-child relationships
        assert parent.left is left
        assert parent.right is right
        assert left.parent is parent
        assert right.parent is parent

    def test_is_left_side(self):
        """Test checking if node is left child."""
        left = LeafNode.from_content(b"left")
        right = LeafNode.from_content(b"right")
        parent = LeafNode.from_left_and_right(left, right)

        assert left.is_left_side() is True
        assert right.is_left_side() is False
        assert parent.is_left_side() is False  # No parent


class TestProof:
    """Test Proof class."""

    def test_init_empty(self):
        """Test creating empty proof."""
        proof = Proof()
        assert proof.lemma == []
        assert proof.path == []

    def test_init_with_values(self):
        """Test creating proof with values."""
        lemma = ["0xabc", "0xdef"]
        path = [True, False]
        proof = Proof(lemma, path)
        assert proof.lemma == lemma
        assert proof.path == path

    def test_validate_format_single_leaf(self):
        """Test format validation for single leaf proof."""
        proof = Proof(["0xroot"], [])
        assert proof.validate_format() is None

    def test_validate_format_single_leaf_invalid(self):
        """Test format validation fails for invalid single leaf."""
        proof = Proof(["0xroot", "0xextra"], [])
        assert proof.validate_format() == ProofErrors.WRONG_FORMAT

    def test_validate_format_multi_leaf(self):
        """Test format validation for multi-leaf proof."""
        # For 1 sibling: lemma must have 3 elements (target + sibling + root)
        proof = Proof(["0xtarget", "0xsibling", "0xroot"], [True])
        assert proof.validate_format() is None

    def test_validate_format_multi_leaf_invalid(self):
        """Test format validation fails for invalid multi-leaf."""
        # Wrong number of lemma entries
        proof = Proof(["0xtarget", "0xsibling"], [True])
        assert proof.validate_format() == ProofErrors.WRONG_FORMAT

    def test_validate_root_single_path(self):
        """Test root validation with simple proof."""
        # Create a simple tree with 2 leaves
        tree = MerkleTree()
        tree.add_leaf(b"chunk1")
        tree.add_leaf(b"chunk2")
        tree.build()

        # Get proof for first leaf
        proof = tree.proof_at(0)

        # Validate format
        assert proof.validate_format() is None

        # Validate root reconstruction
        assert proof.validate_root() is True


class TestMerkleTree:
    """Test MerkleTree class."""

    def test_empty_tree(self):
        """Test empty tree."""
        tree = MerkleTree()
        result = tree.build()
        assert result is None
        assert tree.root_hash() is None

    def test_single_leaf(self):
        """Test tree with single leaf."""
        tree = MerkleTree()
        tree.add_leaf(b"hello world")
        tree.build()

        assert tree.root_hash() is not None
        assert tree.root is not None
        assert len(tree.leaves) == 1

    def test_two_leaves(self):
        """Test tree with two leaves."""
        tree = MerkleTree()
        tree.add_leaf(b"chunk1")
        tree.add_leaf(b"chunk2")
        tree.build()

        assert tree.root_hash() is not None
        assert len(tree.leaves) == 2

        # Root should be parent of both leaves
        assert tree.root.left is tree.leaves[0]
        assert tree.root.right is tree.leaves[1]

    def test_three_leaves(self):
        """Test tree with odd number of leaves."""
        tree = MerkleTree()
        tree.add_leaf(b"chunk1")
        tree.add_leaf(b"chunk2")
        tree.add_leaf(b"chunk3")
        tree.build()

        assert tree.root_hash() is not None
        assert len(tree.leaves) == 3

    def test_four_leaves(self):
        """Test tree with power of 2 leaves."""
        tree = MerkleTree()
        for i in range(4):
            tree.add_leaf(f"chunk{i}".encode())
        tree.build()

        assert tree.root_hash() is not None
        assert len(tree.leaves) == 4

    def test_many_leaves(self):
        """Test tree with many leaves."""
        tree = MerkleTree()
        for i in range(100):
            tree.add_leaf(f"chunk{i}".encode())
        tree.build()

        assert tree.root_hash() is not None
        assert len(tree.leaves) == 100

    def test_add_leaf_by_hash(self):
        """Test adding leaf by hash."""
        tree = MerkleTree()
        hash_val = keccak256_hash(b"test")
        tree.add_leaf_by_hash(hash_val)
        tree.build()

        assert tree.root_hash() == hash_val

    def test_proof_generation_single_leaf(self):
        """Test proof generation for single leaf."""
        tree = MerkleTree()
        tree.add_leaf(b"only")
        tree.build()

        proof = tree.proof_at(0)
        assert len(proof.lemma) == 1
        assert len(proof.path) == 0
        assert proof.lemma[0] == tree.root_hash()

    def test_proof_generation_two_leaves(self):
        """Test proof generation for two leaves."""
        tree = MerkleTree()
        tree.add_leaf(b"left")
        tree.add_leaf(b"right")
        tree.build()

        # Proof for left leaf
        proof_left = tree.proof_at(0)
        assert len(proof_left.lemma) == 3  # target + sibling + root
        assert len(proof_left.path) == 1
        assert proof_left.path[0] is True  # Left side

        # Proof for right leaf
        proof_right = tree.proof_at(1)
        assert len(proof_right.lemma) == 3
        assert len(proof_right.path) == 1
        assert proof_right.path[0] is False  # Right side

    def test_proof_generation_index_error(self):
        """Test proof generation with invalid index."""
        tree = MerkleTree()
        tree.add_leaf(b"only")
        tree.build()

        with pytest.raises(IndexError):
            tree.proof_at(1)

        with pytest.raises(IndexError):
            tree.proof_at(-1)

    def test_proof_validation(self):
        """Test complete proof validation."""
        tree = MerkleTree()
        content = b"test data"
        tree.add_leaf(content)
        tree.add_leaf(b"other data")
        tree.build()

        root_hash = tree.root_hash()
        proof = tree.proof_at(0)

        # Validate proof
        error = proof.validate(root_hash, content, 0, 2)
        assert error is None

    def test_proof_validation_wrong_content(self):
        """Test proof validation with wrong content."""
        tree = MerkleTree()
        tree.add_leaf(b"correct")
        tree.add_leaf(b"other")
        tree.build()

        root_hash = tree.root_hash()
        proof = tree.proof_at(0)

        # Try to validate with wrong content
        error = proof.validate(root_hash, b"wrong", 0, 2)
        assert error == ProofErrors.CONTENT_MISMATCH

    def test_proof_validation_wrong_root(self):
        """Test proof validation with wrong root."""
        tree = MerkleTree()
        tree.add_leaf(b"data")
        tree.add_leaf(b"other")
        tree.build()

        proof = tree.proof_at(0)

        # Try to validate with wrong root
        error = proof.validate("0xwrongroot", b"data", 0, 2)
        assert error == ProofErrors.ROOT_MISMATCH

    def test_deterministic_hashes(self):
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

    def test_empty_chunk_hash_constant(self):
        """Test EMPTY_CHUNK_HASH constant."""
        from config import EMPTY_CHUNK, DEFAULT_CHUNK_SIZE

        # Verify empty chunk is correct size
        assert len(EMPTY_CHUNK) == DEFAULT_CHUNK_SIZE

        # Verify hash matches
        expected = keccak256_hash(EMPTY_CHUNK)
        assert EMPTY_CHUNK_HASH == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
