"""
Stream data builder for KV operations.

Ported from official TypeScript SDK:
src.ts/kv/builder.ts
"""
from typing import Dict, Optional
from .types import AccessControl, StreamData, StreamRead, StreamWrite
from .constants import MAX_KEY_SIZE, MAX_SET_SIZE, STREAM_DOMAIN

# Type aliases
Hash = str


class StreamDataBuilder:
    """
    Builder for constructing StreamData objects.
    
    TS SDK lines 9-155.
    """
    
    def __init__(self, version: int):
        """
        Initialize builder.
        
        TS SDK lines 16-22.
        
        Args:
            version: Stream data version
        """
        self.version = version
        self.stream_ids: Dict[Hash, bool] = {}
        self.controls: list[AccessControl] = []
        self.reads: Dict[Hash, Dict[str, bool]] = {}
        self.writes: Dict[Hash, Dict[str, bytes]] = {}

    def _hex_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes."""
        if hex_str.startswith("0x"):
            hex_str = hex_str[2:]
        return bytes.fromhex(hex_str)

    def build(self, sorted_: bool = False) -> StreamData:
        """
        Build StreamData from accumulated operations.
        
        TS SDK lines 32-109.
        
        Args:
            sorted_: Whether to sort reads and writes by stream_id and key
            
        Returns:
            Constructed StreamData object
        """
        data = StreamData(version=self.version)
        
        # controls
        data.controls = self._build_access_control()
        
        # reads
        data.reads = []
        for stream_id, keys in self.reads.items():
            for k in keys.keys():
                key = self._hex_to_bytes(k)
                if len(key) > MAX_KEY_SIZE:
                    raise ValueError("Key too large")
                if len(key) == 0:
                    raise ValueError("Key is empty")
                data.reads.append(StreamRead(
                    stream_id=stream_id,
                    key=key
                ))
                
                if len(data.reads) > MAX_SET_SIZE:
                    raise ValueError("Size too large")
        
        # writes
        data.writes = []
        for stream_id, keys in self.writes.items():
            for k, d in keys.items():
                key = self._hex_to_bytes(k)
                if len(key) > MAX_KEY_SIZE:
                    raise ValueError("Key too large")
                if len(key) == 0:
                    raise ValueError("Key is empty")
                data.writes.append(StreamWrite(
                    stream_id=stream_id,
                    key=key,
                    data=d
                ))
                
                if len(data.writes) > MAX_SET_SIZE:
                    raise ValueError("Size too large")
        
        if sorted_:
            # Sort reads by stream_id, then by key
            data.reads.sort(key=lambda x: (x.stream_id, x.key.hex()))
            # Sort writes by stream_id, then by key
            data.writes.sort(key=lambda x: (x.stream_id, x.key.hex()))
        
        return data

    def set(self, stream_id: str, key: bytes, data: bytes) -> None:
        """
        Add a write operation.
        
        TS SDK lines 111-121.
        
        Args:
            stream_id: Stream ID (hex string)
            key: Key bytes
            data: Value bytes
        """
        self.add_stream_id(stream_id)
        
        if stream_id not in self.writes:
            self.writes[stream_id] = {}
        
        self.writes[stream_id][key.hex()] = data

    def add_stream_id(self, stream_id: Hash) -> None:
        """
        Register a stream ID.
        
        TS SDK lines 123-125.
        
        Args:
            stream_id: Stream ID (hex string)
        """
        self.stream_ids[stream_id] = True

    def build_tags(self, sorted_: bool = False) -> bytes:
        """
        Build tags for upload.
        
        TS SDK lines 127-135.
        
        Args:
            sorted_: Whether to sort stream IDs
            
        Returns:
            Encoded tags bytes
        """
        ids = list(self.stream_ids.keys())
        
        if sorted_:
            ids.sort()
        
        return self._create_tags(ids)

    def _create_tags(self, stream_ids: list[Hash]) -> bytes:
        """
        Create tags from stream IDs.
        
        TS SDK lines 137-147.
        
        Args:
            stream_ids: List of stream IDs
            
        Returns:
            Encoded tags
        """
        result = bytearray((1 + len(stream_ids)) * 32)
        
        # Set stream domain
        result[0:32] = STREAM_DOMAIN
        
        # Set each stream ID
        for index, id_ in enumerate(stream_ids):
            id_bytes = self._hex_to_bytes(id_)
            result[32 * (index + 1):32 * (index + 2)] = id_bytes
        
        return bytes(result)

    def _build_access_control(self) -> list[AccessControl]:
        """
        Build access controls.
        
        TS SDK lines 149-154.
        
        Returns:
            List of access controls
        """
        if len(self.controls) > MAX_SET_SIZE:
            raise ValueError("Size too large")
        return self.controls
