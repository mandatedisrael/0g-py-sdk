"""
Test node selection logic.

Tests must match TypeScript SDK behavior exactly.
"""
import pytest
from core.node_selector import (
    select_nodes,
    check_replica,
    is_valid_config,
    SegmentTreeNode,
    pushdown,
    insert
)


class TestSegmentTree:
    """Test segment tree operations."""

    def test_tree_node_init(self):
        """Test tree node initialization."""
        node = SegmentTreeNode(num_shard=1)
        assert node.num_shard == 1
        assert node.replica == 0
        assert node.lazy_tags == 0
        assert node.childs is None

    def test_pushdown_creates_children(self):
        """Test pushdown creates children."""
        node = SegmentTreeNode(num_shard=1)
        pushdown(node)

        assert node.childs is not None
        assert len(node.childs) == 2
        assert node.childs[0].num_shard == 2
        assert node.childs[1].num_shard == 2

    def test_pushdown_propagates_tags(self):
        """Test pushdown propagates lazy tags."""
        node = SegmentTreeNode(num_shard=1)
        node.lazy_tags = 5

        pushdown(node)

        assert node.lazy_tags == 0
        assert node.childs[0].replica == 5
        assert node.childs[0].lazy_tags == 5
        assert node.childs[1].replica == 5
        assert node.childs[1].lazy_tags == 5

    def test_insert_single_shard(self):
        """Test inserting a single shard."""
        root = SegmentTreeNode(num_shard=1)

        inserted = insert(root, num_shard=1, shard_id=0, expected_replica=1)

        assert inserted is True
        assert root.replica == 1
        assert root.lazy_tags == 1

    def test_insert_stops_at_expected_replica(self):
        """Test insert stops when expected replica is reached."""
        root = SegmentTreeNode(num_shard=1)
        root.replica = 2

        inserted = insert(root, num_shard=1, shard_id=0, expected_replica=2)

        assert inserted is False
        assert root.replica == 2

    def test_insert_multiple_shards(self):
        """Test inserting multiple shards."""
        root = SegmentTreeNode(num_shard=1)

        # Insert first shard
        inserted1 = insert(root, num_shard=2, shard_id=0, expected_replica=2)
        assert inserted1 is True

        # Insert second shard
        inserted2 = insert(root, num_shard=2, shard_id=1, expected_replica=2)
        assert inserted2 is True

        # Both shards should contribute to replica
        assert root.replica >= 1


class TestIsValidConfig:
    """Test shard config validation."""

    def test_valid_config_single_shard(self):
        """Test valid single shard config."""
        config = {'numShard': 1, 'shardId': 0}
        assert is_valid_config(config) is True

    def test_valid_config_two_shards(self):
        """Test valid two shard config."""
        config1 = {'numShard': 2, 'shardId': 0}
        assert is_valid_config(config1) is True

        config2 = {'numShard': 2, 'shardId': 1}
        assert is_valid_config(config2) is True

    def test_valid_config_power_of_two(self):
        """Test valid configs with power of 2 shards."""
        for num_shard in [1, 2, 4, 8, 16, 32]:
            for shard_id in range(num_shard):
                config = {'numShard': num_shard, 'shardId': shard_id}
                assert is_valid_config(config) is True

    def test_invalid_config_zero_shards(self):
        """Test invalid config with zero shards."""
        config = {'numShard': 0, 'shardId': 0}
        assert is_valid_config(config) is False

    def test_invalid_config_not_power_of_two(self):
        """Test invalid config with non-power-of-2 shards."""
        config = {'numShard': 3, 'shardId': 0}
        assert is_valid_config(config) is False

        config = {'numShard': 5, 'shardId': 0}
        assert is_valid_config(config) is False

    def test_invalid_config_shard_id_out_of_range(self):
        """Test invalid config with shard ID out of range."""
        config = {'numShard': 2, 'shardId': 2}
        assert is_valid_config(config) is False

        config = {'numShard': 4, 'shardId': 4}
        assert is_valid_config(config) is False


class TestSelectNodes:
    """Test node selection algorithm."""

    def test_select_nodes_zero_replica(self):
        """Test selecting nodes with zero replica requirement."""
        nodes = [
            {'url': 'node1', 'config': {'numShard': 1, 'shardId': 0}, 'latency': 0, 'since': 0}
        ]

        selected, ok = select_nodes(nodes, expected_replica=0)

        assert ok is False
        assert len(selected) == 0

    def test_select_nodes_single_node_single_replica(self):
        """Test selecting single node for single replica."""
        nodes = [
            {'url': 'node1', 'config': {'numShard': 1, 'shardId': 0}, 'latency': 0, 'since': 0}
        ]

        selected, ok = select_nodes(nodes, expected_replica=1)

        assert ok is True
        assert len(selected) == 1
        assert selected[0]['url'] == 'node1'

    def test_select_nodes_two_shards_single_replica(self):
        """Test selecting from two shards for single replica."""
        nodes = [
            {'url': 'node1', 'config': {'numShard': 2, 'shardId': 0}, 'latency': 0, 'since': 0},
            {'url': 'node2', 'config': {'numShard': 2, 'shardId': 1}, 'latency': 0, 'since': 0}
        ]

        selected, ok = select_nodes(nodes, expected_replica=1)

        assert ok is True
        assert len(selected) == 2  # Need both shards for 1 replica

    def test_select_nodes_insufficient_nodes(self):
        """Test selecting when not enough nodes."""
        nodes = [
            {'url': 'node1', 'config': {'numShard': 2, 'shardId': 0}, 'latency': 0, 'since': 0}
        ]

        selected, ok = select_nodes(nodes, expected_replica=2)

        assert ok is False
        assert len(selected) == 0

    def test_select_nodes_sorting(self):
        """Test that nodes are sorted correctly."""
        nodes = [
            {'url': 'node3', 'config': {'numShard': 4, 'shardId': 2}, 'latency': 0, 'since': 0},
            {'url': 'node1', 'config': {'numShard': 2, 'shardId': 0}, 'latency': 0, 'since': 0},
            {'url': 'node2', 'config': {'numShard': 2, 'shardId': 1}, 'latency': 0, 'since': 0},
        ]

        selected, ok = select_nodes(nodes, expected_replica=1)

        # Nodes should be sorted by numShard, then shardId
        assert ok is True
        # First two nodes should be the ones with numShard=2
        assert selected[0]['config']['numShard'] == 2
        assert selected[1]['config']['numShard'] == 2

    def test_select_nodes_multiple_replicas(self):
        """Test selecting for multiple replicas."""
        nodes = [
            {'url': 'node1', 'config': {'numShard': 1, 'shardId': 0}, 'latency': 0, 'since': 0},
            {'url': 'node2', 'config': {'numShard': 1, 'shardId': 0}, 'latency': 0, 'since': 0},
            {'url': 'node3', 'config': {'numShard': 1, 'shardId': 0}, 'latency': 0, 'since': 0}
        ]

        selected, ok = select_nodes(nodes, expected_replica=2)

        assert ok is True
        assert len(selected) == 2


class TestCheckReplica:
    """Test replica checking."""

    def test_check_replica_single_shard(self):
        """Test checking single shard replica."""
        shard_configs = [
            {'numShard': 1, 'shardId': 0}
        ]

        ok = check_replica(shard_configs, expected_replica=1)
        assert ok is True

    def test_check_replica_two_shards(self):
        """Test checking two shard replica."""
        shard_configs = [
            {'numShard': 2, 'shardId': 0},
            {'numShard': 2, 'shardId': 1}
        ]

        ok = check_replica(shard_configs, expected_replica=1)
        assert ok is True

    def test_check_replica_insufficient(self):
        """Test checking with insufficient shards."""
        shard_configs = [
            {'numShard': 2, 'shardId': 0}
        ]

        ok = check_replica(shard_configs, expected_replica=2)
        assert ok is False

    def test_check_replica_multiple(self):
        """Test checking multiple replicas."""
        shard_configs = [
            {'numShard': 1, 'shardId': 0},
            {'numShard': 1, 'shardId': 0}
        ]

        ok = check_replica(shard_configs, expected_replica=2)
        assert ok is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
