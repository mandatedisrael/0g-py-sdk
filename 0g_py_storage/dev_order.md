# 0G Storage Python SDK - Development Order

This document tracks the implementation progress of the 0G Storage Python SDK. Check off items as they are completed.

---

## **Phase 1: Foundation (No Dependencies)** ✅ COMPLETE

- [x] **`config.py`** - Constants, network configs, default values
  - Estimated time: 15 minutes
  - Dependencies: None
  - ✅ Ported from TS SDK constant.js

- [x] **`exceptions.py`** - All custom exceptions
  - Estimated time: 15 minutes
  - Dependencies: None
  - ✅ Complete

- [x] **`utils/validation.py`** - Input validation helpers
  - Estimated time: 30 minutes
  - Dependencies: None
  - ✅ Complete

- [x] **`utils/crypto.py`** - Hash functions (Keccak256, hex operations)
  - Estimated time: 30 minutes
  - Dependencies: None
  - ✅ Ported from @ethersproject/keccak256 & @ethersproject/bytes

- [x] **`utils/file_utils.py`** - File utility functions (BONUS)
  - ✅ Ported from TS SDK file/utils.js

- [x] **`utils/segment.py`** - Segment calculation utilities (BONUS)
  - ✅ Ported from TS SDK utils.js

---

## **Phase 2: Models (Depends on Foundation)**

- [ ] **`models/transaction.py`** - Transaction-related models
  - Estimated time: 20 minutes
  - Dependencies: None

- [ ] **`models/node.py`** - Node and storage models
  - Estimated time: 20 minutes
  - Dependencies: None

- [ ] **`models/file.py`** - File metadata and upload models
  - Estimated time: 30 minutes
  - Dependencies: None

---

## **Phase 3: Core Cryptography (Critical Path)**

- [ ] **`core/merkle.py`** - Merkle tree implementation ⚠️ **CRITICAL**
  - Estimated time: 3-4 hours
  - Dependencies: utils/crypto.py
  - Notes: MOST IMPORTANT - Must match 0G protocol exactly
  - **Write comprehensive tests immediately**

---

## **Phase 4: Smart Contracts**

- [ ] **`contracts/abis.py`** - Contract ABIs and addresses
  - Estimated time: 2 hours (research + implementation)
  - Dependencies: None
  - Notes: Research 0G Flow contract specs

- [ ] **`contracts/flow.py`** - Flow contract wrapper
  - Estimated time: 1 hour
  - Dependencies: contracts/abis.py, models/transaction.py

---

## **Phase 5: Core File Operations**

- [ ] **`core/file.py`** - ZgFile class
  - Estimated time: 1 hour
  - Dependencies: core/merkle.py, models/file.py, utils/validation.py

- [ ] **`utils/http.py`** - HTTP client helpers
  - Estimated time: 1 hour
  - Dependencies: None
  - Notes: For communicating with storage nodes

---

## **Phase 6: Network Layer**

- [ ] **`core/indexer.py`** - Indexer client
  - Estimated time: 2 hours
  - Dependencies: utils/http.py, models/node.py, exceptions.py

- [ ] **`core/node_selector.py`** - Node selection logic
  - Estimated time: 1 hour
  - Dependencies: core/indexer.py, models/node.py

---

## **Phase 7: Upload Path**

- [ ] **`core/uploader.py`** - Upload workflow
  - Estimated time: 3 hours
  - Dependencies: core/file.py, core/merkle.py, contracts/flow.py, core/node_selector.py
  - Notes: Brings together most components

---

## **Phase 8: Download Path**

- [ ] **`core/downloader.py`** - Download and verification
  - Estimated time: 2 hours
  - Dependencies: core/merkle.py, core/indexer.py, utils/http.py

---

## **Phase 9: Main Client**

- [ ] **`client.py`** - ZgStorageClient main entry point
  - Estimated time: 1 hour
  - Dependencies: core/uploader.py, core/downloader.py
  - Notes: This is the public API

---

## **Phase 10: Key-Value Store (Optional/Advanced)**

- [ ] **`kv/stream.py`** - Stream data builder
  - Estimated time: 1 hour
  - Dependencies: None
  - Notes: Can be skipped for MVP

- [ ] **`kv/batcher.py`** - Batch operations
  - Estimated time: 1 hour
  - Dependencies: kv/stream.py, contracts/flow.py
  - Notes: Can be skipped for MVP

- [ ] **`kv/client.py`** - KV client
  - Estimated time: 1 hour
  - Dependencies: core/indexer.py, models/node.py
  - Notes: Can be skipped for MVP

---

## **Phase 11: Package Entry**

- [ ] **`__init__.py`** - Package exports and public API
  - Estimated time: 30 minutes
  - Dependencies: client.py, core/file.py, exceptions.py

---

## **Additional Files**

### **Directory Initializers**
- [ ] **`core/__init__.py`**
- [ ] **`models/__init__.py`**
- [ ] **`utils/__init__.py`**
- [ ] **`contracts/__init__.py`**
- [ ] **`kv/__init__.py`**

---

## **MVP (Minimum Viable Product) Checklist**

These are the **essential files** needed for a working upload/download system:

### **Core MVP Files**
- [ ] config.py
- [ ] exceptions.py
- [ ] utils/crypto.py
- [ ] models/file.py
- [ ] core/merkle.py ⚠️ **CRITICAL**
- [ ] contracts/abis.py
- [ ] contracts/flow.py
- [ ] core/file.py
- [ ] utils/http.py
- [ ] core/indexer.py
- [ ] core/uploader.py
- [ ] core/downloader.py
- [ ] client.py
- [ ] __init__.py

### **MVP Can Skip**
- node_selector.py (use simple selection in uploader)
- All KV store files
- utils/validation.py (do inline validation initially)

---

## **Development Timeline**

### **Day 1: Foundation + Merkle Tree**
- [ ] Phase 1: Foundation (1 hour)
- [ ] Phase 2: Models (1 hour)
- [ ] Phase 3: Merkle Tree (3-4 hours) ⚠️

**Goal:** Working merkle tree implementation

---

### **Day 2: Contracts + File Operations**
- [ ] Phase 4: Smart Contracts (3 hours)
- [ ] Phase 5: Core File Operations (2 hours)

**Goal:** ZgFile can generate merkle trees, contracts are ready

---

### **Day 3: Network + Upload**
- [ ] Phase 6: Network Layer (3 hours)
- [ ] Phase 7: Upload Path (3 hours)

**Goal:** Can upload files to 0G network

---

### **Day 4: Download + Integration**
- [ ] Phase 8: Download Path (2 hours)
- [ ] Phase 9: Main Client (1 hour)
- [ ] Phase 11: Package Entry (30 min)

**Goal:** Complete working SDK with upload/download

---

### **Day 5+: Advanced Features (Optional)**
- [ ] Phase 10: Key-Value Store
- [ ] Advanced node selection

---

## **Progress Tracking**

### **Overall Progress**
- **Foundation:** 6/6 files ✅
- **Models:** 0/3 files
- **Core Crypto:** 0/1 files ⚠️
- **Contracts:** 0/2 files
- **File Ops:** 0/2 files
- **Network:** 0/2 files
- **Upload:** 0/1 files
- **Download:** 0/1 files
- **Main Client:** 0/1 files
- **KV Store:** 0/3 files
- **Package Entry:** 0/1 files

**Total MVP Progress:** 4/14 files (29%)**
**Total Complete Progress:** 6/21 files (29%)**

---

## **Notes**

### **Critical Success Factors**
1. ✅ **Merkle tree must match 0G protocol exactly** - This is non-negotiable
2. ✅ **Test each component before integration** - Unit tests are essential
3. ✅ **Research Flow contract ABI thoroughly** - Wrong ABI = broken uploads
4. ✅ **Handle network failures gracefully** - Nodes can be unreliable

### **Development Best Practices**
- Test each module in isolation before integration
- Use testnet for all integration testing
- Keep functions small and focused
- Document complex algorithms (especially merkle tree)

### **Resources Needed**
- [ ] 0G Storage protocol documentation
- [ ] Flow contract address and ABI
- [ ] Testnet RPC endpoints
- [ ] Example merkle tree implementation (reference)

---

## **Current Status**

**Last Updated:** October 16, 2024

**Current Phase:** Pre-development (Planning complete)

**Next Steps:**
1. Create directory structure
2. Start with config.py
3. Implement foundation files

**Blockers:** None

**Notes:** Ready to begin implementation

---

## **Update Log**

| Date | Files Completed | Notes |
|------|----------------|-------|
| Oct 16, 2024 | Planning phase | Development order established |
| Oct 16, 2024 | Phase 1 (6 files) | Foundation complete - all utilities ported from TS SDK |
|  |  |  |

---

*This document should be updated after completing each file. Check the box, update progress tracking, and add notes if needed.*
