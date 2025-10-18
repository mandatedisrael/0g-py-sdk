"""
Storage node RPC client.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/node/StorageNode.js

CRITICAL: Must EXACTLY match TypeScript SDK RPC methods.
"""
from typing import Optional, Dict, Any, List

try:
    from ..utils.http import HttpProvider
except ImportError:
    from utils.http import HttpProvider


class StorageNode(HttpProvider):
    """
    Storage node RPC client.

    Ported from StorageNode.js (lines 1-103).

    Provides methods to interact with 0G storage nodes via JSON-RPC.
    """

    def __init__(self, url: str):
        """
        Initialize storage node client.

        TS SDK lines 6-8.

        Args:
            url: Storage node RPC URL
        """
        super().__init__(url)

    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Get storage node status.

        TS SDK lines 9-12.

        Returns:
            Status information or None
        """
        res = self.request(method='zgs_getStatus')
        return res

    def upload_segment(self, seg: Dict[str, Any]) -> Any:
        """
        Upload a single segment.

        TS SDK lines 13-19.

        Args:
            seg: Segment data

        Returns:
            Upload result
        """
        res = self.request(
            method='zgs_uploadSegment',
            params=[seg]
        )
        return res

    def upload_segments(self, segs: List[Dict[str, Any]]) -> Any:
        """
        Upload multiple segments.

        TS SDK lines 20-26.

        Args:
            segs: List of segment data

        Returns:
            Upload result
        """
        res = self.request(
            method='zgs_uploadSegments',
            params=[segs]
        )
        return res

    def upload_segment_by_tx_seq(self, seg: Dict[str, Any], tx_seq: int) -> Any:
        """
        Upload segment by transaction sequence number.

        TS SDK lines 28-34.

        Args:
            seg: Segment data
            tx_seq: Transaction sequence number

        Returns:
            Upload result
        """
        res = self.request(
            method='zgs_uploadSegmentByTxSeq',
            params=[seg, tx_seq]
        )
        return res

    def upload_segments_by_tx_seq(self, segs: List[Dict[str, Any]], tx_seq: int) -> Any:
        """
        Upload multiple segments by transaction sequence number.

        TS SDK lines 36-42.

        Args:
            segs: List of segment data
            tx_seq: Transaction sequence number

        Returns:
            Upload result
        """
        res = self.request(
            method='zgs_uploadSegmentsByTxSeq',
            params=[segs, tx_seq]
        )
        return res

    def download_segment(self, root: str, start_index: int, end_index: int) -> Any:
        """
        Download segment data.

        TS SDK lines 43-49.

        Args:
            root: File root hash
            start_index: Start segment index
            end_index: End segment index

        Returns:
            Segment data
        """
        seg = self.request(
            method='zgs_downloadSegment',
            params=[root, start_index, end_index]
        )
        return seg

    def download_segment_with_proof(self, root: str, index: int) -> Any:
        """
        Download segment with merkle proof.

        TS SDK lines 50-56.

        Args:
            root: File root hash
            index: Segment index

        Returns:
            Segment with proof
        """
        seg = self.request(
            method='zgs_downloadSegmentWithProof',
            params=[root, index]
        )
        return seg

    def download_segment_by_tx_seq(self, tx_seq: int, start_index: int, end_index: int) -> Any:
        """
        Download segment by transaction sequence.

        TS SDK lines 58-64.

        Args:
            tx_seq: Transaction sequence number
            start_index: Start segment index
            end_index: End segment index

        Returns:
            Segment data
        """
        seg = self.request(
            method='zgs_downloadSegmentByTxSeq',
            params=[tx_seq, start_index, end_index]
        )
        return seg

    def download_segment_with_proof_by_tx_seq(self, tx_seq: int, index: int) -> Any:
        """
        Download segment with proof by transaction sequence.

        TS SDK lines 66-72.

        Args:
            tx_seq: Transaction sequence number
            index: Segment index

        Returns:
            Segment with proof
        """
        seg = self.request(
            method='zgs_downloadSegmentWithProofByTxSeq',
            params=[tx_seq, index]
        )
        return seg

    def get_sector_proof(self, sector_index: int, root: str) -> Any:
        """
        Get proof of a sector.

        TS SDK lines 74-80.

        Args:
            sector_index: Sector index
            root: File root hash

        Returns:
            Sector proof
        """
        seg = self.request(
            method='zgs_getSectorProof',
            params=[sector_index, root]
        )
        return seg

    def get_file_info(self, root: str, need_available: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get file information.

        TS SDK lines 81-87.

        Args:
            root: File root hash
            need_available: Whether to check availability

        Returns:
            File info or None
        """
        info = self.request(
            method='zgs_getFileInfo',
            params=[root, need_available]
        )
        return info

    def get_file_info_by_tx_seq(self, tx_seq: int) -> Optional[Dict[str, Any]]:
        """
        Get file information by transaction sequence.

        TS SDK lines 88-94.

        Args:
            tx_seq: Transaction sequence number

        Returns:
            File info or None
        """
        info = self.request(
            method='zgs_getFileInfoByTxSeq',
            params=[tx_seq]
        )
        return info

    def get_shard_config(self) -> Optional[Dict[str, Any]]:
        """
        Get shard configuration.

        TS SDK lines 95-100.

        Returns:
            Shard config or None
        """
        config = self.request(
            method='zgs_getShardConfig'
        )
        return config
