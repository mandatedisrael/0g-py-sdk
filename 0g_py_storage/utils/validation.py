"""
Input validation utilities.
"""
import os


def validate_file_path(path: str) -> bool:
    """Check if file path exists and is readable."""
    return os.path.isfile(path) and os.access(path, os.R_OK)


def validate_root_hash(root_hash: str) -> bool:
    """Check if root hash is valid hex string."""
    if not root_hash:
        return False

    # Remove 0x prefix if present
    if root_hash.startswith('0x'):
        root_hash = root_hash[2:]

    # Check if valid hex and reasonable length
    try:
        int(root_hash, 16)
        return len(root_hash) == 64  # 32 bytes = 64 hex chars
    except ValueError:
        return False


def validate_replicas(replicas: int) -> bool:
    """Check if replica count is valid."""
    return replicas >= 1
