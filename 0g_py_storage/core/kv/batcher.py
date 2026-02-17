"""
KV Batcher for batching KV operations and uploading.

Ported from official TypeScript SDK:
src.ts/kv/batcher.ts
"""
from typing import Optional, Dict, Any, List, Tuple

from .builder import StreamDataBuilder

try:
    from ..core.storage_node import StorageNode
    from ..core.file import ZgFile
    from ..core.uploader import Uploader
    from ..contracts.flow import FlowContract
except ImportError:
    from core.storage_node import StorageNode
    from core.file import ZgFile
    from core.uploader import Uploader
    from contracts.flow import FlowContract


# Default upload options
DEFAULT_UPLOAD_OPTION: Dict[str, Any] = {
    'tags': b'\x00',
    'finalityRequired': True,
    'taskSize': 10,
    'expectedReplica': 1,
    'skipTx': False,
}


class Batcher:
    """
    Batcher for KV operations.
    
    TS SDK lines 11-51.
    
    Accumulates KV write operations and uploads them as a batch.
    """

    def __init__(
        self,
        version: int,
        clients: List[StorageNode],
        flow: FlowContract,
        provider: str
    ):
        """
        Initialize batcher.
        
        TS SDK lines 17-27.
        
        Args:
            version: Stream data version
            clients: List of storage node clients
            flow: Flow contract instance
            provider: Blockchain RPC URL
        """
        self.stream_data_builder = StreamDataBuilder(version)
        self.clients = clients
        self.flow = flow
        self.blockchain_rpc = provider

    def set(self, stream_id: str, key: bytes, data: bytes) -> None:
        """
        Add a write operation to the batch.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            data: Value bytes
        """
        self.stream_data_builder.set(stream_id, key, data)

    def exec(
        self,
        opts: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, str], Optional[Exception]]:
        """
        Execute the batched operations by uploading to storage.
        
        TS SDK lines 29-50.
        
        Args:
            opts: Upload options (optional)
            
        Returns:
            Tuple of ({txHash, rootHash}, error)
        """
        # Build stream data
        stream_data = self.stream_data_builder.build()
        encoded = stream_data.encode()
        
        # Create in-memory file from encoded data
        data = ZgFile.from_bytes(encoded)
        
        # Create uploader
        uploader = Uploader(
            self.clients,
            self.blockchain_rpc,
            self.flow
        )
        
        # Set up options
        if opts is None:
            opts = DEFAULT_UPLOAD_OPTION.copy()
        
        # Add tags from builder
        opts['tags'] = self.stream_data_builder.build_tags()
        
        # Upload the file
        return uploader.upload_file(data, opts)
