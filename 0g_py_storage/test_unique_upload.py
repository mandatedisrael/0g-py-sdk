#!/usr/bin/env python3
"""Upload a unique file with timestamp to test shard upload"""
import sys
import os
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer import Indexer
from core.file import ZgFile
from eth_account import Account

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL", "https://evmrpc-testnet.0g.ai")
INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"

if not PRIVATE_KEY:
    print("❌ ERROR: PRIVATE_KEY not found!")
    sys.exit(1)

# Create account
if PRIVATE_KEY.startswith("0x"):
    account = Account.from_key(PRIVATE_KEY)
else:
    account = Account.from_key("0x" + PRIVATE_KEY)

print(f"\n✅ Account: {account.address}")

# Create UNIQUE test file with timestamp and UUID
unique_id = str(uuid.uuid4())
timestamp = time.time()
test_file = f"./devName.txt"

# Create file object
file = ZgFile.from_file_path(test_file)

# Upload
print(f"\n📤 Uploading to 0G Storage...")
indexer = Indexer(INDEXER_URL)

upload_opts = {
    'tags': b'\x00',
    'finalityRequired': False,  # Don't wait for finality to speed up test
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

    tx_hash = result['txHash']
    root_hash = result['rootHash']

    if not tx_hash.startswith('0x'):
        tx_hash = f"0x{tx_hash}"

    print(f"\n✅ Upload successful!")
    print(f"   TX: {tx_hash}")
    print(f"   Root: {root_hash}")

    # Check which shards have the file
    print(f"\n🔍 Checking upload status across shards...")
    time.sleep(5)  # Wait a bit for propagation

    from core.storage_node import StorageNode
    sharded = indexer.get_sharded_nodes()
    nodes = sharded.get('trusted', [])

    shard_0_count = 0
    shard_1_count = 0

    for node in nodes:
        try:
            sn = StorageNode(node['url'])
            info = sn.get_file_info(root_hash, True)
            if info:
                shard_id = node['config']['shardId']
                uploaded = info.get('uploadedSegNum', 0)
                if shard_id == 0:
                    shard_0_count += uploaded
                else:
                    shard_1_count += uploaded
                print(f"   {node['url']}: shard {shard_id}, uploaded {uploaded} segments")
        except:
            pass

    print(f"\n📊 Summary:")
    print(f"   Shard 0 total segments: {shard_0_count}")
    print(f"   Shard 1 total segments: {shard_1_count}")

    if shard_0_count > 0 and shard_1_count == 0:
        print(f"   ✅ Correctly uploaded to shard 0 only!")
    elif shard_0_count == 0 and shard_1_count > 0:
        print(f"   ❌ ERROR: Uploaded to shard 1 instead of shard 0!")
    elif shard_0_count > 0 and shard_1_count > 0:
        print(f"   ⚠️  Uploaded to both shards (unexpected for 1-segment file)")
    else:
        print(f"   ❌ No uploads detected on any shard!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    file.close()
    if os.path.exists(test_file):
        os.remove(test_file)
