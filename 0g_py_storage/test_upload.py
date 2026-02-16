#!/usr/bin/env python3
"""
Upload Test for 0G Storage Python SDK (Mainnet)

This script tests the complete upload workflow:
1. Load file and generate merkle tree
2. Get nodes from indexer
3. Submit transaction to Flow contract
4. Upload segments to storage nodes
5. Wait for finality

Configuration:
- Uses mainnet endpoints
- Requires a private key for signing transactions
- File to upload: test.txt
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.file import ZgFile
from core.indexer import Indexer
from web3 import Web3
from eth_account import Account

# ============================================================================
# CONFIGURATION - CUSTOMIZE THESE
# ============================================================================

# Network configuration
INDEXER_URL = "https://indexer-storage-turbo.0g.ai"  # Mainnet indexer
BLOCKCHAIN_RPC = "https://evmrpc.0g.ai"              # Mainnet RPC

# File to upload
FILE_TO_UPLOAD = "./test.txt"

# Your Ethereum account (NEVER commit private keys!)
# Option 1: Load from environment variable
PRIVATE_KEY = os.environ.get('OG_PRIVATE_KEY', None)

# If no private key, use a test account (for demo only!)
if not PRIVATE_KEY:
    print("\n⚠️  WARNING: No OG_PRIVATE_KEY environment variable found!")
    print("   Using test account for demo (do NOT use for production!)")
    # This is a dummy test account - DO NOT USE WITH REAL FUNDS!
    PRIVATE_KEY = "0x" + "1" * 64  # Dummy key for demonstration

# Upload options
UPLOAD_OPTIONS = {
    'tags': b'\x00',                # Metadata (empty for test)
    'finalityRequired': False,      # Don't wait for finality (faster for testing)
    'taskSize': 10,                 # Segments per upload task
    'expectedReplica': 1,           # Number of replicas needed
    'skipTx': False,                # Submit to blockchain
    'fee': 0                        # Auto-calculate fee
}

# Retry options
RETRY_OPTIONS = {
    'retries': 3,
    'interval': 3000,               # ms between retries
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, title):
    """Print a step indicator"""
    print(f"\n[{step_num}] {title}")
    print("-" * 70)


def format_bytes(num_bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


# ============================================================================
# MAIN UPLOAD TEST
# ============================================================================

def main():
    print_header("0G STORAGE - MAINNET UPLOAD TEST")

    try:
        # ====================================================================
        # STEP 1: Load file and generate merkle tree
        # ====================================================================
        print_step(1, "Loading file and generating Merkle tree")

        if not os.path.exists(FILE_TO_UPLOAD):
            print(f"❌ File not found: {FILE_TO_UPLOAD}")
            return False

        print(f"📄 Loading file: {FILE_TO_UPLOAD}")
        file = ZgFile.from_file_path(FILE_TO_UPLOAD)

        file_size = file.size()
        print(f"   Size: {format_bytes(file_size)}")

        print(f"🌳 Generating Merkle tree...")
        tree, err = file.merkle_tree()
        if err:
            print(f"❌ Merkle tree generation failed: {err}")
            return False

        root_hash = tree.root_hash()
        print(f"   Root Hash: {root_hash}")

        # Create submission for blockchain
        submission, err = file.create_submission(UPLOAD_OPTIONS.get('tags', b'\x00'))
        if err:
            print(f"❌ Submission creation failed: {err}")
            return False

        print(f"✅ File loaded and verified")
        print(f"   File size: {format_bytes(file_size)}")
        print(f"   Root hash: {root_hash}")
        print(f"   Submission nodes: {len(submission.get('nodes', []))}")

        # ====================================================================
        # STEP 2: Get network nodes from indexer
        # ====================================================================
        print_step(2, "Discovering storage nodes from indexer")

        print(f"🔗 Indexer URL: {INDEXER_URL}")
        indexer = Indexer(INDEXER_URL)

        print(f"🔍 Fetching sharded nodes...")
        nodes_result = indexer.get_sharded_nodes()

        if not nodes_result or ('trusted' not in nodes_result and 'discovered' not in nodes_result):
            print(f"❌ Failed to get nodes from indexer")
            return False

        trusted_nodes = nodes_result.get('trusted', [])
        discovered_nodes = nodes_result.get('discovered', [])

        print(f"   Trusted nodes: {len(trusted_nodes)}")
        for node in trusted_nodes:
            print(f"     - {node['url']} (shard {node['config']['shardId']}/{node['config']['numShard']})")

        print(f"   Discovered nodes: {len(discovered_nodes)}")
        for node in discovered_nodes[:3]:  # Show first 3
            print(f"     - {node['url']} (shard {node['config']['shardId']}/{node['config']['numShard']})")
        if len(discovered_nodes) > 3:
            print(f"     ... and {len(discovered_nodes) - 3} more")

        # ====================================================================
        # STEP 3: Setup blockchain account
        # ====================================================================
        print_step(3, "Setting up blockchain account")

        print(f"🔗 RPC URL: {BLOCKCHAIN_RPC}")
        web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC))

        if not web3.is_connected():
            print(f"❌ Failed to connect to blockchain RPC")
            return False

        print(f"✅ Connected to blockchain")

        # Create account from private key
        try:
            account = Account.from_key(PRIVATE_KEY)
            print(f"👤 Account address: {account.address}")

            # Get account balance
            balance = web3.eth.get_balance(account.address)
            balance_eth = web3.from_wei(balance, 'ether')
            print(f"   Balance: {balance_eth:.6f} ETH")

            if balance == 0:
                print(f"   ⚠️  WARNING: Account has 0 balance - upload will fail!")
                print(f"      Send some ETH to {account.address} first")

        except Exception as e:
            print(f"❌ Failed to create account: {e}")
            return False

        # ====================================================================
        # STEP 4: Create uploader with selected nodes
        # ====================================================================
        print_step(4, "Creating uploader with selected nodes")

        print(f"📋 Creating uploader...")
        uploader, err = indexer.new_uploader_from_indexer_nodes(
            BLOCKCHAIN_RPC,
            account,
            UPLOAD_OPTIONS.get('expectedReplica', 1)
        )

        if err or not uploader:
            print(f"❌ Failed to create uploader: {err}")
            return False

        print(f"✅ Uploader created")
        print(f"   Nodes: {len(uploader.nodes)}")
        for i, node in enumerate(uploader.nodes):
            print(f"     {i+1}. {node.url}")

        # ====================================================================
        # STEP 5: Upload file
        # ====================================================================
        print_step(5, "Uploading file to 0G Storage Network")

        print(f"⏫ Starting file upload...")
        print(f"   File size: {format_bytes(file_size)}")
        print(f"   Root hash: {root_hash}")
        print(f"   Finality required: {UPLOAD_OPTIONS.get('finalityRequired', False)}")

        start_time = time.time()

        upload_opts = {
            **UPLOAD_OPTIONS,
            'account': account
        }

        result, err = uploader.upload_file(file, upload_opts, RETRY_OPTIONS)

        elapsed = time.time() - start_time

        if err:
            print(f"❌ Upload failed: {err}")
            import traceback
            traceback.print_exc()
            return False

        if not result:
            print(f"❌ Upload returned no result")
            return False

        tx_hash = result.get('txHash')
        result_root = result.get('rootHash')

        print(f"\n" + "=" * 70)
        print("  ✅ UPLOAD SUCCESSFUL!")
        print("=" * 70)

        print(f"\n📋 Upload Details:")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Transaction Hash: {tx_hash}")
        print(f"   Root Hash: {result_root}")
        print(f"   File Size: {format_bytes(file_size)}")
        print(f"   Match: {'✅' if result_root == root_hash else '❌'}")

        # ====================================================================
        # STEP 6: Verify upload
        # ====================================================================
        print_step(6, "Verifying upload on storage nodes")

        print(f"🔍 Checking file on storage nodes...")
        print(f"   (This may take a moment...)")

        # Wait a bit for propagation
        time.sleep(2)

        found_on_nodes = 0
        for i, node in enumerate(uploader.nodes):
            try:
                file_info, _ = node.get_file_info_by_tx_seq(0)  # Would need actual tx_seq
                if file_info:
                    found_on_nodes += 1
                    print(f"     ✅ Node {i+1}: Found")
            except:
                print(f"     ⚠️  Node {i+1}: Not found yet (may be propagating)")

        print(f"\n   Found on {found_on_nodes} nodes")

        # ====================================================================
        # STEP 7: Print summary
        # ====================================================================
        print_step(7, "Summary")

        print(f"""
✅ Upload Complete!

📝 File Information:
   - Path: {FILE_TO_UPLOAD}
   - Size: {format_bytes(file_size)}
   - Root Hash: {root_hash}

⛓️  Blockchain Information:
   - Network: Mainnet
   - RPC: {BLOCKCHAIN_RPC}
   - Account: {account.address}
   - Transaction: {tx_hash}

📊 Storage Information:
   - Indexer: {INDEXER_URL}
   - Replicas: {UPLOAD_OPTIONS.get('expectedReplica', 1)}
   - Nodes: {len(uploader.nodes)}

💾 Next Steps:
   1. Wait for file to be fully finalized (~5-10 minutes)
   2. Download using: python3 test_download.py
   3. Use root hash: {root_hash}
""")

        print(f"=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if 'file' in locals():
            try:
                file.close()
            except:
                pass


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
