# API Integrations - 0G Storage Python SDK

The SDK integrates with multiple 0G network components via JSON-RPC APIs. Here's what's connected:

---

## 1. Indexer API

**File:** `core/indexer.py`

The Indexer provides information about storage nodes and file locations in the 0G network.

### Endpoints:
- **Testnet:** `https://indexer-storage-testnet-turbo.0g.ai`
- **Mainnet:** `https://indexer-storage-turbo.0g.ai`

### Available Methods:

#### `indexer_getShardedNodes()`
Gets list of sharded storage nodes with their configuration.
```python
indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")
nodes = indexer.get_sharded_nodes()
# Returns: {'trusted': [...], 'discovered': [...]}
```

**Response Structure:**
```python
{
    'trusted': [
        {
            'url': 'http://node1.example.com:5678',
            'config': {
                'numShard': 4,
                'shardId': 0
            }
        },
        ...
    ],
    'discovered': [...]
}
```

#### `indexer_getNodeLocations()`
Gets node location information (IP addresses, geographic info).

```python
locations = indexer.get_node_locations()
# Returns geographic/network location data
```

#### `indexer_getFileLocations(root_hash)`
Gets which storage nodes have a specific file.
```python
locations = indexer.get_file_locations("0x...")
# Returns: [{'url': 'http://node1:5678'}, ...]
```

#### `indexer_selectNodes(expected_replica)`
Selects optimal storage nodes for uploading with replication.
```python
nodes, err = indexer.select_nodes(expected_replica=2)
# Returns selected StorageNode instances
```

---

## 2. Storage Node API

**File:** `core/storage_node.py`

Each storage node provides methods for uploading and downloading data.

### Endpoint Format:
`http://<node-address>:5678`

### Available Methods (14 RPC calls):

#### Upload Operations:

**`zgs_uploadSegment(segment)`**
- Upload a single segment
- Parameter: Segment data structure
- Returns: Upload result/confirmation

**`zgs_uploadSegments(segments)`**
- Upload multiple segments in batch
- Parameter: Array of segment data
- Returns: Batch upload result

**`zgs_uploadSegmentByTxSeq(segment, tx_seq)`**
- Upload segment associated with a transaction
- Parameters: Segment data, transaction sequence number
- Returns: Upload confirmation with tx reference

**`zgs_uploadSegmentsByTxSeq(segments, tx_seq)`**
- Upload multiple segments for a transaction
- Parameters: Array of segments, transaction sequence
- Returns: Batch confirmation

#### Download Operations:

**`zgs_downloadSegment(root, start, end)`**
- Download specific byte range of a segment
- Parameters: Root hash, start byte, end byte
- Returns: Binary segment data

**`zgs_downloadSegmentWithProof(root, index)`**
- Download segment with merkle proof
- Parameters: Root hash, segment index
- Returns: Segment data + proof structure

#### Query Operations:

**`zgs_getStatus()`**
- Get node status (sync state, version, etc.)
- Returns: Node status information

**`zgs_getSyncProgress()`**
- Get node's sync progress
- Returns: Sync state (syncing/synced)

**`zgs_getFileInfo(root, need_available)`**
- Get file information
- Parameters: Root hash, flag for availability check
- Returns: File metadata (size, chunks, status)

**`zgs_getShardConfig()`**
- Get node's shard configuration
- Returns: Shard ID and count

**`zgs_getLogEntry(tx_seq)`**
- Get log entry by transaction sequence
- Parameter: Transaction sequence number
- Returns: Log entry data

**`zgs_getLogEntries(start_tx_seq, max_entries, max_size)`**
- Get multiple log entries
- Parameters: Start position, count, max size
- Returns: Array of log entries

**`zgs_getNodeFinalization()`**
- Get node finalization status
- Returns: Finalization state

---

## 3. Blockchain RPC API

**Files:** `contracts/flow.py`, `core/market.py`

Integrates with 0G blockchain for on-chain submissions and fee calculations.

### Endpoints:
- **Testnet:** `https://evmrpc-testnet.0g.ai`
- **Mainnet:** `https://evmrpc.0g.ai`

### Smart Contracts:

#### Flow Contract
- **Testnet:** `0x22e03a6a89b950f1c82ec5e74f8eca321a105296`
- **Mainnet:** `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526`
- **Chain ID (Testnet):** 16602
- **Chain ID (Mainnet):** 16661

**Methods:**

`submit(submission, account, value, gas_limit, gas_price)`
- Submit file metadata to blockchain
- Submits merkle tree and file info on-chain
- Calculates and sends storage fee
- Returns: Transaction receipt

```python
flow = FlowContract(web3, network="mainnet")
receipt = flow.submit(
    submission={
        'length': file_size,
        'tags': b'\x00',
        'nodes': [{'root': hash, 'height': h}, ...]
    },
    account=account,
    value=storage_fee_in_wei
)
print(f"TX: {receipt.transactionHash}")
```

#### Market Contract
**Purpose:** Determine current storage pricing

**Method:** `pricePerSector()`
- Returns: Current price in wei per sector
- Used to calculate storage fees

```python
from core.market import get_market_contract

market = get_market_contract(market_address, web3)
price_per_sector = market.functions.pricePerSector().call()
# Storage fee = file_size * price_per_sector
```

---

## 4. HTTP/JSON-RPC Layer

**File:** `utils/http.py`

Custom HTTP provider for JSON-RPC communication.

### Features:
- **TLS Support** - Enforces minimum TLS 1.2
- **Retry Logic** - Automatic retries with exponential backoff
- **Timeout Handling** - Configurable request timeouts (default: 30s)
- **Error Handling** - Proper JSON-RPC error detection
- **SSL/Cert Management** - Handles certificate verification

```python
from utils.http import HttpProvider

provider = HttpProvider(url, timeout=30)
result = provider.request(
    method='some_method',
    params=['param1', 'param2']
)
```

---

## Complete Integration Flow

### Upload Flow (Shows API Interactions):

```
1. User uploads file
   └─→ ZgFile.from_file_path()

2. Generate Merkle Tree
   └─→ file.merkle_tree()

3. Select Storage Nodes
   └─→ Indexer.get_sharded_nodes()  [Indexer API call #1]
   └─→ Indexer.select_nodes()        [Node selection logic]

4. Calculate Storage Fee
   └─→ Market.pricePerSector()       [Blockchain RPC call #1]
   └─→ fee_calculation(price × size)

5. Submit to Blockchain
   └─→ FlowContract.submit()         [Blockchain RPC call #2]
   └─→ Create transaction
   └─→ Wait for confirmation

6. Upload Segments to Nodes
   └─→ StorageNode.upload_segment()  [Storage Node API calls]
   └─→ StorageNode.uploadSegments()
   └─→ StorageNode.uploadSegmentByTxSeq()

7. Verify Upload
   └─→ Indexer.get_file_locations()  [Indexer API call #2]
   └─→ StorageNode.getFileInfo()     [Storage Node query]

8. Return Result
   └─→ {txHash, rootHash}
```

### Download Flow (Shows API Interactions):

```
1. User requests download
   └─→ indexer.download(root_hash)

2. Find File Locations
   └─→ Indexer.get_file_locations()  [Indexer API call]

3. Download from Nodes
   └─→ StorageNode.download_segment()     [Storage Node API]
   └─→ StorageNode.download_segment_with_proof()

4. Verify Merkle Proofs
   └─→ Validate proof against root hash

5. Reconstruct File
   └─→ Combine segments
   └─→ Verify file integrity

6. Write to Disk
   └─→ Return file or error
```

---

## API Usage Examples

### Example 1: List Available Storage Nodes

```python
from core.indexer import Indexer

indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")

# Get all sharded nodes
nodes = indexer.get_sharded_nodes()

print(f"Trusted nodes: {len(nodes['trusted'])}")
for node in nodes['trusted']:
    print(f"  - {node['url']}")
    print(f"    Shard: {node['config']['shardId']}/{node['config']['numShard']}")
```

### Example 2: Check Current Storage Pricing

```python
from web3 import Web3
from core.market import get_market_contract

web3 = Web3(Web3.HTTPProvider("https://evmrpc-testnet.0g.ai"))
market = get_market_contract("0x...", web3)

price = market.functions.pricePerSector().call()
print(f"Storage price: {price} wei per sector")

# Calculate fee for 1MB file
file_size_bytes = 1024 * 1024
fee_wei = file_size_bytes * price
fee_og = web3.from_wei(fee_wei, 'ether')
print(f"Upload cost: {fee_og} OG")
```

### Example 3: Query File Status

```python
from core.storage_node import StorageNode

node = StorageNode("http://node1.example.com:5678")

# Get file info
info = node.get_file_info("0x...")
if info:
    print(f"File size: {info['size']} bytes")
    print(f"Uploaded segments: {info['uploadedSegNum']}")
    print(f"Finalized: {info.get('finalized', False)}")

# Get node status
status = node.get_status()
print(f"Node version: {status['version']}")
print(f"Sync progress: {status['syncProgress']}")
```

### Example 4: Download with Proof Verification

```python
from core.downloader import Downloader
from core.indexer import Indexer

indexer = Indexer("https://indexer-storage-testnet-turbo.0g.ai")
downloader = Downloader(indexer, verify_proofs=True)

# Download and verify
error = downloader.download(
    root_hash="0x...",
    file_path="./output.txt",
    proof=True  # Verify merkle proofs
)

if error:
    print(f"Download failed: {error}")
else:
    print("Download successful and verified!")
```

---

## API Response Formats

### Indexer Response: get_sharded_nodes()

```json
{
  "trusted": [
    {
      "url": "http://192.168.1.100:5678",
      "config": {
        "numShard": 4,
        "shardId": 0
      },
      "latency": 45,
      "since": 1699000000
    }
  ],
  "discovered": [...]
}
```

### Storage Node Response: get_file_info()

```json
{
  "tx": {
    "seq": 12345,
    "startEntryIndex": 0,
    "size": 1048576,
    "tags": "0x00"
  },
  "finalized": true,
  "uploadedSegNum": 4
}
```

### Blockchain Response: transaction receipt

```json
{
  "transactionHash": "0x...",
  "blockNumber": 10998900,
  "gasUsed": 150000,
  "status": 1,
  "logs": [...]
}
```

---

## Error Handling for API Calls

All API calls can fail. The SDK includes enhanced error handling:

```python
from utils.error_handler import handle_network_error, is_retryable

try:
    result = indexer.get_sharded_nodes()
except Exception as e:
    # Convert to NetworkError with context
    error = handle_network_error(e, operation="get_nodes")

    # Check if retryable
    if is_retryable(error):
        print("Will retry...")
    else:
        print("Non-retryable error")
```

---

## Summary

| API | Endpoint | Methods | Purpose |
|-----|----------|---------|---------|
| **Indexer** | indexer-storage-turbo.0g.ai | 4+ | Node discovery & file location |
| **Storage Node** | node:5678 | 14 | Upload/download data |
| **Flow Contract** | evmrpc.0g.ai | submit() | On-chain file metadata |
| **Market Contract** | evmrpc.0g.ai | pricePerSector() | Calculate storage fees |
| **HTTP Provider** | Custom | request() | JSON-RPC transport layer |

All APIs are fully integrated and production-tested on mainnet.
