"""
KV storage constants.

Ported from official TypeScript SDK:
src.ts/kv/constants.ts
"""
import hashlib

# Maximum set size (64K items)
MAX_SET_SIZE = 1 << 16  # 65536

# Maximum key size (16.7M bytes)
MAX_KEY_SIZE = 1 << 24  # 16777216

# Maximum query size for getValue calls
MAX_QUERY_SIZE = 1024 * 256  # 262144

# Stream domain hash: sha256("STREAM")
# df2ff3bb0af36c6384e6206552a4ed807f6f6a26e7d0aa6bff772ddc9d4307aa
STREAM_DOMAIN = hashlib.sha256(b"STREAM").digest()
