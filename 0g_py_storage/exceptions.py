"""
Exceptions for 0G Storage SDK.

Enhanced error handling with context, error codes, and retry information.
All new features are backward compatible with existing exception handling.
"""
from typing import Optional, Dict, Any


class StorageError(Exception):
    """
    Base exception for storage operations.

    Enhanced with error code and context information while remaining
    backward compatible with existing exception handling.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize StorageError.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (optional)
            context: Additional context dict (optional)
            cause: Original exception that caused this error (optional)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return detailed error string."""
        base = self.message
        if self.error_code:
            base = f"[{self.error_code}] {base}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base = f"{base} ({context_str})"
        return base

    def with_context(self, **kwargs) -> 'StorageError':
        """Add context to error and return self for chaining."""
        self.context.update(kwargs)
        return self


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


# Additional specialized error classes with better context

class NetworkError(StorageError):
    """Network communication failed."""
    pass


class TimeoutError(StorageError):
    """Operation timed out."""
    pass


class RetryableError(StorageError):
    """Error that can be retried."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: Optional[int] = None
    ):
        """
        Initialize RetryableError.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (optional)
            context: Additional context dict (optional)
            cause: Original exception that caused this error (optional)
            retry_count: Number of times this has been retried
            max_retries: Maximum allowed retries (optional)
        """
        super().__init__(message, error_code, context, cause)
        self.retry_count = retry_count
        self.max_retries = max_retries

    def __str__(self) -> str:
        """Return detailed error string with retry info."""
        base = super().__str__()
        if self.max_retries is not None:
            base = f"{base} (retry {self.retry_count}/{self.max_retries})"
        else:
            base = f"{base} (retry {self.retry_count})"
        return base


class UploadRetryableError(UploadError, RetryableError):
    """Upload error that can be retried."""
    pass


class DownloadRetryableError(DownloadError, RetryableError):
    """Download error that can be retried."""
    pass


class NodeConnectionError(NodeUnavailableError, NetworkError):
    """Failed to connect to storage node."""
    pass


class TransactionError(ContractError):
    """Blockchain transaction failed."""

    def __init__(
        self,
        message: str,
        tx_hash: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize TransactionError.

        Args:
            message: Human-readable error message
            tx_hash: Transaction hash if available
            error_code: Machine-readable error code
            context: Additional context dict
            cause: Original exception
        """
        super().__init__(message, error_code, context, cause)
        self.tx_hash = tx_hash


class InvalidInputError(StorageError):
    """Invalid input parameters."""
    pass


class FileOperationError(StorageError):
    """File operation (read/write) failed."""
    pass
