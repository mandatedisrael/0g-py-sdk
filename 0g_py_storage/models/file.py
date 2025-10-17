"""
File operation models.

Ported from official TypeScript SDK:
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/node/types.d.ts
"""
from dataclasses import dataclass
from typing import List, Tuple

# Type aliases matching TypeScript
Hash = str  # export type Hash = string;
Base64 = str  # export type Base64 = string;
Segment = Base64  # export type Segment = Base64;
MerkleNode = Tuple[int, Hash]  # export type MerkleNode = [number, Hash];


@dataclass
class FileProof:
    """
    File merkle proof.

    TypeScript definition:
    export interface FileProof {
        lemma: Hash[];
        path: boolean[];
    }
    """
    lemma: List[Hash]
    path: List[bool]


@dataclass
class SegmentWithProof:
    """
    Segment with merkle proof.

    TypeScript definition:
    export interface SegmentWithProof {
        root: Hash;
        data: Base64;
        index: number;
        proof: FileProof;
        fileSize: number;
    }
    """
    root: Hash
    data: Base64
    index: int
    proof: FileProof
    fileSize: int


@dataclass
class Transaction:
    """
    Storage transaction.

    TypeScript definition:
    export interface Transaction {
        streamIds: BigInt[];
        data: Bytes;
        dataMerkleRoot: Hash;
        merkleNodes: MerkleNode[];
        startEntryIndex: number;
        size: number;
        seq: number;
    }
    """
    streamIds: List[int]
    data: bytes
    dataMerkleRoot: Hash
    merkleNodes: List[MerkleNode]
    startEntryIndex: int
    size: int
    seq: int


@dataclass
class FileInfo:
    """
    File information from storage node.

    TypeScript definition:
    export interface FileInfo {
        tx: Transaction;
        finalized: boolean;
        isCached: boolean;
        uploadedSegNum: number;
    }
    """
    tx: Transaction
    finalized: bool
    isCached: bool
    uploadedSegNum: int


@dataclass
class Metadata:
    """
    File metadata.

    TypeScript definition:
    export interface Metadata {
        root: Hash;
        fileSize: number;
        offsite: number;
    }
    """
    root: Hash
    fileSize: int
    offsite: int


@dataclass
class Value:
    """
    KV store value.

    TypeScript definition:
    export interface Value {
        version: number;
        data: Base64;
        size: number;
    }
    """
    version: int
    data: Base64
    size: int


@dataclass
class KeyValue:
    """
    KV store key-value pair.

    TypeScript definition:
    export interface KeyValue {
        version: number;
        data: Base64;
        size: number;
        key: Bytes;
    }
    """
    version: int
    data: Base64
    size: int
    key: bytes


@dataclass
class FlowProof:
    """
    Flow proof.

    TypeScript definition:
    export interface FlowProof {
        lemma: Hash[];
        path: boolean[];
    }
    """
    lemma: List[Hash]
    path: List[bool]
