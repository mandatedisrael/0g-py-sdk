"""
Merkle tree implementation for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/file/MerkleTree.js

CRITICAL: This must EXACTLY match the 0G protocol implementation.
"""
from typing import Optional, List
from enum import Enum
import math

try:
    from ..utils.crypto import keccak256_hash, keccak256_hash_combine
except ImportError:
    from utils.crypto import keccak256_hash, keccak256_hash_combine


class LeafNode:
    """
    Represents a node in the merkle tree.

    Ported from TS SDK LeafNode class (lines 6-29).
    """

    def __init__(self, hash: str):
        """
        Initialize a leaf node with a hash.

        Args:
            hash: Hex string with 0x prefix
        """
        self.hash = hash  # hex string
        self.parent: Optional[LeafNode] = None
        self.left: Optional[LeafNode] = None
        self.right: Optional[LeafNode] = None

    @staticmethod
    def from_content(content: bytes) -> 'LeafNode':
        """
        Create a leaf node from content.

        TS SDK line 15-16:
        static fromContent(content) {
            return new LeafNode(keccak256(content));
        }
        """
        return LeafNode(keccak256_hash(content))

    @staticmethod
    def from_left_and_right(left: 'LeafNode', right: 'LeafNode') -> 'LeafNode':
        """
        Create parent node from left and right children.

        TS SDK lines 18-24:
        static fromLeftAndRight(left, right) {
            const node = new LeafNode(keccak256Hash(left.hash, right.hash));
            node.left = left;
            node.right = right;
            left.parent = node;
            right.parent = node;
            return node;
        }
        """
        node = LeafNode(keccak256_hash_combine(left.hash, right.hash))
        node.left = left
        node.right = right
        left.parent = node
        right.parent = node
        return node

    def is_left_side(self) -> bool:
        """
        Check if this node is the left child of its parent.

        TS SDK lines 26-27:
        isLeftSide() {
            return this.parent !== null && this.parent.left === this;
        }
        """
        return self.parent is not None and self.parent.left is self


class ProofErrors(Enum):
    """
    Proof validation error types.

    TS SDK lines 31-38.
    """
    WRONG_FORMAT = "invalid merkle proof format"
    ROOT_MISMATCH = "merkle proof root mismatch"
    CONTENT_MISMATCH = "merkle proof content mismatch"
    POSITION_MISMATCH = "merkle proof position mismatch"
    VALIDATION_FAILURE = "failed to validate merkle proof"


class Proof:
    """
    Merkle proof for verifying data integrity.

    TS SDK lines 40-121.

    Lemma structure (lines 41-44):
    1. Target content hash (leaf node)
    2. Hashes from bottom to top of sibling nodes
    3. Root hash
    """

    def __init__(self, lemma: Optional[List[str]] = None, path: Optional[List[bool]] = None):
        """
        Initialize a proof.

        TS SDK lines 49-51:
        constructor(lemma = [], path = []) {
            this.lemma = lemma;
            this.path = path;
        }
        """
        self.lemma = lemma if lemma is not None else []
        self.path = path if path is not None else []

    def validate_format(self) -> Optional[ProofErrors]:
        """
        Validate proof format.

        TS SDK lines 53-64:
        validateFormat() {
            const numSiblings = this.path.length;
            if (numSiblings === 0) {
                if (this.lemma.length !== 1) {
                    return ProofErrors.WRONG_FORMAT;
                }
                return null;
            }
            if (numSiblings + 2 !== this.lemma.length) {
                return ProofErrors.WRONG_FORMAT;
            }
            return null;
        }
        """
        num_siblings = len(self.path)

        if num_siblings == 0:
            if len(self.lemma) != 1:
                return ProofErrors.WRONG_FORMAT
            return None

        if num_siblings + 2 != len(self.lemma):
            return ProofErrors.WRONG_FORMAT

        return None

    def validate(self, root_hash: str, content: bytes, position: int, num_leaf_nodes: int) -> Optional[ProofErrors]:
        """
        Validate proof against content.

        TS SDK lines 66-68:
        validate(rootHash, content, position, numLeafNodes) {
            const contentHash = keccak256(content);
            return this.validateHash(rootHash, contentHash, position, numLeafNodes);
        }
        """
        content_hash = keccak256_hash(content)
        return self.validate_hash(root_hash, content_hash, position, num_leaf_nodes)

    def validate_hash(self, root_hash: str, content_hash: str, position: int, num_leaf_nodes: int) -> Optional[ProofErrors]:
        """
        Validate proof with content hash.

        TS SDK lines 70-89:
        validateHash(rootHash, contentHash, position, numLeafNodes) {
            const formatError = this.validateFormat();
            if (formatError !== null) {
                return formatError;
            }
            if (contentHash !== this.lemma[0]) {
                return ProofErrors.CONTENT_MISMATCH;
            }
            if (this.lemma.length > 1 &&
                rootHash !== this.lemma[this.lemma.length - 1]) {
                return ProofErrors.ROOT_MISMATCH;
            }
            const proofPosition = this.calculateProofPosition(numLeafNodes);
            if (proofPosition !== position) {
                return ProofErrors.POSITION_MISMATCH;
            }
            if (!this.validateRoot()) {
                return ProofErrors.VALIDATION_FAILURE;
            }
            return null;
        }
        """
        format_error = self.validate_format()
        if format_error is not None:
            return format_error

        if content_hash != self.lemma[0]:
            return ProofErrors.CONTENT_MISMATCH

        if len(self.lemma) > 1 and root_hash != self.lemma[-1]:
            return ProofErrors.ROOT_MISMATCH

        proof_position = self.calculate_proof_position(num_leaf_nodes)
        if proof_position != position:
            return ProofErrors.POSITION_MISMATCH

        if not self.validate_root():
            return ProofErrors.VALIDATION_FAILURE

        return None

    def validate_root(self) -> bool:
        """
        Validate that proof path reconstructs to root.

        TS SDK lines 91-102:
        validateRoot() {
            let hash = this.lemma[0];
            for (let i = 0; i < this.path.length; i++) {
                const isLeft = this.path[i];
                if (isLeft) {
                    hash = keccak256Hash(hash, this.lemma[i + 1]);
                }
                else {
                    hash = keccak256Hash(this.lemma[i + 1], hash);
                }
            }
            return hash === this.lemma[this.lemma.length - 1];
        }
        """
        hash_val = self.lemma[0]

        for i in range(len(self.path)):
            is_left = self.path[i]
            if is_left:
                hash_val = keccak256_hash_combine(hash_val, self.lemma[i + 1])
            else:
                hash_val = keccak256_hash_combine(self.lemma[i + 1], hash_val)

        return hash_val == self.lemma[-1]

    def calculate_proof_position(self, num_leaf_nodes: int) -> int:
        """
        Calculate position from proof path.

        TS SDK lines 105-119:
        calculateProofPosition(numLeafNodes) {
            let position = 0;
            for (let i = this.path.length - 1; i >= 0; i--) {
                const leftSideDepth = Math.ceil(Math.log2(numLeafNodes));
                const leftSideLeafNodes = Math.pow(2, leftSideDepth) / 2;
                const isLeft = this.path[i];
                if (isLeft) {
                    numLeafNodes = leftSideLeafNodes;
                }
                else {
                    position += leftSideLeafNodes;
                    numLeafNodes -= leftSideLeafNodes;
                }
            }
            return position;
        }
        """
        position = 0

        for i in range(len(self.path) - 1, -1, -1):
            left_side_depth = math.ceil(math.log2(num_leaf_nodes))
            left_side_leaf_nodes = int(math.pow(2, left_side_depth) / 2)
            is_left = self.path[i]

            if is_left:
                num_leaf_nodes = left_side_leaf_nodes
            else:
                position += left_side_leaf_nodes
                num_leaf_nodes -= left_side_leaf_nodes

        return position


class MerkleTree:
    """
    Main merkle tree implementation.

    TS SDK lines 123-201.
    """

    def __init__(self, root: Optional[LeafNode] = None, leaves: Optional[List[LeafNode]] = None):
        """
        Initialize merkle tree.

        TS SDK lines 126-128:
        constructor(root = null, leaves = []) {
            this.root = root;
            this.leaves = leaves;
        }
        """
        self.root = root
        self.leaves = leaves if leaves is not None else []

    def root_hash(self) -> Optional[str]:
        """
        Get root hash.

        TS SDK lines 130-131:
        rootHash() {
            return this.root ? this.root.hash : null;
        }
        """
        return self.root.hash if self.root else None

    def proof_at(self, i: int) -> Proof:
        """
        Generate proof for leaf at index i.

        TS SDK lines 133-157:
        proofAt(i) {
            if (i < 0 || i >= this.leaves.length) {
                throw new Error('Index out of range');
            }
            if (this.leaves.length === 1) {
                return new Proof([this.rootHash()], []);
            }
            const proof = new Proof();
            // append the target leaf node hash
            proof.lemma.push(this.leaves[i].hash);
            let current = this.leaves[i];
            while (current !== this.root) {
                if (current.isLeftSide()) {
                    proof.lemma.push(current.parent?.right?.hash);
                    proof.path.push(true);
                }
                else {
                    proof.lemma.push(current.parent?.left?.hash);
                    proof.path.push(false);
                }
                current = current.parent;
            }
            // append the root node hash
            proof.lemma.push(this.rootHash());
            return proof;
        }
        """
        if i < 0 or i >= len(self.leaves):
            raise IndexError('Index out of range')

        if len(self.leaves) == 1:
            return Proof([self.root_hash()], [])

        proof = Proof()
        # Append the target leaf node hash
        proof.lemma.append(self.leaves[i].hash)

        current = self.leaves[i]
        while current != self.root:
            if current.is_left_side():
                proof.lemma.append(current.parent.right.hash)
                proof.path.append(True)
            else:
                proof.lemma.append(current.parent.left.hash)
                proof.path.append(False)
            current = current.parent

        # Append the root node hash
        proof.lemma.append(self.root_hash())
        return proof

    def add_leaf(self, leaf_content: bytes) -> None:
        """
        Add leaf from content.

        TS SDK lines 159-160:
        addLeaf(leafContent) {
            this.leaves.push(LeafNode.fromContent(leafContent));
        }
        """
        self.leaves.append(LeafNode.from_content(leaf_content))

    def add_leaf_by_hash(self, leaf_hash: str) -> None:
        """
        Add leaf from hash.

        TS SDK lines 162-163:
        addLeafByHash(leafHash) {
            this.leaves.push(new LeafNode(leafHash));
        }
        """
        self.leaves.append(LeafNode(leaf_hash))

    def build(self) -> Optional['MerkleTree']:
        """
        Build merkle tree from leaves.

        CRITICAL: Must match TS SDK exactly.

        TS SDK lines 166-200:
        build() {
            const numLeafNodes = this.leaves.length;
            if (numLeafNodes === 0) {
                return null;
            }
            let queue = [];
            for (let i = 0; i < numLeafNodes; i += 2) {
                // last single leaf node
                if (i === numLeafNodes - 1) {
                    queue.push(this.leaves[i]);
                    continue;
                }
                const node = LeafNode.fromLeftAndRight(this.leaves[i], this.leaves[i + 1]);
                queue.push(node);
            }
            while (true) {
                const numNodes = queue.length;
                if (numNodes <= 1) {
                    break;
                }
                for (let i = 0; i < Math.floor(numNodes / 2); i++) {
                    const left = queue[0];
                    const right = queue[1];
                    queue.splice(0, 2); // remove first two elements
                    queue.push(LeafNode.fromLeftAndRight(left, right));
                }
                if (numNodes % 2 === 1) {
                    const first = queue[0];
                    queue.splice(0, 1); // remove first element
                    queue.push(first);
                }
            }
            this.root = queue[0];
            return this;
        }
        """
        num_leaf_nodes = len(self.leaves)

        if num_leaf_nodes == 0:
            return None

        queue = []

        # Pair up leaves
        for i in range(0, num_leaf_nodes, 2):
            # Last single leaf node
            if i == num_leaf_nodes - 1:
                queue.append(self.leaves[i])
                continue

            # Pair left and right
            node = LeafNode.from_left_and_right(self.leaves[i], self.leaves[i + 1])
            queue.append(node)

        # Build upper levels
        while True:
            num_nodes = len(queue)

            if num_nodes <= 1:
                break

            # Process pairs
            for i in range(num_nodes // 2):
                left = queue[0]
                right = queue[1]
                queue = queue[2:]  # Remove first two elements
                queue.append(LeafNode.from_left_and_right(left, right))

            # Handle odd node
            if num_nodes % 2 == 1:
                first = queue[0]
                queue = queue[1:]  # Remove first element
                queue.append(first)

        self.root = queue[0]
        return self
