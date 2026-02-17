"""
KV storage types and data structures.

Ported from official TypeScript SDK:
src.ts/kv/types.ts
"""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
import struct

# Type aliases
Hash = str  # Hex string
Address = str  # Hex string (20 bytes)


class AccessControlType(IntEnum):
    """
    Access control operation types.
    
    TS SDK lines 7-18.
    """
    GRANT_ADMIN_ROLE = 0x00
    RENOUNCE_ADMIN_ROLE = 0x01
    SET_KEY_TO_SPECIAL = 0x10
    SET_KEY_TO_NORMAL = 0x11
    GRANT_WRITE_ROLE = 0x20
    REVOKE_WRITE_ROLE = 0x21
    RENOUNCE_WRITE_ROLE = 0x22
    GRANT_SPECIAL_WRITE_ROLE = 0x30
    REVOKE_SPECIAL_WRITE_ROLE = 0x31
    RENOUNCE_SPECIAL_WRITE_ROLE = 0x32


@dataclass
class StreamRead:
    """
    Stream read operation.
    
    TS SDK lines 20-23.
    """
    stream_id: Hash
    key: bytes


@dataclass
class StreamWrite:
    """
    Stream write operation.
    
    TS SDK lines 25-29.
    """
    stream_id: Hash
    key: bytes
    data: bytes


@dataclass
class AccessControl:
    """
    Access control operation.
    
    TS SDK lines 31-36.
    """
    type: AccessControlType
    stream_id: Hash
    account: Optional[Address] = None
    key: Optional[bytes] = None


@dataclass
class StreamData:
    """
    Stream data container for KV operations.
    
    TS SDK lines 38-179.
    """
    version: int
    reads: List[StreamRead] = field(default_factory=list)
    writes: List[StreamWrite] = field(default_factory=list)
    controls: List[AccessControl] = field(default_factory=list)

    def size(self) -> int:
        """
        Calculate total encoded size in bytes.
        
        TS SDK lines 48-73.
        """
        size = 8  # version size in bytes

        size += 4  # Reads size prefix
        for v in self.reads:
            size += 32 + 3 + len(v.key)

        size += 4  # Writes size prefix
        for v in self.writes:
            size += 32 + 3 + len(v.key) + 8 + len(v.data)

        size += 4  # Controls size prefix
        for v in self.controls:
            size += 1 + 32  # Type + StreamId
            if v.account is not None:
                size += 20  # Address length
            if v.key is not None:
                size += 3 + len(v.key)

        return size

    def _encode_size24(self, size: int) -> bytes:
        """
        Encode size as 24-bit big-endian.
        
        TS SDK lines 75-86.
        """
        if size == 0:
            raise ValueError("Key is empty")
        buf = struct.pack(">I", size)  # 4 bytes big-endian
        if buf[0] != 0:
            raise ValueError("Key too large")
        return buf[1:]  # Return last 3 bytes

    def _encode_size32(self, size: int) -> bytes:
        """
        Encode size as 32-bit big-endian.
        
        TS SDK lines 88-93.
        """
        return struct.pack(">I", size)

    def _encode_size64(self, size: int) -> bytes:
        """
        Encode size as 64-bit big-endian.
        
        TS SDK lines 95-100.
        """
        return struct.pack(">Q", size)

    def _hex_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes."""
        if hex_str.startswith("0x"):
            hex_str = hex_str[2:]
        return bytes.fromhex(hex_str)

    def encode(self) -> bytes:
        """
        Encode stream data to bytes.
        
        TS SDK lines 102-178.
        """
        encoded = bytearray(self.size())
        offset = 0

        # version
        encoded[offset:offset + 8] = self._encode_size64(self.version)
        offset += 8

        # reads
        encoded[offset:offset + 4] = self._encode_size32(len(self.reads))
        offset += 4
        for v in self.reads:
            stream_id_bytes = self._hex_to_bytes(v.stream_id)
            encoded[offset:offset + 32] = stream_id_bytes
            offset += 32

            key_size = self._encode_size24(len(v.key))
            encoded[offset:offset + len(key_size)] = key_size
            offset += len(key_size)

            encoded[offset:offset + len(v.key)] = v.key
            offset += len(v.key)

        # writes
        encoded[offset:offset + 4] = self._encode_size32(len(self.writes))
        offset += 4
        for v in self.writes:
            # add stream id
            stream_id_bytes = self._hex_to_bytes(v.stream_id)
            encoded[offset:offset + 32] = stream_id_bytes
            offset += 32

            # add key size
            key_size = self._encode_size24(len(v.key))
            encoded[offset:offset + len(key_size)] = key_size
            offset += len(key_size)

            # add key
            encoded[offset:offset + len(v.key)] = v.key
            offset += len(v.key)

            # add value size, add value later
            data_size = self._encode_size64(len(v.data))
            encoded[offset:offset + len(data_size)] = data_size
            offset += len(data_size)

        # add all values
        for v in self.writes:
            encoded[offset:offset + len(v.data)] = v.data
            offset += len(v.data)

        # controls
        encoded[offset:offset + 4] = self._encode_size32(len(self.controls))
        offset += 4
        for v in self.controls:
            encoded[offset] = v.type
            offset += 1
            
            stream_id_bytes = self._hex_to_bytes(v.stream_id)
            encoded[offset:offset + 32] = stream_id_bytes
            offset += 32

            if v.key is not None:
                key_size = self._encode_size24(len(v.key))
                encoded[offset:offset + len(key_size)] = key_size
                offset += len(key_size)
                encoded[offset:offset + len(v.key)] = v.key
                offset += len(v.key)

            if v.account is not None:
                account_bytes = self._hex_to_bytes(v.account)
                encoded[offset:offset + 20] = account_bytes
                offset += 20

        return bytes(encoded)
