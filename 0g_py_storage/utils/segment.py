"""
Segment calculation utilities.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/utils.js
"""
import math
from ..config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS


def get_split_num(total: int, unit: int) -> int:
    """
    Calculate number of splits.

    Matches TS: Math.floor((total - 1) / unit + 1)
    """
    return math.floor((total - 1) / unit + 1)


def segment_range(start_chunk_index: int, file_size: int) -> tuple:
    """
    Calculate the start and end segment indices for a file.

    Args:
        start_chunk_index: The starting chunk index (integer)
        file_size: The file size (number of chunks, as an integer)

    Returns:
        Tuple of (start_segment_index, end_segment_index)

    Matches TS implementation:
    function SegmentRange(startChunkIndex, fileSize) {
        const totalChunks = GetSplitNum(fileSize, DEFAULT_CHUNK_SIZE);
        const startSegmentIndex = Math.floor(startChunkIndex / DEFAULT_SEGMENT_MAX_CHUNKS);
        const endChunkIndex = startChunkIndex + totalChunks - 1;
        const endSegmentIndex = Math.floor(endChunkIndex / DEFAULT_SEGMENT_MAX_CHUNKS);
        return [startSegmentIndex, endSegmentIndex];
    }
    """
    # Calculate total number of chunks for the file
    total_chunks = get_split_num(file_size, DEFAULT_CHUNK_SIZE)

    # Calculate the starting segment index
    start_segment_index = math.floor(start_chunk_index / DEFAULT_SEGMENT_MAX_CHUNKS)

    # Calculate the ending chunk index and then the segment index
    end_chunk_index = start_chunk_index + total_chunks - 1
    end_segment_index = math.floor(end_chunk_index / DEFAULT_SEGMENT_MAX_CHUNKS)

    return (start_segment_index, end_segment_index)
