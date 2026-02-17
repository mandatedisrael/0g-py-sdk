"""
KV iterator for traversing key-value pairs.

Ported from official TypeScript SDK:
src.ts/kv/iterator.ts
"""
from typing import Optional

try:
    from ..models.file import KeyValue
except ImportError:
    from models.file import KeyValue

from .client import KvClient

# Type aliases
Bytes = bytes


class KvIterator:
    """
    Iterator for traversing key-value pairs in a stream.
    
    TS SDK lines 5-116.
    """

    def __init__(self, client: KvClient, stream_id: str, version: Optional[int] = None):
        """
        Create a new iterator.
        
        TS SDK lines 16-20.
        
        Args:
            client: KvClient instance
            stream_id: Stream ID (hex string)
            version: Optional specific version
        """
        self.client = client
        self.stream_id = stream_id
        self.version = version
        self.current_pair: Optional[KeyValue] = None

    def valid(self) -> bool:
        """
        Check if current position is valid.
        
        TS SDK lines 22-24.
        
        Returns:
            True if current pair exists
        """
        return self.current_pair is not None

    def get_current_pair(self) -> Optional[KeyValue]:
        """
        Get current key-value pair.
        
        TS SDK lines 27-29.
        
        Returns:
            Current KeyValue or None
        """
        return self.current_pair

    def _move(self, kv: Optional[KeyValue]) -> Optional[Exception]:
        """
        Move to a new key-value pair.
        
        TS SDK lines 31-51.
        
        Args:
            kv: KeyValue to move to
            
        Returns:
            Error if value not found, None on success
        """
        if kv is None:
            self.current_pair = None
            return None
        
        # Get full value for this key
        value = self.client.get_value(
            self.stream_id,
            kv.key,
            kv.version
        )
        
        if value is None:
            return Exception("Value not found")
        
        self.current_pair = KeyValue(
            key=kv.key,
            data=value.data,
            size=value.size,
            version=kv.version
        )
        return None

    def seek_before(self, key: Bytes) -> Optional[Exception]:
        """
        Seek to position before or at key.
        
        TS SDK lines 53-63.
        
        Args:
            key: Key to seek before
            
        Returns:
            Error or None on success
        """
        kv = self.client.get_prev(
            self.stream_id,
            key,
            0,
            0,
            True,  # inclusive
            self.version
        )
        return self._move(kv)

    def seek_after(self, key: Bytes) -> Optional[Exception]:
        """
        Seek to position after or at key.
        
        TS SDK lines 65-75.
        
        Args:
            key: Key to seek after
            
        Returns:
            Error or None on success
        """
        kv = self.client.get_next(
            self.stream_id,
            key,
            0,
            0,
            True,  # inclusive
            self.version
        )
        return self._move(kv)

    def seek_to_first(self) -> Optional[Exception]:
        """
        Seek to first key-value pair.
        
        TS SDK lines 77-80.
        
        Returns:
            Error or None on success
        """
        kv = self.client.get_first(self.stream_id, 0, 0, self.version)
        return self._move(kv)

    def seek_to_last(self) -> Optional[Exception]:
        """
        Seek to last key-value pair.
        
        TS SDK lines 82-85.
        
        Returns:
            Error or None on success
        """
        kv = self.client.get_last(self.stream_id, 0, 0, self.version)
        return self._move(kv)

    def next(self) -> Optional[Exception]:
        """
        Move to next key-value pair.
        
        TS SDK lines 87-100.
        
        Returns:
            Error if iterator invalid, or None on success
        """
        if not self.valid():
            return Exception("Iterator invalid")
        
        kv = self.client.get_next(
            self.stream_id,
            self.current_pair.key,
            0,
            0,
            False,  # not inclusive
            self.version
        )
        return self._move(kv)

    def prev(self) -> Optional[Exception]:
        """
        Move to previous key-value pair.
        
        TS SDK lines 102-115.
        
        Returns:
            Error if iterator invalid, or None on success
        """
        if not self.valid():
            return Exception("Iterator invalid")
        
        kv = self.client.get_prev(
            self.stream_id,
            self.current_pair.key,
            0,
            0,
            False,  # not inclusive
            self.version
        )
        return self._move(kv)
