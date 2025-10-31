#!/usr/bin/env python3
"""
Download Test for 0G Storage Python SDK (Mainnet)

This script downloads the file we just uploaded to mainnet.
File Root Hash: 0x4454572265e0ae600d281a703df306ba7f62e447a9a5526f7f23bf2d4e99cd9d
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer

# Configuration for mainnet
INDEXER_URL = "https://indexer-storage-turbo.0g.ai"
ROOT_HASH = "0x4454572265e0ae600d281a703df306ba7f62e447a9a5526f7f23bf2d4e99cd9d"
OUTPUT_FILE = "./downloaded_file.txt"

def main():
    print("\n" + "="*70)
    print("  0G STORAGE - MAINNET DOWNLOAD TEST")
    print("="*70)

    print(f"\n📥 Downloading from 0G Storage...")
    print(f"   Indexer: {INDEXER_URL}")
    print(f"   Root Hash: {ROOT_HASH}")
    print(f"   Output File: {OUTPUT_FILE}")

    try:
        indexer = Indexer(INDEXER_URL)

        # Get file locations first
        print(f"\n🔍 Checking file locations...")
        locations = indexer.get_file_locations(ROOT_HASH)
        print(f"   Found {len(locations)} location(s):")
        for loc in locations:
            print(f"     - {loc}")

        # Download file
        print(f"\n⏬ Starting download...")
        start_time = time.time()
        err = indexer.download(ROOT_HASH, OUTPUT_FILE, proof=False)

        if err is not None:
            print(f"\n❌ Download failed: {err}")
            return False

        elapsed = time.time() - start_time

        # Verify download
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r') as f:
                content = f.read()

            print(f"\n" + "="*70)
            print("  ✅ DOWNLOAD SUCCESSFUL!")
            print("="*70)
            print(f"\n📋 File Details:")
            print(f"   File: {OUTPUT_FILE}")
            print(f"   Size: {len(content)} bytes")
            print(f"   Time: {elapsed:.2f}s")
            print(f"\n📄 Content:")
            print(f"   {content[:100]}..." if len(content) > 100 else f"   {content}")

            print(f"\n✅ Test complete!")
            return True
        else:
            print(f"\n❌ File not found after download")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
