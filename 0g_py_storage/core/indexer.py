"""
Indexer RPC client for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/indexer/Indexer.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import Optional, List, Dict, Any, Tuple

try:
    from ..utils.http import HttpProvider
    from .storage_node import StorageNode
    from .node_selector import select_nodes
    from .downloader import Downloader
except ImportError:
    from utils.http import HttpProvider
    from core.storage_node import StorageNode
    from core.node_selector import select_nodes
    from core.downloader import Downloader


class Indexer(HttpProvider):
    """
    Indexer RPC client.

    Ported from Indexer.js (lines 1-102).

    The indexer provides information about storage nodes and file locations
    in the 0G network.
    """

    def __init__(self, url: str):
        """
        Initialize indexer client.

        TS SDK lines 10-12.

        Args:
            url: Indexer RPC URL
        """
        super().__init__(url)

    def get_sharded_nodes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get list of sharded storage nodes.

        TS SDK lines 13-18.

        Returns:
            Dictionary with 'trusted' and 'discovered' node lists
        """
        res = self.request(method='indexer_getShardedNodes')
        return res

    def get_node_locations(self) -> Any:
        """
        Get node location information.

        TS SDK lines 19-24.

        Returns:
            Node locations
        """
        res = self.request(method='indexer_getNodeLocations')
        return res

    def get_file_locations(self, root_hash: str) -> List[Dict[str, Any]]:
        """
        Get storage nodes that have a specific file.

        TS SDK lines 25-31.

        Args:
            root_hash: File root hash

        Returns:
            List of storage node locations
        """
        res = self.request(
            method='indexer_getFileLocations',
            params=[root_hash]
        )
        return res

    def select_nodes(
        self,
        expected_replica: int
    ) -> Tuple[List[StorageNode], Optional[Exception]]:
        """
        Select storage nodes that meet replication requirements.

        TS SDK lines 50-65.

        Args:
            expected_replica: Number of replicas required

        Returns:
            Tuple of (storage_node_clients, error)
        """
        # TS line 51
        nodes = self.get_sharded_nodes()

        # TS line 52
        trusted, ok = select_nodes(nodes['trusted'], expected_replica)

        # TS line 53-57
        if not ok:
            return (
                [],
                Exception('cannot select a subset from the returned nodes that meets the replication requirement')
            )

        # TS line 59
        clients = []

        # TS line 60-63
        for node in trusted:
            sn = StorageNode(node['url'])
            clients.append(sn)

        # TS line 64
        return (clients, None)

    def new_uploader_from_indexer_nodes(
        self,
        blockchain_rpc: str,
        signer: Any,
        expected_replica: int,
        opts: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Optional[Exception]]:
        """
        Create uploader with nodes selected from indexer.

        TS SDK lines 32-49.

        NOTE: Requires Uploader class (Phase 7).
        This is a placeholder for now.

        Args:
            blockchain_rpc: Blockchain RPC URL
            signer: Transaction signer
            expected_replica: Expected replicas
            opts: Optional upload options

        Returns:
            Tuple of (uploader, error)
        """
        # TS line 33-36
        clients, err = self.select_nodes(expected_replica)
        if err is not None:
            return (None, err)

        # TS line 37-43
        status = clients[0].get_status()
        if status is None:
            return (
                None,
                Exception('failed to get status from the selected node')
            )

        # TS line 44
        print('First selected node status :', status)

        # TS line 45 - get_flow_contract (needs to be implemented)
        # For now, return placeholder
        # flow = get_flow_contract(status['networkIdentity']['flowAddress'], signer)

        # TS line 46
        print('Selected nodes:', clients)

        # TS line 47 - Create Uploader (Phase 7)
        # uploader = Uploader(clients, blockchain_rpc, flow, opts?.gasPrice, opts?.gasLimit)

        # TS line 48
        # return (uploader, None)

        # Placeholder return
        return (None, Exception("Uploader not implemented yet (Phase 7)"))

    def upload(
        self,
        file: Any,
        blockchain_rpc: str,
        signer: Any,
        upload_opts: Optional[Dict[str, Any]] = None,
        retry_opts: Optional[Dict[str, Any]] = None,
        opts: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, str], Optional[Exception]]:
        """
        Upload file to storage network.

        TS SDK lines 66-86.

        NOTE: Requires Uploader class (Phase 7).
        This is a placeholder for now.

        Args:
            file: File to upload
            blockchain_rpc: Blockchain RPC URL
            signer: Transaction signer
            upload_opts: Upload options
            retry_opts: Retry options
            opts: Additional options

        Returns:
            Tuple of (result_dict, error)
        """
        # TS line 67-70
        expected_replica = 1
        if upload_opts is not None and 'expectedReplica' in upload_opts:
            expected_replica = max(1, upload_opts['expectedReplica'])

        # TS line 71-74
        uploader, err = self.new_uploader_from_indexer_nodes(
            blockchain_rpc,
            signer,
            expected_replica,
            opts
        )
        if err is not None or uploader is None:
            return ({'txHash': '', 'rootHash': ''}, err)

        # TS line 75-84
        if upload_opts is None:
            upload_opts = {
                'tags': '0x',
                'finalityRequired': True,
                'taskSize': 10,
                'expectedReplica': 1,
                'skipTx': False,
                'fee': 0,
            }

        # TS line 85 - uploader.uploadFile (Phase 7)
        # return await uploader.uploadFile(file, upload_opts, retry_opts)

        # Placeholder return
        return ({'txHash': '', 'rootHash': ''}, Exception("Upload not implemented yet (Phase 7)"))

    def download(
        self,
        root_hash: str,
        file_path: str,
        proof: bool = False
    ) -> Optional[Exception]:
        """
        Download file from storage network.

        TS SDK lines 87-99.

        Args:
            root_hash: File root hash
            file_path: Output file path
            proof: Whether to download with proof

        Returns:
            Error if download failed, None otherwise
        """
        # TS line 88-91
        locations = self.get_file_locations(root_hash)
        if len(locations) == 0:
            return Exception('failed to get file locations')

        # TS line 92-96
        clients = []
        for node in locations:
            sn = StorageNode(node['url'])
            clients.append(sn)

        # TS line 97
        downloader = Downloader(clients)

        # TS line 98
        return downloader.download_file(root_hash, file_path, proof)
