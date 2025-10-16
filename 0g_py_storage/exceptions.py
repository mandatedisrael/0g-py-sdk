"""
Exceptions for 0G Storage SDK.
"""


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class UploadError(StorageError):
    """Failed to upload file."""
    pass


class DownloadError(StorageError):
    """Failed to download file."""
    pass


class VerificationError(StorageError):
    """Failed to verify merkle proof."""
    pass


class NodeUnavailableError(StorageError):
    """Storage node is unavailable."""
    pass


class InsufficientReplicasError(StorageError):
    """Not enough storage nodes available."""
    pass


class MerkleTreeError(StorageError):
    """Failed to compute merkle tree."""
    pass


class ContractError(StorageError):
    """Smart contract interaction failed."""
    pass
