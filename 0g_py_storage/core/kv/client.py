"""
KV client for high-level key-value operations.

Ported from official TypeScript SDK:
src.ts/kv/client.ts
"""
from typing import Optional, List, TYPE_CHECKING
import base64

try:
    from ..core.storage_kv import StorageKv
except ImportError:
    from core.storage_kv import StorageKv

try:
    from ..models.file import Value, KeyValue
except ImportError:
    from models.file import Value, KeyValue

from .constants import MAX_QUERY_SIZE

if TYPE_CHECKING:
    from .iterator import KvIterator

# Type aliases
Hash = str
Bytes = bytes


class KvClient:
    """
    High-level KV storage client.
    
    TS SDK lines 6-171.
    
    Provides convenient methods for KV operations with automatic
    pagination and value assembly.
    """

    def __init__(self, rpc: str):
        """
        Initialize KV client.
        
        TS SDK lines 9-12.
        
        Args:
            rpc: Storage node RPC URL
        """
        self.inner = StorageKv(rpc)

    def new_iterator(self, stream_id: str, version: Optional[int] = None) -> "KvIterator":
        """
        Create a new iterator for traversing key-value pairs.
        
        TS SDK lines 14-16.
        
        Args:
            stream_id: Stream ID (hex string)
            version: Optional specific version
            
        Returns:
            KvIterator instance
        """
        # Import here to avoid circular import
        from .iterator import KvIterator
        return KvIterator(self, stream_id, version)

    def get_value(
        self,
        stream_id: str,
        key: Bytes,
        version: Optional[int] = None
    ) -> Optional[Value]:
        """
        Get complete value for a key.
        
        TS SDK lines 18-56.
        
        Automatically handles pagination to retrieve the full value.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            Value or None if not found
        """
        val = Value(
            data="",
            size=0,
            version=version if version is not None else 0
        )
        
        while True:
            # Get current data length for pagination
            current_len = len(base64.b64decode(val.data)) if val.data else 0
            
            seg = self.inner.get_value(
                stream_id,
                key,
                current_len,
                MAX_QUERY_SIZE,
                version
            )
            
            if seg is None:
                return None
            
            # Handle version mismatch
            if val.version == float('inf'):
                val.version = seg.version
            elif val.version != seg.version:
                val.version = seg.version
                val.data = ""
            
            val.size = seg.size
            
            # Concatenate data
            seg_data = base64.b64decode(seg.data) if seg.data else b""
            val_data = base64.b64decode(val.data) if val.data else b""
            combined = val_data + seg_data
            val.data = base64.b64encode(combined).decode()
            
            # Check if we have all data
            if seg.size == len(combined):
                return val

    def get(
        self,
        stream_id: str,
        key: Bytes,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[Value]:
        """
        Get partial value with pagination.
        
        TS SDK lines 58-66.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            start_index: Start byte offset
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            Value or None
        """
        return self.inner.get_value(stream_id, key, start_index, length, version)

    def get_next(
        self,
        stream_id: str,
        key: Bytes,
        start_index: int,
        length: int,
        inclusive: bool,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get next key-value pair.
        
        TS SDK lines 68-84.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Starting key bytes
            start_index: Start byte offset for value
            length: Number of bytes to retrieve
            inclusive: Whether to include starting key
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        return self.inner.get_next(
            stream_id,
            key,
            start_index,
            length,
            inclusive,
            version
        )

    def get_prev(
        self,
        stream_id: str,
        key: Bytes,
        start_index: int,
        length: int,
        inclusive: bool,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get previous key-value pair.
        
        TS SDK lines 86-102.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Starting key bytes
            start_index: Start byte offset for value
            length: Number of bytes to retrieve
            inclusive: Whether to include starting key
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        return self.inner.get_prev(
            stream_id,
            key,
            start_index,
            length,
            inclusive,
            version
        )

    def get_first(
        self,
        stream_id: str,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get first key-value pair in stream.
        
        TS SDK lines 104-111.
        
        Args:
            stream_id: Stream ID (hex string)
            start_index: Start byte offset for value
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        return self.inner.get_first(stream_id, start_index, length, version)

    def get_last(
        self,
        stream_id: str,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get last key-value pair in stream.
        
        TS SDK lines 113-120.
        
        Args:
            stream_id: Stream ID (hex string)
            start_index: Start byte offset for value
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        return self.inner.get_last(stream_id, start_index, length, version)

    def get_transaction_result(self, tx_seq: int) -> Optional[str]:
        """
        Get transaction result.
        
        TS SDK lines 122-124.
        
        Args:
            tx_seq: Transaction sequence number
            
        Returns:
            Transaction result string or None
        """
        return self.inner.get_transaction_result(tx_seq)

    def get_holding_stream_ids(self) -> List[str]:
        """
        Get list of stream IDs held by this node.
        
        TS SDK lines 126-128.
        
        Returns:
            List of stream IDs
        """
        return self.inner.get_holding_stream_ids()

    def has_write_permission(
        self,
        account: str,
        stream_id: str,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account has write permission for key.
        
        TS SDK lines 130-137.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if has write permission
        """
        return self.inner.has_write_permission(account, stream_id, key, version)

    def is_admin(
        self,
        account: str,
        stream_id: str,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is admin of stream.
        
        TS SDK lines 139-145.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            version: Optional specific version
            
        Returns:
            True if is admin
        """
        return self.inner.is_admin(account, stream_id, version)

    def is_special_key(
        self,
        stream_id: str,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if key is special.
        
        TS SDK lines 147-153.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if is special key
        """
        return self.inner.is_special_key(stream_id, key, version)

    def is_writer_of_key(
        self,
        account: str,
        stream_id: str,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is writer of specific key.
        
        TS SDK lines 155-162.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if is writer of key
        """
        return self.inner.is_writer_of_key(account, stream_id, key, version)

    def is_writer_of_stream(
        self,
        account: str,
        stream_id: str,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is writer of stream.
        
        TS SDK lines 164-170.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            version: Optional specific version
            
        Returns:
            True if is writer of stream
        """
        return self.inner.is_writer_of_stream(account, stream_id, version)
