"""
KV Storage Module for 0G Storage.

Ported from official TypeScript SDK:
src.ts/kv/

Provides key-value storage functionality on top of 0G Storage.
"""

from .types import (
    AccessControlType,
    StreamRead,
    StreamWrite,
    AccessControl,
    StreamData,
)
from .constants import (
    MAX_SET_SIZE,
    MAX_KEY_SIZE,
    MAX_QUERY_SIZE,
    STREAM_DOMAIN,
)
from .builder import StreamDataBuilder
from .batcher import Batcher
from .client import KvClient
from .iterator import KvIterator

__all__ = [
    # Types
    'AccessControlType',
    'StreamRead',
    'StreamWrite',
    'AccessControl',
    'StreamData',
    # Constants
    'MAX_SET_SIZE',
    'MAX_KEY_SIZE',
    'MAX_QUERY_SIZE',
    'STREAM_DOMAIN',
    # Classes
    'StreamDataBuilder',
    'Batcher',
    'KvClient',
    'KvIterator',
]
