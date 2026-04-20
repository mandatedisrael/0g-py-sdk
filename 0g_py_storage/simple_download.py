#!/usr/bin/env python3
"""
Minimal download script for 0G Storage (Testnet).

Usage:
    python3 simple_download.py <root_hash> [output_file]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer

# Mainnet Config (default)
INDEXER_URL = "https://indexer-storage-turbo.0g.ai"


def download(root_hash: str, output_file: str = "downloaded_file"):
    print(f"Downloading: {root_hash}")
    print(f"Output: {output_file}")

    indexer = Indexer(INDEXER_URL)

    # Download
    err = indexer.download(root_hash, output_file, proof=False)
    if err:
        print(f"Error: {err}")
        return False

    # Verify
    if os.path.exists(output_file):
        size = os.path.getsize(output_file)
        print(f"Success! Downloaded {size} bytes to {output_file}")
        return True

    print("Error: File not found after download")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 simple_download.py <root_hash> [output_file]")
        print("\nExample:")
        print("  python3 simple_download.py 0x1234...abcd output.txt")
        sys.exit(1)

    root_hash = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "downloaded_file"

    success = download(root_hash, output_file)
    sys.exit(0 if success else 1)
