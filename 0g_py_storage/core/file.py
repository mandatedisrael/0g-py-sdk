"""
File operations for 0G Storage.

Ported from official TypeScript SDK:
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/file/AbstractFile.js
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/file/ZgFile.js
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/file/Iterator/*.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import Optional, Tuple, List, Dict, Any
from abc import ABC, abstractmethod
import os
import math

try:
    from .merkle import MerkleTree
    from ..config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_SEGMENT_SIZE,
        DEFAULT_SEGMENT_MAX_CHUNKS,
        EMPTY_CHUNK_HASH,
        ZERO_HASH
    )
    from ..utils.file_utils import num_splits, compute_padded_size
except ImportError:
    from core.merkle import MerkleTree
    from config import (
        DEFAULT_CHUNK_SIZE,
        DEFAULT_SEGMENT_SIZE,
        DEFAULT_SEGMENT_MAX_CHUNKS,
        EMPTY_CHUNK_HASH,
        ZERO_HASH
    )
    from utils.file_utils import num_splits, compute_padded_size


# ============================================================================
# ITERATORS (Ported from Iterator/*.js)
# ============================================================================

class FileIterator(ABC):
    """
    Base iterator for file data.

    Ported from BlobIterator.js and MemIterator.js base behavior.
    """

    def __init__(
        self,
        file_size: int,
        offset: int,
        batch: int,
        flow_padding: bool
    ):
        """
        Initialize iterator.

        TS SDK BlobIterator constructor (lines 14-34).

        Args:
            file_size: Size of file in bytes
            offset: Starting offset
            batch: Batch size (must align with chunk size)
            flow_padding: Whether to add flow padding

        Raises:
            ValueError: If batch size doesn't align with chunk size
        """
        # TS line 15-17
        if batch % DEFAULT_CHUNK_SIZE > 0:
            raise ValueError("batch size should align with chunk size")

        # TS line 18-27
        self.buf = bytearray(batch)
        chunks = num_splits(file_size, DEFAULT_CHUNK_SIZE)

        if flow_padding:
            padded_chunks, _ = compute_padded_size(chunks)
            padded_size = padded_chunks * DEFAULT_CHUNK_SIZE
        else:
            padded_size = chunks * DEFAULT_CHUNK_SIZE

        # TS line 28-33
        self.buf_size = 0  # buffer content size
        self.file_size = file_size
        self.padded_size = padded_size  # total size including padding zeros
        self.batch_size = batch
        self.offset = offset

    @abstractmethod
    def read_from_file(self, start: int, end: int) -> Tuple[int, bytes]:
        """
        Read data from file/memory.

        Returns (bytes_read, buffer).
        """
        pass

    def clear_buffer(self):
        """
        Clear buffer.

        TS SDK line 53-54.
        """
        self.buf_size = 0

    def padding_zeros(self, length: int):
        """
        Pad buffer with zeros.

        TS SDK lines 56-61.
        """
        start_offset = self.buf_size
        # Fill with zeros
        for i in range(start_offset, start_offset + length):
            self.buf[i] = 0
        self.buf_size += length
        self.offset += length

    def next(self) -> Tuple[bool, Optional[Exception]]:
        """
        Read next batch.

        TS SDK lines 62-95.

        Returns:
            Tuple of (ok, error) where ok indicates if data was read
        """
        # TS line 63-64
        if self.offset < 0 or self.offset >= self.padded_size:
            return (False, None)

        # TS line 66-73
        max_available_length = self.padded_size - self.offset  # include padding zeros
        if max_available_length >= self.batch_size:
            expected_buf_size = self.batch_size
        else:
            expected_buf_size = max_available_length

        # TS line 74
        self.clear_buffer()

        # TS line 75-78
        if self.offset >= self.file_size:
            self.padding_zeros(expected_buf_size)
            return (True, None)

        # TS line 79-82
        try:
            n, buffer = self.read_from_file(self.offset, self.offset + self.batch_size)
            self.buf = bytearray(buffer)
            self.buf_size = n
            self.offset += n
        except Exception as e:
            return (False, e)

        # TS line 84-85
        if n == expected_buf_size:
            return (True, None)

        # TS line 87-90
        if n > expected_buf_size:
            raise Exception("load more data from file than expected")

        # TS line 91-93
        if expected_buf_size > n:
            self.padding_zeros(expected_buf_size - n)

        return (True, None)

    def current(self) -> bytes:
        """
        Get current buffer data.

        TS SDK lines 96-98.
        """
        return bytes(self.buf[0:self.buf_size])


class MemIterator(FileIterator):
    """
    Iterator for in-memory data (bytes).

    Ported from MemIterator.js (lines 1-98).
    """

    def __init__(
        self,
        data: bytes,
        file_size: int,
        offset: int,
        batch: int,
        flow_padding: bool
    ):
        """
        Initialize memory iterator.

        TS SDK MemIterator constructor (lines 14-34).
        """
        super().__init__(file_size, offset, batch, flow_padding)
        self.data_array = data  # TS line 28

    def read_from_file(self, start: int, end: int) -> Tuple[int, bytes]:
        """
        Read from memory buffer.

        TS SDK lines 35-49.
        """
        # TS line 36-38
        if start < 0 or start >= self.file_size:
            raise ValueError("invalid start offset")

        # TS line 39-41
        if end > self.file_size:
            end = self.file_size

        # TS line 42-47
        buf = self.data_array[start:end]
        buffer = bytearray(self.batch_size)
        buffer[0:len(buf)] = buf

        return (len(buf), bytes(buffer))


class FileFdIterator(FileIterator):
    """
    Iterator for file descriptor.

    Ported from NodeFdIterator.js (lines 1-29) and BlobIterator.js.
    """

    def __init__(
        self,
        fd,  # file object
        file_size: int,
        offset: int,
        batch: int,
        flow_padding: bool
    ):
        """
        Initialize file descriptor iterator.

        TS SDK NodeFdIterator constructor (lines 7-10).
        """
        super().__init__(file_size, offset, batch, flow_padding)
        self.fd = fd  # TS line 9

    def read_from_file(self, start: int, end: int) -> Tuple[int, bytes]:
        """
        Read from file descriptor.

        TS SDK NodeFdIterator.readFromFile (lines 12-26).
        """
        # TS line 13-14
        if start < 0 or start >= self.file_size:
            raise ValueError("invalid start offset")

        # TS line 15-18
        if end > self.file_size:
            end = self.file_size

        # TS line 19-25
        # Read from file at position
        self.fd.seek(start)
        data = self.fd.read(end - start)

        # Create buffer and copy data
        buffer = bytearray(self.batch_size)
        buffer[0:len(data)] = data

        return (len(data), bytes(buffer))


# ============================================================================
# ABSTRACT FILE (Ported from AbstractFile.js)
# ============================================================================

class AbstractFile(ABC):
    """
    Abstract base class for file operations.

    Ported from AbstractFile.js (lines 1-124).
    """

    def __init__(self):
        """Initialize abstract file."""
        self.file_size = 0  # TS line 8

    @staticmethod
    def segment_root(segment: bytes, empty_chunks_padded: int = 0) -> str:
        """
        Split a segment into chunks and compute the root hash.

        TS SDK lines 11-28.

        Args:
            segment: Segment data
            empty_chunks_padded: Number of empty chunks to pad

        Returns:
            Root hash as hex string
        """
        # TS line 12
        tree = MerkleTree()

        # TS line 13-17
        data_length = len(segment)
        for offset in range(0, data_length, DEFAULT_CHUNK_SIZE):
            chunk = segment[offset:offset + DEFAULT_CHUNK_SIZE]
            tree.add_leaf(chunk)

        # TS line 18-22
        if empty_chunks_padded > 0:
            for i in range(empty_chunks_padded):
                tree.add_leaf_by_hash(EMPTY_CHUNK_HASH)

        # TS line 23
        tree.build()

        # TS line 24-27
        if tree.root is not None:
            return tree.root_hash()

        return ZERO_HASH  # TODO check this

    def size(self) -> int:
        """
        Get file size.

        TS SDK lines 29-31.
        """
        return self.file_size

    def iterate(self, flow_padding: bool) -> FileIterator:
        """
        Create iterator with default segment size.

        TS SDK lines 32-34.
        """
        return self.iterate_with_offset_and_batch(0, DEFAULT_SEGMENT_SIZE, flow_padding)

    @abstractmethod
    def iterate_with_offset_and_batch(
        self,
        offset: int,
        batch: int,
        flow_padding: bool
    ) -> FileIterator:
        """
        Create iterator with custom offset and batch size.

        Must be implemented by subclasses.
        """
        pass

    def merkle_tree(self) -> Tuple[Optional[MerkleTree], Optional[Exception]]:
        """
        Generate merkle tree for file.

        TS SDK lines 35-51.

        Returns:
            Tuple of (tree, error)
        """
        # TS line 36
        iter = self.iterate(True)

        # TS line 37
        tree = MerkleTree()

        # TS line 38
        while True:
            # TS line 39-42
            ok, err = iter.next()
            if err is not None:
                return (None, err)

            # TS line 43-45
            if not ok:
                break

            # TS line 46-48
            current = iter.current()
            seg_root = AbstractFile.segment_root(current)
            tree.add_leaf_by_hash(seg_root)

        # TS line 50
        return (tree.build(), None)

    def num_chunks(self) -> int:
        """
        Calculate number of chunks.

        TS SDK lines 52-54.
        """
        return num_splits(self.size(), DEFAULT_CHUNK_SIZE)

    def num_segments(self) -> int:
        """
        Calculate number of segments.

        TS SDK lines 55-57.
        """
        return num_splits(self.size(), DEFAULT_SEGMENT_SIZE)

    def create_submission(self, tags: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """
        Create submission structure for contract.

        TS SDK lines 58-75.

        Args:
            tags: Additional metadata bytes

        Returns:
            Tuple of (submission, error)
        """
        # TS line 59-63
        submission = {
            'length': self.size(),
            'tags': tags,
            'nodes': [],
        }

        # TS line 64
        nodes = self.split_nodes()

        # TS line 65-66
        offset = 0
        for chunks in nodes:
            # TS line 67-70
            node, err = self.create_node(offset, chunks)
            if err is not None:
                return (None, err)

            # TS line 71-72
            submission['nodes'].append(node)
            offset += chunks * DEFAULT_CHUNK_SIZE

        # TS line 74
        return (submission, None)

    def split_nodes(self) -> List[int]:
        """
        Split file into nodes based on power-of-2 sizes.

        TS SDK lines 76-89.

        Returns:
            List of chunk counts for each node
        """
        # TS line 77
        nodes = []

        # TS line 78-79
        chunks = self.num_chunks()
        padded_chunks, chunks_next_pow2 = compute_padded_size(chunks)

        # TS line 80
        next_chunk_size = chunks_next_pow2

        # TS line 81
        while padded_chunks > 0:
            # TS line 82-85
            if padded_chunks >= next_chunk_size:
                padded_chunks -= next_chunk_size
                nodes.append(next_chunk_size)

            # TS line 86
            next_chunk_size //= 2

        # TS line 88
        return nodes

    def create_node(self, offset: int, chunks: int) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """
        Create a single merkle node.

        TS SDK lines 90-96.

        Args:
            offset: Starting offset
            chunks: Number of chunks

        Returns:
            Tuple of (node, error)
        """
        # TS line 91
        batch = chunks

        # TS line 92-94
        if chunks > DEFAULT_SEGMENT_MAX_CHUNKS:
            batch = DEFAULT_SEGMENT_MAX_CHUNKS

        # TS line 95
        return self.create_segment_node(
            offset,
            DEFAULT_CHUNK_SIZE * batch,
            DEFAULT_CHUNK_SIZE * chunks
        )

    def create_segment_node(
        self,
        offset: int,
        batch: int,
        size: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """
        Create node from segments.

        TS SDK lines 97-121.

        Args:
            offset: Starting offset
            batch: Batch size for iteration
            size: Total size to process

        Returns:
            Tuple of (node, error)
        """
        # TS line 98
        iter = self.iterate_with_offset_and_batch(offset, batch, True)

        # TS line 99
        tree = MerkleTree()

        # TS line 100
        i = 0
        while i < size:
            # TS line 101-104
            ok, err = iter.next()
            if err is not None:
                return (None, err)

            # TS line 105-107
            if not ok:
                break

            # TS line 108-111
            current = iter.current()
            seg_root = AbstractFile.segment_root(current)
            tree.add_leaf_by_hash(seg_root)
            i += len(current)

        # TS line 113
        tree.build()

        # TS line 114-119
        num_chunks = size // DEFAULT_CHUNK_SIZE
        height = math.log2(num_chunks)
        node = {
            'height': int(height),
            'root': tree.root_hash(),
        }

        # TS line 120
        return (node, None)


# ============================================================================
# ZG FILE (Ported from ZgFile.js)
# ============================================================================

class ZgFile(AbstractFile):
    """
    File implementation for file system paths.

    Ported from ZgFile.js (lines 1-32).
    """

    def __init__(self, fd, file_size: int):
        """
        Initialize ZgFile.

        TS SDK lines 10-14.

        Args:
            fd: File descriptor/object
            file_size: Size of file
        """
        super().__init__()
        self.fd = fd  # TS line 12
        self.file_size = file_size  # TS line 13

    @staticmethod
    def from_file_path(path: str) -> 'ZgFile':
        """
        Create ZgFile from file path.

        TS SDK lines 20-23.

        NOTE: need manually close fd after use

        Args:
            path: Path to file

        Returns:
            ZgFile instance

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        # TS line 21
        fd = open(path, 'rb')  # if fail, throw error

        # TS line 22 (stat to get size)
        file_size = os.path.getsize(path)

        return ZgFile(fd, file_size)

    @staticmethod
    def from_bytes(data: bytes, filename: str = "data") -> 'ZgFile':
        """
        Create ZgFile from bytes (memory).

        Extension for Python - uses MemIterator internally.

        Args:
            data: File data as bytes
            filename: Optional filename for reference

        Returns:
            ZgFile instance with bytes data
        """
        # Create a special marker for memory-based files
        class BytesFile:
            def __init__(self, data):
                self.data = data
                self.is_memory = True

        return ZgFile(BytesFile(data), len(data))

    def close(self):
        """
        Close file descriptor.

        TS SDK lines 24-26.
        """
        if hasattr(self.fd, 'close') and not hasattr(self.fd, 'is_memory'):
            self.fd.close()

    def iterate_with_offset_and_batch(
        self,
        offset: int,
        batch: int,
        flow_padding: bool
    ) -> FileIterator:
        """
        Create iterator for this file.

        TS SDK lines 27-29.

        Args:
            offset: Starting offset
            batch: Batch size
            flow_padding: Whether to add flow padding

        Returns:
            FileIterator instance
        """
        # Check if this is a memory-based file
        if hasattr(self.fd, 'is_memory'):
            return MemIterator(
                self.fd.data,
                self.size(),
                offset,
                batch,
                flow_padding
            )
        else:
            # TS line 28
            return FileFdIterator(
                self.fd,
                self.size(),
                offset,
                batch,
                flow_padding
            )
