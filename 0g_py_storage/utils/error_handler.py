"""
Error handling utilities for 0G Storage SDK.

Provides helper functions for better error handling, logging, and recovery.
"""
import traceback
import logging
from typing import Optional, Callable, Any, TypeVar, Tuple
from functools import wraps

try:
    from ..exceptions import (
        StorageError,
        RetryableError,
        NetworkError,
        TimeoutError as StorageTimeoutError,
        UploadRetryableError,
        DownloadRetryableError,
        NodeConnectionError,
        TransactionError,
        InvalidInputError,
        FileOperationError
    )
except ImportError:
    from exceptions import (
        StorageError,
        RetryableError,
        NetworkError,
        TimeoutError as StorageTimeoutError,
        UploadRetryableError,
        DownloadRetryableError,
        NodeConnectionError,
        TransactionError,
        InvalidInputError,
        FileOperationError
    )

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorContext:
    """Context manager for better error handling and logging."""

    def __init__(
        self,
        operation: str,
        verbose: bool = False,
        logger_obj: Optional[logging.Logger] = None
    ):
        """
        Initialize ErrorContext.

        Args:
            operation: Name of the operation (e.g., "upload", "download")
            verbose: Enable verbose logging
            logger_obj: Custom logger instance
        """
        self.operation = operation
        self.verbose = verbose
        self.logger = logger_obj or logger
        self.errors = []

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle errors."""
        if exc_type is not None:
            if issubclass(exc_type, StorageError):
                self.logger.error(f"Storage error in {self.operation}: {exc_val}")
            else:
                self.logger.error(
                    f"Unexpected error in {self.operation}: {exc_val}",
                    exc_info=self.verbose
                )
            self.errors.append(exc_val)

    def add_error(self, error: Exception) -> None:
        """Add an error to the context."""
        self.errors.append(error)
        self.logger.warning(f"Error in {self.operation}: {error}")

    def raise_if_errors(self, message: Optional[str] = None) -> None:
        """Raise a combined error if any errors occurred."""
        if self.errors:
            error_msg = message or f"Multiple errors in {self.operation}"
            combined = StorageError(error_msg)
            combined.context['error_count'] = len(self.errors)
            combined.context['first_error'] = str(self.errors[0])
            raise combined

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0


def wrap_with_context(operation: str, verbose: bool = False):
    """
    Decorator to wrap function calls with error context.

    Args:
        operation: Name of the operation
        verbose: Enable verbose error logging

    Returns:
        Decorated function with error context
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorContext(operation, verbose) as ctx:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    ctx.add_error(e)
                    raise
        return wrapper
    return decorator


def handle_network_error(
    error: Exception,
    operation: str = "network operation",
    node_url: Optional[str] = None
) -> NetworkError:
    """
    Convert exception to NetworkError with context.

    Args:
        error: The original exception
        operation: Description of the operation
        node_url: URL of the node that failed

    Returns:
        NetworkError with context
    """
    context = {'operation': operation}
    if node_url:
        context['node_url'] = node_url

    return NetworkError(
        f"Network error during {operation}: {str(error)}",
        error_code="NETWORK_ERROR",
        context=context,
        cause=error
    )


def handle_timeout_error(
    operation: str = "operation",
    timeout_ms: int = 0,
    elapsed_ms: int = 0
) -> StorageTimeoutError:
    """
    Create a TimeoutError with context.

    Args:
        operation: Description of the operation
        timeout_ms: Timeout duration in milliseconds
        elapsed_ms: Time elapsed before timeout

    Returns:
        TimeoutError with context
    """
    context = {'operation': operation}
    if timeout_ms > 0:
        context['timeout_ms'] = timeout_ms
    if elapsed_ms > 0:
        context['elapsed_ms'] = elapsed_ms

    return StorageTimeoutError(
        f"{operation} timed out after {timeout_ms}ms",
        error_code="TIMEOUT",
        context=context
    )


def handle_upload_error(
    error: Exception,
    file_size: Optional[int] = None,
    segment_count: Optional[int] = None,
    retry_count: int = 0,
    max_retries: Optional[int] = None
) -> UploadRetryableError:
    """
    Convert exception to UploadRetryableError with context.

    Args:
        error: The original exception
        file_size: Size of file being uploaded
        segment_count: Number of segments
        retry_count: Current retry count
        max_retries: Maximum retries allowed

    Returns:
        UploadRetryableError with context
    """
    context = {}
    if file_size is not None:
        context['file_size'] = file_size
    if segment_count is not None:
        context['segment_count'] = segment_count

    return UploadRetryableError(
        f"Upload failed: {str(error)}",
        error_code="UPLOAD_ERROR",
        context=context,
        cause=error,
        retry_count=retry_count,
        max_retries=max_retries
    )


def handle_download_error(
    error: Exception,
    root_hash: Optional[str] = None,
    segment_index: Optional[int] = None,
    retry_count: int = 0,
    max_retries: Optional[int] = None
) -> DownloadRetryableError:
    """
    Convert exception to DownloadRetryableError with context.

    Args:
        error: The original exception
        root_hash: Root hash of file being downloaded
        segment_index: Index of segment being downloaded
        retry_count: Current retry count
        max_retries: Maximum retries allowed

    Returns:
        DownloadRetryableError with context
    """
    context = {}
    if root_hash:
        context['root_hash'] = root_hash
    if segment_index is not None:
        context['segment_index'] = segment_index

    return DownloadRetryableError(
        f"Download failed: {str(error)}",
        error_code="DOWNLOAD_ERROR",
        context=context,
        cause=error,
        retry_count=retry_count,
        max_retries=max_retries
    )


def handle_node_error(
    error: Exception,
    node_url: str,
    operation: str = "node operation"
) -> NodeConnectionError:
    """
    Convert exception to NodeConnectionError with context.

    Args:
        error: The original exception
        node_url: URL of the node
        operation: Description of the operation

    Returns:
        NodeConnectionError with context
    """
    return NodeConnectionError(
        f"Node connection error: {str(error)}",
        error_code="NODE_CONNECTION_ERROR",
        context={'node_url': node_url, 'operation': operation},
        cause=error
    )


def handle_transaction_error(
    error: Exception,
    tx_hash: Optional[str] = None,
    operation: str = "transaction"
) -> TransactionError:
    """
    Convert exception to TransactionError with context.

    Args:
        error: The original exception
        tx_hash: Transaction hash if available
        operation: Description of the operation

    Returns:
        TransactionError with context
    """
    return TransactionError(
        f"Transaction error: {str(error)}",
        tx_hash=tx_hash,
        error_code="TRANSACTION_ERROR",
        context={'operation': operation},
        cause=error
    )


def validate_input(
    value: Any,
    name: str,
    validator: Callable[[Any], bool],
    expected: str = "valid value"
) -> None:
    """
    Validate input and raise InvalidInputError if invalid.

    Args:
        value: Value to validate
        name: Name of the parameter
        validator: Callable that returns True if valid
        expected: Description of what's expected

    Raises:
        InvalidInputError: If validation fails
    """
    if not validator(value):
        raise InvalidInputError(
            f"Invalid value for {name}: expected {expected}",
            error_code="INVALID_INPUT",
            context={'parameter': name, 'value': str(value)}
        )


def is_retryable(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if error is retryable
    """
    if isinstance(error, RetryableError):
        return True
    if isinstance(error, NetworkError):
        return True
    if isinstance(error, StorageTimeoutError):
        return True

    error_str = str(error).lower()
    retryable_keywords = [
        'too many',
        'timeout',
        'connection',
        'unavailable',
        'busy',
        'retry',
        'temporary'
    ]
    return any(keyword in error_str for keyword in retryable_keywords)


def log_error_details(
    error: Exception,
    operation: str = "operation",
    level: str = "error",
    logger_obj: Optional[logging.Logger] = None
) -> None:
    """
    Log detailed error information.

    Args:
        error: The exception to log
        operation: Description of the operation
        level: Logging level (error, warning, info, debug)
        logger_obj: Custom logger instance
    """
    log_func = getattr(logger_obj or logger, level, logger.error)

    if isinstance(error, StorageError):
        log_func(
            f"{operation} failed: {error.message} "
            f"(code={error.error_code}, context={error.context})"
        )
        if error.cause:
            logger.debug(f"Caused by: {error.cause}")
    else:
        log_func(f"{operation} failed: {error}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")


def safe_call(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    handle_error: Optional[Callable[[Exception], None]] = None,
    **kwargs
) -> Optional[T]:
    """
    Safely call a function with error handling.

    Args:
        func: Function to call
        *args: Positional arguments
        default: Default value to return on error
        handle_error: Optional callback for error handling
        **kwargs: Keyword arguments

    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if handle_error:
            handle_error(e)
        logger.debug(f"Safe call failed: {e}")
        return default
