"""
Test file operations.

Tests ZgFile functionality matching TypeScript SDK behavior.
"""
import pytest
import os
import tempfile
from core.file import ZgFile, AbstractFile
from config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_SIZE


class TestAbstractFile:
    """Test AbstractFile static methods."""

    def test_segment_root_single_chunk(self):
        """Test segment root with single chunk."""
        # Create a chunk of data
        data = b"hello world" + b"\x00" * (DEFAULT_CHUNK_SIZE - 11)
        root = AbstractFile.segment_root(data)

        assert root is not None
        assert root.startswith("0x")
        assert len(root) == 66  # 0x + 64 hex chars

    def test_segment_root_multiple_chunks(self):
        """Test segment root with multiple chunks."""
        # Create 3 chunks of data
        data = b"X" * (DEFAULT_CHUNK_SIZE * 3)
        root = AbstractFile.segment_root(data)

        assert root is not None
        assert root.startswith("0x")

    def test_segment_root_with_padding(self):
        """Test segment root with empty chunk padding."""
        data = b"test data"
        root = AbstractFile.segment_root(data, empty_chunks_padded=2)

        assert root is not None
        assert root.startswith("0x")


class TestZgFileFromBytes:
    """Test ZgFile with in-memory bytes data."""

    def test_from_bytes_small(self):
        """Test creating ZgFile from small bytes."""
        data = b"Hello, 0G Storage!"
        file = ZgFile.from_bytes(data)

        assert file.size() == len(data)
        file.close()

    def test_from_bytes_merkle_tree(self):
        """Test merkle tree generation from bytes."""
        data = b"Test data for merkle tree generation"
        file = ZgFile.from_bytes(data)

        tree, err = file.merkle_tree()

        assert err is None
        assert tree is not None
        assert tree.root_hash() is not None
        print(f"Bytes merkle root: {tree.root_hash()}")
        file.close()

    def test_from_bytes_large(self):
        """Test with data larger than one segment."""
        # Create data larger than DEFAULT_SEGMENT_SIZE
        data = b"X" * (DEFAULT_SEGMENT_SIZE + 1000)
        file = ZgFile.from_bytes(data)

        assert file.size() == len(data)

        tree, err = file.merkle_tree()
        assert err is None
        assert tree is not None

        file.close()

    def test_num_chunks(self):
        """Test chunk calculation."""
        data = b"X" * 1000
        file = ZgFile.from_bytes(data)

        num_chunks = file.num_chunks()
        # 1000 bytes / 256 bytes per chunk = 4 chunks (rounded up)
        assert num_chunks == 4

        file.close()

    def test_num_segments(self):
        """Test segment calculation."""
        # Create data that's exactly 2 segments
        data = b"X" * (DEFAULT_SEGMENT_SIZE * 2)
        file = ZgFile.from_bytes(data)

        num_segments = file.num_segments()
        assert num_segments == 2

        file.close()

    def test_create_submission(self):
        """Test creating submission structure."""
        data = b"Test data for submission"
        file = ZgFile.from_bytes(data)

        tags = b"\x00\x01\x02"
        submission, err = file.create_submission(tags)

        assert err is None
        assert submission is not None
        assert submission['length'] == len(data)
        assert submission['tags'] == tags
        assert 'nodes' in submission
        assert len(submission['nodes']) > 0

        # Check node structure
        for node in submission['nodes']:
            assert 'root' in node
            assert 'height' in node
            assert node['root'].startswith('0x')

        file.close()

    def test_split_nodes(self):
        """Test node splitting logic."""
        # Small file
        data = b"X" * 1000
        file = ZgFile.from_bytes(data)

        nodes = file.split_nodes()
        assert len(nodes) > 0
        assert all(isinstance(n, int) for n in nodes)

        file.close()

    def test_deterministic_merkle(self):
        """Test that same data produces same merkle root."""
        data = b"Deterministic test data"

        file1 = ZgFile.from_bytes(data)
        tree1, _ = file1.merkle_tree()
        root1 = tree1.root_hash()
        file1.close()

        file2 = ZgFile.from_bytes(data)
        tree2, _ = file2.merkle_tree()
        root2 = tree2.root_hash()
        file2.close()

        assert root1 == root2


class TestZgFileFromPath:
    """Test ZgFile with actual files."""

    def test_from_file_path(self):
        """Test creating ZgFile from file path."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            test_data = b"Hello from file system!"
            f.write(test_data)
            temp_path = f.name

        try:
            file = ZgFile.from_file_path(temp_path)
            assert file.size() == len(test_data)
            file.close()
        finally:
            os.unlink(temp_path)

    def test_from_file_path_merkle_tree(self):
        """Test merkle tree from file."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            test_data = b"Test file for merkle tree\n" * 100
            f.write(test_data)
            temp_path = f.name

        try:
            file = ZgFile.from_file_path(temp_path)
            tree, err = file.merkle_tree()

            assert err is None
            assert tree is not None
            assert tree.root_hash() is not None
            print(f"File merkle root: {tree.root_hash()}")

            file.close()
        finally:
            os.unlink(temp_path)

    def test_from_file_path_large(self):
        """Test with larger file."""
        # Create file larger than one segment
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            # Write multiple segments worth of data
            chunk_data = b"Large file test data\n" * 1000
            for _ in range(10):
                f.write(chunk_data)
            temp_path = f.name

        try:
            file = ZgFile.from_file_path(temp_path)
            size = file.size()

            tree, err = file.merkle_tree()
            assert err is None
            assert tree is not None

            print(f"Large file size: {size} bytes")
            print(f"Large file merkle root: {tree.root_hash()}")

            file.close()
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            ZgFile.from_file_path("/nonexistent/path/to/file.txt")

    def test_create_submission_from_file(self):
        """Test creating submission from file."""
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            test_data = b"Submission test data"
            f.write(test_data)
            temp_path = f.name

        try:
            file = ZgFile.from_file_path(temp_path)

            tags = b"\x00"
            submission, err = file.create_submission(tags)

            assert err is None
            assert submission is not None
            assert submission['length'] == len(test_data)

            file.close()
        finally:
            os.unlink(temp_path)


class TestIterator:
    """Test file iteration."""

    def test_iterate_small_file(self):
        """Test iterating over small file."""
        data = b"Small iteration test"
        file = ZgFile.from_bytes(data)

        iterator = file.iterate(flow_padding=True)

        ok, err = iterator.next()
        assert err is None
        assert ok is True

        current = iterator.current()
        assert len(current) > 0

        file.close()

    def test_iterate_multiple_segments(self):
        """Test iterating over multiple segments."""
        # Create data spanning multiple segments
        data = b"X" * (DEFAULT_SEGMENT_SIZE * 2 + 1000)
        file = ZgFile.from_bytes(data)

        iterator = file.iterate(flow_padding=True)

        segment_count = 0
        while True:
            ok, err = iterator.next()
            assert err is None

            if not ok:
                break

            current = iterator.current()
            assert len(current) > 0
            segment_count += 1

        assert segment_count >= 2

        file.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
