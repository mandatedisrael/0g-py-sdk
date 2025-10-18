"""
Transfer utilities.

Ported from official TypeScript SDK:
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/transfer/utils.js
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/utils.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import List, Dict, Any, Optional
import time

try:
    from ..core.storage_node import StorageNode
    from ..core.node_selector import is_valid_config
except ImportError:
    from core.storage_node import StorageNode
    from core.node_selector import is_valid_config


async def get_shard_configs(nodes: List[StorageNode]) -> Optional[List[Dict[str, Any]]]:
    """
    Get shard configurations from storage nodes.

    TS SDK transfer/utils.js lines 6-16.

    Args:
        nodes: List of storage nodes

    Returns:
        List of shard configs or None if any invalid
    """
    # TS line 7
    configs = []

    # TS line 8
    for c_node in nodes:
        # TS line 9
        c_config = c_node.get_shard_config()

        # TS line 10-12
        if not is_valid_config(c_config):
            return None

        # TS line 13
        configs.append(c_config)

    # TS line 15
    return configs


def calculate_price(submission: Dict[str, Any], price_per_sector: int) -> int:
    """
    Calculate storage price for submission.

    TS SDK transfer/utils.js lines 17-23.

    Args:
        submission: Submission structure
        price_per_sector: Price per sector

    Returns:
        Total price
    """
    # TS line 18
    sectors = 0

    # TS line 19-21
    for node in submission['nodes']:
        sectors += 1 << int(node['height'])

    # TS line 22
    return sectors * price_per_sector


def delay(seconds: float) -> None:
    """
    Delay execution.

    TS SDK utils.js line 22.

    Args:
        seconds: Seconds to delay
    """
    time.sleep(seconds)


def get_split_num(total: int, unit: int) -> int:
    """
    Calculate number of splits.

    TS SDK utils.js lines 38-40.

    Args:
        total: Total size
        unit: Unit size

    Returns:
        Number of splits
    """
    return (total - 1) // unit + 1


def segment_range(start_chunk_index: int, file_size: int) -> tuple:
    """
    Calculate segment range for file.

    TS SDK utils.js lines 49-58.

    Args:
        start_chunk_index: Starting chunk index
        file_size: File size in bytes

    Returns:
        Tuple of (start_segment_index, end_segment_index)
    """
    from ..config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 51
    total_chunks = get_split_num(file_size, DEFAULT_CHUNK_SIZE)

    # TS line 53
    start_segment_index = start_chunk_index // DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 55-56
    end_chunk_index = start_chunk_index + total_chunks - 1
    end_segment_index = end_chunk_index // DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 57
    return (start_segment_index, end_segment_index)
