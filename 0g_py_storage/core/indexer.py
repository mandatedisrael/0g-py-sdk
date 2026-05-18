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
            print(f"  - {node['url']} (shard {node['config']['shardId']}/{node['config']['numShard']})")

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
        proof: bool = False,
        symmetric_key: Optional[bytes] = None,
        private_key: Optional[Any] = None,
    ) -> Optional[Exception]:
        """
        Download file from storage network.

        TS SDK lines 87-99.

        Args:
            root_hash: File root hash
            file_path: Output file path
            proof: Whether to download with proof
            symmetric_key: Optional 32-byte AES key (v1-encrypted files).
            private_key: Optional secp256k1 private key (v2/ECIES files).

        Returns:
            Error if download failed, None otherwise
        """
        downloader, err = self._new_downloader_from_indexer_nodes(root_hash)
        if err is not None or downloader is None:
            return err
        return downloader.download_file(
            root_hash,
            file_path,
            proof,
            symmetric_key=symmetric_key,
            private_key=private_key,
        )

    def _new_downloader_from_indexer_nodes(
        self, root_hash: str
    ) -> Tuple[Optional["Downloader"], Optional[Exception]]:
        """
        Build a ``Downloader`` from the indexer's file-location list.

        Mirrors TS ``Indexer.newDownloaderFromIndexerNodes`` for reuse across
        ``download`` and ``peek_header``.
        """
        locations = self.get_file_locations(root_hash)

        if locations is None or len(locations) == 0:
            print("Indexer doesn't have file locations, querying storage nodes directly...")
            sharded = self.get_sharded_nodes()
            candidates = sharded.get('trusted', [])
            if len(candidates) == 0:
                candidates = sharded.get('discovered', [])
            if candidates is None or len(candidates) == 0:
                node_locations = self.get_node_locations()
                if node_locations is None or len(node_locations) == 0:
                    return None, Exception('failed to get storage node locations')
                locations = [{'url': f'http://{ip}:5678'} for ip in node_locations.keys()]
            else:
                locations = candidates

        clients = []
        for node in locations:
            if isinstance(node, dict):
                sn = StorageNode(node['url'])
            elif isinstance(node, str):
                sn = StorageNode(node)
            else:
                continue
            clients.append(sn)

        if not clients:
            return None, Exception('no usable storage node clients')

        return Downloader(clients), None

    def peek_header(
        self, root_hash: str
    ) -> Tuple[Optional["EncryptionHeader"], Optional[Exception]]:
        """
        Inspect the first segment of ``root_hash`` and return its parsed
        ``EncryptionHeader`` if it carries one, ``(None, None)`` if not, or
        ``(None, error)`` on transport failure. Mirrors TS
        ``Indexer.peekHeader``.

        Useful for rendering a "this file is encrypted, supply a key"
        prompt before committing to a full download.
        """
        try:
            from .encryption import parse_encryption_header
        except ImportError:  # pragma: no cover
            from core.encryption import parse_encryption_header

        downloader, err = self._new_downloader_from_indexer_nodes(root_hash)
        if err is not None or downloader is None:
            return None, err

        # The Python Downloader currently writes to disk. To mirror TS's
        # "download to bytes" + slice the first 50 bytes, we use a temp file.
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        os.unlink(tmp_path)  # download_file rejects existing paths

        try:
            dl_err = downloader.download_file(root_hash, tmp_path, False)
            if dl_err is not None:
                return None, dl_err
            with open(tmp_path, 'rb') as f:
                prefix = f.read(50)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        try:
            return parse_encryption_header(prefix), None
        except Exception:
            return None, None
