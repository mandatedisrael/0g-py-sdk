"""
File downloader for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/transfer/Downloader.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import List, Dict, Any, Optional, Tuple
import base64
import os

try:
    from ..core.storage_node import StorageNode
    from ..config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS
    from ..utils.transfer import get_shard_configs, get_split_num
except ImportError:
    from core.storage_node import StorageNode
    from config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS
    from utils.transfer import get_shard_configs, get_split_num


class Downloader:
    """
    File downloader for 0G Storage.

    Ported from Downloader.js (lines 1-113).

    Handles downloading files from storage nodes with proof verification.
    """

    def __init__(self, nodes: List[StorageNode]):
        """
        Initialize downloader.

        TS SDK lines 15-20.

        Args:
            nodes: List of storage node clients
        """
        # TS line 16
        self.nodes = nodes

        # TS line 17-19
        self.shard_configs = []
        self.start_segment_index = 0
        self.end_segment_index = 0

    def download_file(
        self,
        root: str,
        file_path: str,
        proof: bool = False
    ) -> Optional[Exception]:
        """
        Download file from storage network.

        TS SDK lines 21-39.

        Args:
            root: File root hash
            file_path: Output file path
            proof: Whether to download with proof verification

        Returns:
            Error if download failed, None otherwise
        """
        # TS line 22-25
        info, err = self.query_file(root)
        if err is not None or info is None:
            return Exception(str(err) if err else "Failed to query file")

        # TS line 26-28
        if not info['finalized']:
            return Exception('File not finalized')

        # TS line 29-31 - Check if file path is valid
        if self.check_exist(file_path):
            return Exception('Wrong path, provide a file path which does not exist.')

        # TS line 32-36
        shard_configs = get_shard_configs(self.nodes)
        if shard_configs is None:
            return Exception('Failed to get shard configs')

        self.shard_configs = shard_configs

        # TS line 37
        err = self.download_file_helper(file_path, info, proof)

        # TS line 38
        return err

    def query_file(self, root: str) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """
        Query file information from storage nodes.

        TS SDK lines 40-52.

        Args:
            root: File root hash

        Returns:
            Tuple of (file_info, error)
        """
        # TS line 41
        file_info = None

        # TS line 42
        for node in self.nodes:
            try:
                # TS line 43
                curr_info = node.get_file_info(root, True)

                # TS line 44-46
                if curr_info is None:
                    # If a node doesn't have the file, continue to next node
                    continue

                # TS line 47-49
                # Prefer finalized file info
                if curr_info.get('finalized', False):
                    file_info = curr_info
                    break  # Found finalized file, done

                # If not finalized but we don't have any info yet, keep it as fallback
                elif file_info is None:
                    file_info = curr_info

            except Exception as e:
                # Node query failed, try next node
                continue

        # TS line 51
        if file_info is None:
            return (None, Exception(f'File not found on any storage node'))

        return (file_info, None)

    def download_task(
        self,
        info: Dict[str, Any],
        segment_offset: int,
        task_ind: int,
        num_chunks: int,
        proof: bool
    ) -> Tuple[bytes, Optional[Exception]]:
        """
        Download a single segment.

        TS SDK lines 54-88.

        TODO: add proof check

        Args:
            info: File information
            segment_offset: Segment offset
            task_ind: Task index
            num_chunks: Total number of chunks
            proof: Whether to verify proof

        Returns:
            Tuple of (segment_data, error)
        """
        # TS line 55
        segment_index = segment_offset + task_ind

        # TS line 56-60
        start_index = segment_index * DEFAULT_SEGMENT_MAX_CHUNKS
        end_index = start_index + DEFAULT_SEGMENT_MAX_CHUNKS
        if end_index > num_chunks:
            end_index = num_chunks

        # TS line 61
        segment = None

        # TS line 62
        for i in range(len(self.shard_configs)):
            # TS line 63
            node_index = (task_ind + i) % len(self.shard_configs)

            # TS line 64-68
            if ((self.start_segment_index + segment_index) %
                self.shard_configs[node_index]['numShard'] !=
                self.shard_configs[node_index]['shardId']):
                continue

            # TS line 70
            segment = self.nodes[node_index].download_segment_by_tx_seq(
                info['tx']['seq'],
                start_index,
                end_index
            )

            # TS line 71-73
            if segment is None:
                continue

            # TS line 74
            seg_array = base64.b64decode(segment)

            # TS line 75-81
            if self.start_segment_index + segment_index == self.end_segment_index:
                last_chunk_size = info['tx']['size'] % DEFAULT_CHUNK_SIZE
                if last_chunk_size > 0:
                    paddings = DEFAULT_CHUNK_SIZE - last_chunk_size
                    seg_array = seg_array[0:len(seg_array) - paddings]

            # TS line 82
            return (seg_array, None)

        # TS line 84-87
        return (
            bytes(),
            Exception(f'No storage node holds segment with index {segment_index}')
        )

    def download_file_helper(
        self,
        file_path: str,
        info: Dict[str, Any],
        proof: bool
    ) -> Optional[Exception]:
        """
        Helper to download file segments.

        TS SDK lines 89-110.

        Args:
            file_path: Output file path
            info: File information
            proof: Whether to verify proof

        Returns:
            Error if download failed, None otherwise
        """
        # TS line 90-93
        shard_configs = get_shard_configs(self.nodes)
        if shard_configs is None:
            return Exception('Failed to get shard configs')

        # TS line 94
        segment_offset = 0

        # TS line 95
        num_chunks = get_split_num(info['tx']['size'], DEFAULT_CHUNK_SIZE)

        # TS line 96-100
        self.start_segment_index = info['tx']['startEntryIndex'] // DEFAULT_SEGMENT_MAX_CHUNKS
        self.end_segment_index = (
            (info['tx']['startEntryIndex'] +
             get_split_num(info['tx']['size'], DEFAULT_CHUNK_SIZE) - 1) //
            DEFAULT_SEGMENT_MAX_CHUNKS
        )

        # TS line 101
        num_tasks = self.end_segment_index - self.start_segment_index + 1

        # TS line 102
        for task_ind in range(num_tasks):
            # TS line 103
            seg_array, err = self.download_task(
                info,
                segment_offset,
                task_ind,
                num_chunks,
                proof
            )

            # TS line 104-106
            if err is not None:
                return err

            # TS line 107 - Append to file
            with open(file_path, 'ab') as f:
                f.write(seg_array)

        # TS line 109
        return None

    @staticmethod
    def check_exist(input_path: str) -> bool:
        """
        Check if path exists or is invalid.

        TS SDK utils.js lines 24-37.

        Args:
            input_path: Path to check

        Returns:
            True if path is invalid or exists
        """
        # TS line 25-28
        dir_name = os.path.dirname(input_path)
        if not os.path.exists(dir_name):
            return True

        # TS line 29-31
        if os.path.exists(input_path) and os.path.isdir(input_path):
            return True

        # TS line 33-35
        if not os.path.exists(input_path):
            return False

        # TS line 36
        return True
