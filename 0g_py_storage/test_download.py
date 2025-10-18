#!/usr/bin/env python3
"""
Simple Download Test for 0G Storage Python SDK

This script downloads a file from 0G Storage using its root hash.

Usage:
    python test_download.py <root_hash>
    python test_download.py  # Uses last uploaded file
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer

# ============================================================================
# Configuration
# ============================================================================

INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"

# ============================================================================
# Download File
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  0G STORAGE - SIMPLE DOWNLOAD TEST")
    print("="*70)

    # Get root hash from command line or last upload
    root_hash = None

    if len(sys.argv) > 1:
        root_hash = sys.argv[1]
        print(f"\n📥 Using root hash from command line")
    else:
        # Try to read from last upload
        last_upload_file = '.last_upload_root.txt'
        if os.path.exists(last_upload_file):
            with open(last_upload_file, 'r') as f:
                root_hash = f.read().strip()
            print(f"\n📥 Using root hash from last upload")
        else:
            print("\n❌ ERROR: No root hash provided!")
            print("\nUsage:")
            print("  python test_download.py <root_hash>")
            print("  python test_download.py  # Uses last uploaded file")
            print("\nExample:")
            print("  python test_download.py 0x11fdd3fd0a6e9594bf4ffe86a5cf095d85ac00f23b4f2e559802d624f6a86b58")
            sys.exit(1)

    print(f"   Root Hash: {root_hash}")

    # Download file
    download_path = "./downloaded_file.txt"

    # Remove old file if exists
    if os.path.exists(download_path):
        os.remove(download_path)

    print(f"\n📥 Downloading from 0G Storage...")
    print(f"   Indexer: {INDEXER_URL}")
    print(f"   Output:  {download_path}")

    indexer = Indexer(INDEXER_URL)

    try:
        err = indexer.download(root_hash, download_path, proof=False)

        if err is not None:
            print(f"\n❌ Download failed: {err}")
            print("\n💡 Possible reasons:")
            print("   - File not yet finalized (wait 3-5 minutes after upload)")
            print("   - Invalid root hash")
            print("   - Network connectivity issues")
            sys.exit(1)

        # Success!
        print(f"\n" + "="*70)
        print("  ✅ DOWNLOAD SUCCESSFUL!")
        print("="*70)

        # Show file info
        file_size = os.path.getsize(download_path)
        print(f"\n📊 File Information:")
        print(f"   Downloaded to: {download_path}")
        print(f"   File size:     {file_size} bytes")

        # Show content preview
        print(f"\n📄 Content Preview:")
        print("-" * 70)
        with open(download_path, 'rb') as f:
            content = f.read()
            # Show first 500 bytes
            preview = content[:500].decode('utf-8', errors='replace')
            print(preview)
            if len(content) > 500:
                print(f"\n... ({len(content) - 500} more bytes)")
        print("-" * 70)

        print(f"\n✅ Test complete!\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
