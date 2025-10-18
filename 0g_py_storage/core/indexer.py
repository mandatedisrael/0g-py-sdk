"""
Indexer RPC client for 0G Storage.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/indexer/Indexer.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import Optional, List, Dict, Any, Tuple
from web3 import Web3

try:
    from ..utils.http import HttpProvider
    from .storage_node import StorageNode
    from .node_selector import select_nodes
    from .downloader import Downloader
    from .uploader import Uploader
    from ..contracts.flow import FlowContract
except ImportError:
    from utils.http import HttpProvider
    from core.storage_node import StorageNode
    from core.node_selector import select_nodes
    from core.downloader import Downloader
    from core.uploader import Uploader
    from contracts.flow import FlowContract


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
        try:
            res = self.request(
                method='indexer_getFileLocations',
                params=[root_hash]
            )
            return res
        except Exception as e:
            # Indexer method might not be available or file not indexed yet
            return None

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

        status = clients[0].get_status()
        if status is None:
            return (
                None,
                Exception('failed to get status from the selected node')
            )

        print('First selected node status :', status)
        print('Selected nodes:', clients)

        # Create Flow contract and Uploader
        web3 = Web3(Web3.HTTPProvider(blockchain_rpc))
        flow = FlowContract(web3, status['networkIdentity']['flowAddress'])
        gas_price = opts.get('gasPrice', 0) if opts else 0
        gas_limit = opts.get('gasLimit', 0) if opts else 0
        uploader = Uploader(clients, blockchain_rpc, flow, gas_price, gas_limit)

        return (uploader, None)

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

        uploader, err = self.new_uploader_from_indexer_nodes(
            blockchain_rpc,
            signer,
            expected_replica,
            opts
        )
        if err is not None or uploader is None:
            return ({'txHash': '', 'rootHash': ''}, err)

        if upload_opts is None:
            upload_opts = {
                'tags': b'\x00',
                'finalityRequired': True,
                'taskSize': 10,
                'expectedReplica': 1,
                'skipTx': False,
                'fee': 0,
            }

        return uploader.upload_file(file, upload_opts, retry_opts)

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

        # If indexer doesn't have file locations (returns None or empty),
        # fall back to querying all available storage nodes
        if locations is None or len(locations) == 0:
            print("Indexer doesn't have file locations, querying storage nodes directly...")
            node_locations = self.get_node_locations()
            if node_locations is None or len(node_locations) == 0:
                return Exception('failed to get storage node locations')

            # node_locations is a dict mapping IP -> location_info
            # Convert to list of URL dicts for compatibility
            locations = []
            for ip in node_locations.keys():
                locations.append({'url': f'http://{ip}:5678'})

        # TS line 92-96
        clients = []
        for node in locations:
            # Handle both dict with 'url' key and direct URL strings
            if isinstance(node, dict):
                sn = StorageNode(node['url'])
            elif isinstance(node, str):
                sn = StorageNode(node)
            else:
                continue
            clients.append(sn)

        # TS line 97
        downloader = Downloader(clients)

        # TS line 98
        return downloader.download_file(root_hash, file_path, proof)
