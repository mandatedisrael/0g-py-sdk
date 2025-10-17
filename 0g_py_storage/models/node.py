"""
Node and network models.

Ported from official TypeScript SDK:
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/common/types.d.ts
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/node/types.d.ts
0g_py_inference/node_modules/@0glabs/0g-ts-sdk/lib.commonjs/indexer/types.d.ts
"""
from dataclasses import dataclass
from typing import List


@dataclass
class ShardConfig:
    """
    Shard configuration.

    TypeScript definition:
    export interface ShardConfig {
        shardId: number;
        numShard: number;
    }
    """
    shardId: int
    numShard: int


@dataclass
class ShardedNode:
    """
    Sharded storage node.

    TypeScript definition:
    export interface ShardedNode {
        url: string;
        config: ShardConfig;
        latency: number;
        since: number;
    }
    """
    url: str
    config: ShardConfig
    latency: int
    since: int


@dataclass
class NetworkProtocolVersion:
    """
    Network protocol version.

    TypeScript definition:
    interface NetworkProtocolVersion {
        major: number;
        minor: number;
        build: number;
    }
    """
    major: int
    minor: int
    build: int


@dataclass
class NetworkIdentity:
    """
    Network identity information.

    TypeScript definition:
    interface NetworkIdentity {
        chainId: number;
        flowAddress: string;
        p2pProtocolVersion: NetworkProtocolVersion;
    }
    """
    chainId: int
    flowAddress: str
    p2pProtocolVersion: NetworkProtocolVersion


@dataclass
class Status:
    """
    Storage node status.

    TypeScript definition:
    export interface Status {
        connectedPeers: number;
        logSyncHeight: number;
        logSyncBlock: Hash;
        nextTxSeq: number;
        networkIdentity: NetworkIdentity;
    }
    """
    connectedPeers: int
    logSyncHeight: int
    logSyncBlock: str  # Hash
    nextTxSeq: int
    networkIdentity: NetworkIdentity


@dataclass
class IpLocation:
    """
    IP location information.

    TypeScript definition:
    export interface IpLocation {
        city: number;
        region: string;
        country: string;
        location: string;
        timezone: string;
    }
    """
    city: int
    region: str
    country: str
    location: str
    timezone: str


@dataclass
class ShardedNodes:
    """
    Collection of sharded nodes.

    TypeScript definition:
    export interface ShardedNodes {
        trusted: ShardedNode[];
        discovered: ShardedNode[];
    }
    """
    trusted: List[ShardedNode]
    discovered: List[ShardedNode]
