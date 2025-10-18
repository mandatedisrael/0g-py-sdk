"""
Node selection logic for storage nodes.

Ported from official TypeScript SDK:
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/common/index.js
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/common/segment_tree.js

CRITICAL: Must EXACTLY match TypeScript SDK node selection algorithm.
"""
from typing import List, Tuple, Optional, Dict, Any


# ============================================================================
# SEGMENT TREE (Ported from segment_tree.js)
# ============================================================================

class SegmentTreeNode:
    """
    Node in segment tree for replica tracking.

    TS SDK segment_tree.js structure (implicit in code).
    """

    def __init__(self, num_shard: int):
        """
        Initialize tree node.

        Args:
            num_shard: Number of shards at this level
        """
        self.childs: Optional[List['SegmentTreeNode']] = None
        self.num_shard = num_shard
        self.replica = 0
        self.lazy_tags = 0


def pushdown(node: SegmentTreeNode) -> None:
    """
    Push lazy tags down to children.

    TS SDK segment_tree.js lines 5-22.

    Args:
        node: Tree node to push down
    """
    # TS line 6
    if node.childs is None:
        # TS line 7
        node.childs = []
        # TS line 8-15
        for i in range(2):
            node.childs.append(SegmentTreeNode(
                num_shard=node.num_shard << 1  # TS line 11
            ))

    # TS line 17-20
    for i in range(2):
        node.childs[i].replica += node.lazy_tags
        node.childs[i].lazy_tags += node.lazy_tags

    # TS line 21
    node.lazy_tags = 0


def insert(
    node: SegmentTreeNode,
    num_shard: int,
    shard_id: int,
    expected_replica: int
) -> bool:
    """
    Insert a shard if it contributes to the replica.

    TS SDK segment_tree.js lines 24-40.

    Args:
        node: Current tree node
        num_shard: Number of shards
        shard_id: Shard ID
        expected_replica: Expected replica count

    Returns:
        True if shard was inserted

    Raises:
        Exception: If tree structure is invalid
    """
    # TS line 25-27
    if node.replica >= expected_replica:
        return False

    # TS line 28-32
    if node.num_shard == num_shard:
        node.replica += 1
        node.lazy_tags += 1
        return True

    # TS line 33
    pushdown(node)

    # TS line 34-36
    if node.childs is None:
        raise Exception('node.childs is null')

    # TS line 37
    inserted = insert(
        node.childs[shard_id % 2],
        num_shard,
        shard_id >> 1,
        expected_replica
    )

    # TS line 38
    node.replica = min(node.childs[0].replica, node.childs[1].replica)

    # TS line 39
    return inserted


# ============================================================================
# NODE SELECTION (Ported from common/index.js)
# ============================================================================

def select_nodes(
    nodes: List[Dict[str, Any]],
    expected_replica: int
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Select nodes that meet replication requirements.

    TS SDK common/index.js lines 9-36.

    Args:
        nodes: List of sharded nodes with config
        expected_replica: Expected number of replicas

    Returns:
        Tuple of (selected_nodes, success)
    """
    # TS line 10-12
    if expected_replica == 0:
        return ([], False)

    # TS line 13-18
    # Sort nodes by numShard, then by shardId
    nodes.sort(key=lambda node: (
        node['config']['numShard'],
        node['config']['shardId']
    ))

    # TS line 19-24
    root = SegmentTreeNode(num_shard=1)
    root.replica = 0
    root.lazy_tags = 0

    # TS line 25
    selected_nodes = []

    # TS line 26
    for i in range(len(nodes)):
        # TS line 27
        node = nodes[i]

        # TS line 28-30
        if insert(
            root,
            node['config']['numShard'],
            node['config']['shardId'],
            expected_replica
        ):
            selected_nodes.append(node)

        # TS line 31-33
        if root.replica >= expected_replica:
            return (selected_nodes, True)

    # TS line 35
    return ([], False)


def check_replica(
    shard_configs: List[Dict[str, int]],
    expected_replica: int
) -> bool:
    """
    Check if shard configs can meet replica requirements.

    TS SDK common/index.js lines 37-52.

    Args:
        shard_configs: List of shard configurations
        expected_replica: Expected replica count

    Returns:
        True if replica requirement can be met
    """
    # TS line 38
    sharded_nodes = []

    # TS line 39-48
    for i in range(len(shard_configs)):
        sharded_nodes.append({
            'url': '',
            'config': {
                'numShard': shard_configs[i]['numShard'],
                'shardId': shard_configs[i]['shardId'],
            },
            'latency': 0,
            'since': 0,
        })

    # TS line 50
    _, ok = select_nodes(sharded_nodes, expected_replica)

    # TS line 51
    return ok


def is_valid_config(config: Dict[str, int]) -> bool:
    """
    Validate shard configuration.

    TS SDK node/utils.js lines 4-9.

    Args:
        config: Shard config with numShard and shardId

    Returns:
        True if config is valid
    """
    # TS line 5-8
    # NumShard should be larger than zero and be power of 2
    num_shard = config['numShard']
    shard_id = config['shardId']

    return (
        num_shard > 0 and
        (num_shard & (num_shard - 1)) == 0 and
        shard_id < num_shard
    )
