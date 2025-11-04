# Enhanced Error Handling Guide

The 0G Storage Python SDK includes comprehensive error handling with context, error codes, and retry information. This guide shows how to use these features effectively.

## Quick Start

### Basic Error Handling (Backward Compatible)

The SDK continues to work with existing error handling patterns:

```python
from core.indexer import Indexer
from core.file import ZgFile

file = ZgFile.from_file_path("./data.txt")
indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")

# Old-style error handling still works
result, err = indexer.upload(file, rpc_url, account, upload_opts)
if err is not None:
    print(f"Upload failed: {err}")
```

## New Error Handling Features

### 1. Enhanced Exception Classes with Context

All `StorageError` exceptions now support error codes and context:

```python
from exceptions import UploadError

# Create error with context
error = UploadError(
    "Failed to upload file",
    error_code="UPLOAD_001",
    context={
        'file_size': 1024,
        'segment_count': 2,
        'node_url': 'http://node1.example.com'
    }
)

# Access error details
print(f"Code: {error.error_code}")
print(f"Context: {error.context}")
print(f"Message: {error.message}")

# Add more context dynamically
error.with_context(retry_count=3, timeout_ms=5000)
print(error)  # Detailed output with all context
```

### 2. Retryable Errors with Retry Tracking

Track retry attempts automatically:

```python
from exceptions import UploadRetryableError

error = UploadRetryableError(
    "Network error during upload",
    error_code="NETWORK_001",
    context={'node_url': 'http://node1.example.com'},
    retry_count=2,
    max_retries=5
)

print(error)  # "Network error... (retry 2/5)"

# Check if we should continue retrying
if error.retry_count < error.max_retries:
    print("Retrying...")
```

### 3. Error Context Manager

Use the error context manager for cleaner error handling:

```python
from utils.error_handler import ErrorContext

def upload_file(file_path, rpc_url, account):
    with ErrorContext("file_upload", verbose=True) as ctx:
        try:
            file = ZgFile.from_file_path(file_path)
            indexer = Indexer(rpc_url)
            result, err = indexer.upload(file, rpc_url, account, {})

            if err:
                ctx.add_error(err)
                raise err

            return result
        except Exception as e:
            ctx.add_error(e)
            ctx.raise_if_errors(f"Upload failed for {file_path}")
```

### 4. Error Handler Utilities

Convert exceptions to specific error types with context:

```python
from utils.error_handler import (
    handle_network_error,
    handle_upload_error,
    handle_timeout_error,
    handle_node_error,
    is_retryable
)

try:
    # Some operation
    pass
except ConnectionError as e:
    # Convert to NetworkError with context
    error = handle_network_error(
        e,
        operation="node_sync",
        node_url="http://node1.example.com"
    )
    print(error)  # Network error with full context

    # Check if retryable
    if is_retryable(error):
        print("Will retry...")
```

### 5. Input Validation

Validate user input with automatic error context:

```python
from utils.error_handler import validate_input

def process_file(root_hash):
    # Validate hex string
    validate_input(
        root_hash,
        "root_hash",
        lambda x: x.startswith("0x") and len(x) == 66,
        "valid 0x-prefixed 64-character hex string"
    )
    # If validation fails, raises InvalidInputError with context
```

### 6. Safe Function Calls

Call functions safely with error handling:

```python
from utils.error_handler import safe_call

# Call with default value on error
file_size = safe_call(
    lambda: get_file_info(root_hash)['size'],
    default=0
)

# Call with error callback
def on_error(e):
    logger.warning(f"Failed to get file size: {e}")

file_size = safe_call(
    lambda: get_file_info(root_hash)['size'],
    default=0,
    handle_error=on_error
)
```

### 7. Specific Error Types for Different Operations

Use specialized error handlers for different operations:

```python
from utils.error_handler import (
    handle_upload_error,
    handle_download_error,
    handle_transaction_error
)

# Upload errors
error = handle_upload_error(
    connection_error,
    file_size=1048576,
    segment_count=16,
    retry_count=1,
    max_retries=3
)

# Download errors
error = handle_download_error(
    timeout_error,
    root_hash="0x...",
    segment_index=5,
    retry_count=2,
    max_retries=5
)

# Transaction errors
error = handle_transaction_error(
    tx_failed,
    tx_hash="0x...",
    operation="submit_file"
)
```

### 8. Error Logging

Log errors with detailed context:

```python
from utils.error_handler import log_error_details
import logging

logger = logging.getLogger(__name__)

try:
    # Some operation
    pass
except Exception as e:
    log_error_details(
        e,
        operation="file_upload",
        level="error",
        logger_obj=logger
    )
```

## Error Hierarchy

```
StorageError (base)
├── UploadError
│   └── UploadRetryableError
├── DownloadError
│   └── DownloadRetryableError
├── VerificationError
├── NodeUnavailableError
│   └── NodeConnectionError
├── InsufficientReplicasError
├── MerkleTreeError
├── ContractError
│   └── TransactionError
├── NetworkError
│   └── NodeConnectionError (also inherits from NodeUnavailableError)
├── TimeoutError
├── InvalidInputError
└── FileOperationError
```

## Best Practices

### 1. Always Check for Errors

```python
result, err = indexer.upload(file, rpc_url, account, opts)
if err is not None:
    # Handle error
    log_error_details(err, "upload")
    if is_retryable(err):
        # Retry logic
        pass
```

### 2. Add Context to Errors

```python
try:
    # operation
except Exception as e:
    error = UploadError("Operation failed")
    error.with_context(
        file_size=size,
        node_count=len(nodes),
        timestamp=time.time()
    )
    raise error
```

### 3. Use Specific Error Types

```python
# Bad
raise Exception("Something went wrong")

# Good
raise UploadError(
    "Failed to upload segments",
    error_code="UPLOAD_SEGMENT_FAILED",
    context={'segment_count': 5}
)
```

### 4. Chain Context Information

```python
error = UploadError("Upload failed")
error.with_context(attempt=1).with_context(timeout=30000)
print(error)  # Full context available
```

### 5. Log Before Raising

```python
try:
    # operation
except Exception as e:
    log_error_details(e, "critical_operation", level="error")
    raise handle_upload_error(e, retry_count=1, max_retries=3)
```

## Migration Guide

### From Old Style

```python
# Old
try:
    result = upload_file(...)
except Exception as e:
    print(f"Error: {e}")
```

### To New Style

```python
# New
from utils.error_handler import ErrorContext, log_error_details

with ErrorContext("upload_file") as ctx:
    try:
        result = upload_file(...)
    except Exception as e:
        log_error_details(e, "upload_file")
        ctx.add_error(e)
        ctx.raise_if_errors("Upload operation failed")
```

## Error Codes Reference

Common error codes used throughout the SDK:

- `NETWORK_ERROR`: Network communication failed
- `TIMEOUT`: Operation timed out
- `UPLOAD_ERROR`: File upload failed
- `DOWNLOAD_ERROR`: File download failed
- `NODE_CONNECTION_ERROR`: Node connection failed
- `TRANSACTION_ERROR`: Blockchain transaction failed
- `INVALID_INPUT`: Invalid input parameters
- `FILE_OPERATION_ERROR`: File read/write failed

## Backward Compatibility

All new error handling features are **fully backward compatible**:

- Existing code continues to work unchanged
- Old exception catching patterns still work
- New features are opt-in
- No breaking changes to existing APIs

## Complete Example

```python
from core.indexer import Indexer
from core.file import ZgFile
from utils.error_handler import (
    ErrorContext,
    handle_upload_error,
    is_retryable,
    log_error_details
)
from exceptions import UploadRetryableError
import time

def upload_with_retry(file_path, rpc_url, account, max_retries=3):
    """Upload file with comprehensive error handling."""

    with ErrorContext("upload_with_retry", verbose=False) as ctx:
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                file = ZgFile.from_file_path(file_path)
                indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")

                result, err = indexer.upload(
                    file,
                    rpc_url,
                    account,
                    {'taskSize': 10, 'expectedReplica': 1}
                )

                if err:
                    raise err

                print(f"✅ Upload successful: {result['txHash']}")
                return result

            except Exception as e:
                last_error = e
                log_error_details(e, f"upload (attempt {retry_count + 1}/{max_retries})")
                ctx.add_error(e)

                if not is_retryable(e):
                    print(f"❌ Non-retryable error: {e}")
                    raise

                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    print(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        # All retries exhausted
        error = handle_upload_error(
            last_error,
            retry_count=retry_count,
            max_retries=max_retries
        )
        ctx.raise_if_errors(f"Upload failed after {max_retries} retries")
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

with ErrorContext("operation", verbose=True) as ctx:
    # Detailed error information will be logged
    pass
```

### Inspect Error Context

```python
try:
    # operation
except Exception as e:
    if hasattr(e, 'context'):
        print(f"Error context: {e.context}")
    if hasattr(e, 'cause'):
        print(f"Caused by: {e.cause}")
```

### Check Retry Status

```python
if isinstance(error, UploadRetryableError):
    print(f"Attempt {error.retry_count}/{error.max_retries}")
    if error.retry_count >= error.max_retries:
        print("Max retries reached")
```

## Support

For issues with error handling:
1. Check the error code and context
2. Review the error hierarchy to understand the error type
3. Check if error is retryable with `is_retryable()`
4. Enable verbose logging for detailed information
5. File an issue with full error context
