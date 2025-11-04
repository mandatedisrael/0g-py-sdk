"""Utility functions for 0G Storage SDK."""

try:
    from .error_handler import (
        ErrorContext,
        wrap_with_context,
        handle_network_error,
        handle_timeout_error,
        handle_upload_error,
        handle_download_error,
        handle_node_error,
        handle_transaction_error,
        validate_input,
        is_retryable,
        log_error_details,
        safe_call
    )
except ImportError:
    # Error handler utilities not available, but this is optional
    pass
