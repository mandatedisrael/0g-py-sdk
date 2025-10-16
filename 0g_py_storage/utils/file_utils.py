"""
File utility functions.

Ported from official TypeScript SDK:
node_modules/@0glabs/0g-ts-sdk/lib.commonjs/file/utils.js
"""


def num_splits(total: int, unit: int) -> int:
    """
    Calculate number of splits needed.

    Matches TS: Math.floor((total - 1) / unit) + 1
    """
    return (total - 1) // unit + 1


def next_pow2(input: int) -> int:
    """
    Calculate next power of 2.

    Matches TS implementation exactly.
    """
    x = input
    x -= 1
    x |= x >> 32
    x |= x >> 16
    x |= x >> 8
    x |= x >> 4
    x |= x >> 2
    x |= x >> 1
    x += 1
    return x


def compute_padded_size(chunks: int) -> tuple:
    """
    Compute padded size for chunks.

    Returns (padded_chunks, chunks_next_pow2).

    Matches TS implementation:
    function computePaddedSize(chunks) {
        let chunksNextPow2 = nextPow2(chunks);
        if (chunksNextPow2 === chunks) {
            return [chunksNextPow2, chunksNextPow2];
        }
        let minChunk;
        if (chunksNextPow2 >= 16) {
            minChunk = Math.floor(chunksNextPow2 / 16);
        } else {
            minChunk = 1;
        }
        const paddedChunks = numSplits(chunks, minChunk) * minChunk;
        return [paddedChunks, chunksNextPow2];
    }
    """
    chunks_next_pow2 = next_pow2(chunks)

    if chunks_next_pow2 == chunks:
        return (chunks_next_pow2, chunks_next_pow2)

    if chunks_next_pow2 >= 16:
        min_chunk = chunks_next_pow2 // 16
    else:
        min_chunk = 1

    padded_chunks = num_splits(chunks, min_chunk) * min_chunk
    return (padded_chunks, chunks_next_pow2)
