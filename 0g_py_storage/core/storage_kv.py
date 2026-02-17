"""
Storage KV RPC client.

Ported from official TypeScript SDK:
src.ts/node/StorageKv.ts

Provides low-level RPC methods for KV storage operations.
"""
from typing import Optional, Dict, Any, List

try:
    from ..utils.http import HttpProvider
except ImportError:
    from utils.http import HttpProvider

try:
    from ..models.file import Value, KeyValue
except ImportError:
    from models.file import Value, KeyValue

# Type aliases
Hash = str
Bytes = bytes


class StorageKv(HttpProvider):
    """
    Storage KV RPC client.
    
    Ported from StorageKv.ts (lines 1-216).
    
    Provides methods to interact with 0G KV storage nodes via JSON-RPC.
    """

    def __init__(self, url: str):
        """
        Initialize storage KV client.
        
        TS SDK lines 6-8.
        
        Args:
            url: Storage node RPC URL
        """
        super().__init__(url)

    def _parse_value(self, res: Optional[Dict[str, Any]]) -> Optional[Value]:
        """Parse Value from RPC response."""
        if res is None:
            return None
        return Value(
            version=res.get("version", 0),
            data=res.get("data", ""),
            size=res.get("size", 0)
        )

    def _parse_key_value(self, res: Optional[Dict[str, Any]]) -> Optional[KeyValue]:
        """Parse KeyValue from RPC response."""
        if res is None:
            return None
        key_data = res.get("key", "")
        if isinstance(key_data, str):
            # Key comes as hex string
            if key_data.startswith("0x"):
                key_data = key_data[2:]
            key_bytes = bytes.fromhex(key_data) if key_data else b""
        else:
            key_bytes = bytes(key_data)
        return KeyValue(
            version=res.get("version", 0),
            data=res.get("data", ""),
            size=res.get("size", 0),
            key=key_bytes
        )

    def get_value(
        self,
        stream_id: Hash,
        key: Bytes,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[Value]:
        """
        Get value for a key.
        
        TS SDK lines 11-29.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            start_index: Start index for pagination
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            Value or None
        """
        # Convert key to hex string for RPC
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [stream_id, key_hex, start_index, length]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_getValue", params=params)
        return self._parse_value(res)

    def get_next(
        self,
        stream_id: Hash,
        key: Bytes,
        start_index: int,
        length: int,
        inclusive: bool,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get next key-value pair.
        
        TS SDK lines 31-50.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Starting key bytes
            start_index: Start index for value pagination
            length: Number of bytes to retrieve
            inclusive: Whether to include the starting key
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [stream_id, key_hex, start_index, length, inclusive]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_getNext", params=params)
        return self._parse_key_value(res)

    def get_prev(
        self,
        stream_id: Hash,
        key: Bytes,
        start_index: int,
        length: int,
        inclusive: bool,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get previous key-value pair.
        
        TS SDK lines 52-71.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Starting key bytes
            start_index: Start index for value pagination
            length: Number of bytes to retrieve
            inclusive: Whether to include the starting key
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [stream_id, key_hex, start_index, length, inclusive]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_getPrev", params=params)
        return self._parse_key_value(res)

    def get_first(
        self,
        stream_id: Hash,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get first key-value pair in stream.
        
        TS SDK lines 73-90.
        
        Args:
            stream_id: Stream ID (hex string)
            start_index: Start index for value pagination
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        params: List[Any] = [stream_id, start_index, length]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_getFirst", params=params)
        return self._parse_key_value(res)

    def get_last(
        self,
        stream_id: Hash,
        start_index: int,
        length: int,
        version: Optional[int] = None
    ) -> Optional[KeyValue]:
        """
        Get last key-value pair in stream.
        
        TS SDK lines 92-109.
        
        Args:
            stream_id: Stream ID (hex string)
            start_index: Start index for value pagination
            length: Number of bytes to retrieve
            version: Optional specific version
            
        Returns:
            KeyValue or None
        """
        params: List[Any] = [stream_id, start_index, length]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_getLast", params=params)
        return self._parse_key_value(res)

    def get_transaction_result(self, tx_seq: int) -> Optional[str]:
        """
        Get transaction result.
        
        TS SDK lines 111-117.
        
        Args:
            tx_seq: Transaction sequence number
            
        Returns:
            Transaction result string or None
        """
        res = self.request(
            method="kv_getTransactionResult",
            params=[str(tx_seq)]
        )
        return res

    def get_holding_stream_ids(self) -> List[Hash]:
        """
        Get list of stream IDs held by this node.
        
        TS SDK lines 119-124.
        
        Returns:
            List of stream IDs
        """
        res = self.request(method="kv_getHoldingStreamIds")
        return res if res else []

    def has_write_permission(
        self,
        account: Hash,
        stream_id: Hash,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account has write permission for key.
        
        TS SDK lines 126-142.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if has write permission
        """
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [account, stream_id, key_hex]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_hasWritePermission", params=params)
        return bool(res)

    def is_admin(
        self,
        account: Hash,
        stream_id: Hash,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is admin of stream.
        
        TS SDK lines 144-160.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            version: Optional specific version
            
        Returns:
            True if is admin
        """
        params: List[Any] = [account, stream_id]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_IsAdmin", params=params)
        return bool(res)

    def is_special_key(
        self,
        stream_id: Hash,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if key is special.
        
        TS SDK lines 162-177.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if is special key
        """
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [stream_id, key_hex]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_isSpecialKey", params=params)
        return bool(res)

    def is_writer_of_key(
        self,
        account: Hash,
        stream_id: Hash,
        key: Bytes,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is writer of specific key.
        
        TS SDK lines 179-196.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            key: Key bytes
            version: Optional specific version
            
        Returns:
            True if is writer of key
        """
        key_hex = "0x" + key.hex() if isinstance(key, bytes) else key
        
        params: List[Any] = [account, stream_id, key_hex]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_isWriterOfKey", params=params)
        return bool(res)

    def is_writer_of_stream(
        self,
        account: Hash,
        stream_id: Hash,
        version: Optional[int] = None
    ) -> bool:
        """
        Check if account is writer of stream.
        
        TS SDK lines 198-214.
        
        Args:
            account: Account address (hex string)
            stream_id: Stream ID (hex string)
            version: Optional specific version
            
        Returns:
            True if is writer of stream
        """
        params: List[Any] = [account, stream_id]
        if version is not None:
            params.append(version)
        
        res = self.request(method="kv_isWriterOfStream", params=params)
        return bool(res)
