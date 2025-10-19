#!/usr/bin/env python3
"""
Simple Upload Test for 0G Storage Python SDK

This script uploads a file to 0G Storage and displays the transaction details.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer
from core.file import ZgFile
from eth_account import Account

# ============================================================================
# Load Configuration from .env
# ============================================================================

def load_env():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL", "https://evmrpc-testnet.0g.ai")
INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"

if not PRIVATE_KEY:
    print("❌ ERROR: PRIVATE_KEY not found in .env file!")
    print("Please create a .env file with your PRIVATE_KEY")
    sys.exit(1)

# ============================================================================
# Upload File
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  0G STORAGE - SIMPLE UPLOAD TEST")
    print("="*70)

    # Create account
    try:
        if PRIVATE_KEY.startswith("0x"):
            account = Account.from_key(PRIVATE_KEY)
        else:
            account = Account.from_key("0x" + PRIVATE_KEY)
        print(f"\n✅ Account: {account.address}")
    except Exception as e:
        print(f"❌ ERROR: Invalid private key: {e}")
        sys.exit(1)

    # Create test file
    print(f"\n📝 Creating test file...")
    test_file = "./notmartin.txt"
    test_content = f"""
0G Storage Upload Test
======================

Timestamp: {time.time()}
Account: {account.address}

This file was uploaded to 0G Storage using the Python SDK.
""".encode()

    with open(test_file, 'wb') as f:
        f.write(test_content)

    print(f"   File: {test_file}")
    print(f"   Size: {len(test_content)} bytes")

    # Create file object
    file = ZgFile.from_file_path(test_file)

    # Upload to 0G Storage
    print(f"\n📤 Uploading to 0G Storage...")
    print(f"   Network: {RPC_URL}")
    print(f"   Indexer: {INDEXER_URL}")

    indexer = Indexer(INDEXER_URL)

    upload_opts = {
        'tags': b'\x00',
        'finalityRequired': True,
        'taskSize': 10,
        'expectedReplica': 1,
        'skipTx': False,
        'account': account,
    }

    try:
        result, err = indexer.upload(
            file,
            RPC_URL,
            account,
            upload_opts
        )

        if err is not None:
            print(f"\n❌ Upload failed: {err}")
            file.close()
            os.remove(test_file)
            sys.exit(1)

        # Success!
        tx_hash = result['txHash']
        root_hash = result['rootHash']

        # Ensure transaction hash has 0x prefix
        if not tx_hash.startswith('0x'):
            tx_hash = f"0x{tx_hash}"

        print(f"\n" + "="*70)
        print("  ✅ UPLOAD SUCCESSFUL!")
        print("="*70)
        print(f"\n📋 Transaction Details:")
        print(f"   Transaction Hash: {tx_hash}")
        print(f"   Root Hash:        {root_hash}")
        print(f"   File Size:        {file.size()} bytes")
        print(f"   Chunks:           {file.num_chunks()}")
        print(f"   Segments:         {file.num_segments()}")

        print(f"\n🔗 View on Explorer:")
        print(f"   https://chainscan-galileo.0g.ai/tx/{tx_hash}")

        print(f"\n💡 To download this file, use:")
        print(f"   python test_download.py {root_hash}")

        print(f"\n⏰ Note: Wait 3-5 minutes for file to propagate before downloading")

        # Save root hash to file for easy download testing
        with open('.last_upload_root.txt', 'w') as f:
            f.write(result['rootHash'])

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        file.close()
        os.remove(test_file)
        sys.exit(1)

    # Cleanup
    file.close()
    os.remove(test_file)

    print(f"\n✅ Test complete!\n")

if __name__ == "__main__":
    main()
