import os
import sys

INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"
ROOT = os.environ.get("ROOT_HASH")  # set ROOT_HASH env var

if not ROOT:
    print("❌ Set ROOT_HASH env var before running (e.g., ROOT_HASH=0x...)")
    raise SystemExit(1)

# Ensure `0g_py_storage` is importable so `core.*` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.indexer import Indexer
from core.storage_node import StorageNode

idx = Indexer(INDEXER_URL)
sharded = idx.get_sharded_nodes()
nodes = [StorageNode(n['url']) for n in (sharded.get('trusted') or sharded.get('discovered') or [])]

for n in nodes:
    cfg = n.get_shard_config()
    info = n.get_file_info(ROOT, True)
    print(n.url, "cfg:", cfg, "finalized:", getattr(info, "get", lambda k, d=None: d)("finalized", False) if info else None, "uploadedSegNum:", info.get("uploadedSegNum", None) if info else None)