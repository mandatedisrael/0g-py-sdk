"""
Caching system for the 0G Compute Network SDK.

This module provides TTL-based caching to reduce blockchain and API calls
by caching service info, session tokens, account info, and fees.

Usage:
    >>> from zerog_py_sdk.cache import Cache, CacheValueType, cache_key
    >>> 
    >>> cache = Cache()
    >>> cache.set("service_0x123", service_data, ttl=600)  # 10 minutes
    >>> service = cache.get("service_0x123")
"""

import json
import time
import threading
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, TypeVar, Generic, Callable


class CacheValueType(Enum):
    """Types of cached values for proper serialization."""
    SERVICE = "service"
    BIGINT = "bigint"
    SESSION = "session"
    ACCOUNT = "account"
    OTHER = "other"


# Cache key prefixes
CACHE_PREFIX = "0g_cache_"

# Standard TTL values (in seconds)
TTL_SERVICE_INFO = 600        # 10 minutes
TTL_ACCOUNT_INFO = 300        # 5 minutes
TTL_SESSION_TOKEN = 86400     # 24 hours (max for ephemeral tokens)
TTL_CACHED_FEE = 60           # 1 minute
TTL_BALANCE_CHECK = 60        # 1 minute
TTL_USER_ACK = 600            # 10 minutes


class CacheKeys:
    """Helper methods for generating cache keys."""
    
    @staticmethod
    def service(provider: str) -> str:
        """Cache key for service info."""
        return f"service_{provider.lower()}"
    
    @staticmethod
    def user_ack(user: str, provider: str) -> str:
        """Cache key for user acknowledgment status."""
        return f"{user.lower()}_{provider.lower()}_ack"
    
    @staticmethod
    def cached_fee(provider: str) -> str:
        """Cache key for accumulated fees."""
        return f"{provider.lower()}_cachedFee"
    
    @staticmethod
    def check_balance(provider: str) -> str:
        """Cache key for balance check threshold."""
        return f"{provider.lower()}_checkBalance"
    
    @staticmethod
    def session_token(user: str, provider: str) -> str:
        """Cache key for ephemeral session tokens."""
        return f"session_{user.lower()}_{provider.lower()}"
    
    @staticmethod
    def account_info(user: str, provider: str) -> str:
        """Cache key for account info (generation, bitmap)."""
        return f"account_info_{user.lower()}_{provider.lower()}"


@dataclass
class CacheItem:
    """A cached item with value, expiry time, and type."""
    value: Any
    expiry: float  # Unix timestamp
    value_type: str


class Cache:
    """
    In-memory cache with TTL-based expiration.
    
    Thread-safe cache implementation with automatic expiration
    and proper serialization for different value types.
    
    Example:
        >>> cache = Cache()
        >>> 
        >>> # Cache service info for 10 minutes
        >>> cache.set(CacheKeys.service(provider), service, ttl=TTL_SERVICE_INFO)
        >>> 
        >>> # Retrieve cached value
        >>> service = cache.get(CacheKeys.service(provider))
        >>> if service is None:
        ...     # Cache miss, fetch from contract
        ...     service = contract.getService(provider)
        ...     cache.set(CacheKeys.service(provider), service, ttl=TTL_SERVICE_INFO)
    """
    
    def __init__(self):
        """Initialize the cache."""
        self._storage: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int,
        value_type: CacheValueType = CacheValueType.OTHER
    ) -> None:
        """
        Set a cache item with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            value_type: Type of value for proper serialization
        """
        with self._lock:
            now = time.time()
            item = CacheItem(
                value=self._encode_value(value, value_type),
                expiry=now + ttl,
                value_type=value_type.value
            )
            self._storage[self._prefixed_key(key)] = json.dumps({
                'value': item.value,
                'expiry': item.expiry,
                'value_type': item.value_type
            })
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a cache item.
        
        Returns None if key doesn't exist or has expired.
        Expired items are automatically removed.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self._lock:
            prefixed = self._prefixed_key(key)
            item_str = self._storage.get(prefixed)
            
            if item_str is None:
                return None
            
            try:
                item_data = json.loads(item_str)
                now = time.time()
                
                # Check expiration
                if now > item_data['expiry']:
                    del self._storage[prefixed]
                    return None
                
                # Decode and return value
                value_type = CacheValueType(item_data['value_type'])
                return self._decode_value(item_data['value'], value_type)
                
            except (json.JSONDecodeError, KeyError, ValueError):
                # Corrupted cache entry
                del self._storage[prefixed]
                return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache item.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            prefixed = self._prefixed_key(key)
            if prefixed in self._storage:
                del self._storage[prefixed]
                return True
            return False
    
    def set_lock(
        self,
        key: str,
        value: Any,
        ttl: int,
        value_type: CacheValueType = CacheValueType.OTHER
    ) -> bool:
        """
        Atomic set-if-not-exists (lock acquisition).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            value_type: Type of value
            
        Returns:
            True if lock acquired (key was not present), False otherwise
        """
        with self._lock:
            if self.get(key) is not None:
                return False
            self.set(key, value, ttl, value_type)
            return True
    
    def remove_lock(self, key: str) -> bool:
        """
        Remove a lock.
        
        Args:
            key: Cache key
            
        Returns:
            True if lock was removed, False if not found
        """
        return self.delete(key)
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._storage.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired items.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            now = time.time()
            expired_keys = []
            
            for key, item_str in self._storage.items():
                try:
                    item_data = json.loads(item_str)
                    if now > item_data['expiry']:
                        expired_keys.append(key)
                except (json.JSONDecodeError, KeyError):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._storage[key]
            
            return len(expired_keys)
    
    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{CACHE_PREFIX}{key}"
    
    def _encode_value(self, value: Any, value_type: CacheValueType) -> Any:
        """Encode value for JSON serialization."""
        if value_type == CacheValueType.BIGINT:
            return f"{value}n"  # BigInt format
        elif hasattr(value, '__dict__'):
            # Dataclass or object
            return value.__dict__ if hasattr(value, '__dict__') else str(value)
        elif isinstance(value, dict):
            return value
        else:
            return value
    
    def _decode_value(self, value: Any, value_type: CacheValueType) -> Any:
        """Decode value from JSON."""
        if value_type == CacheValueType.BIGINT:
            if isinstance(value, str) and value.endswith('n'):
                return int(value[:-1])
            return int(value)
        return value


# Global cache instance
_global_cache: Optional[Cache] = None
_cache_lock = threading.Lock()


def get_cache() -> Cache:
    """
    Get the global cache instance.
    
    Creates a new instance if none exists.
    
    Returns:
        Cache instance
    """
    global _global_cache
    with _cache_lock:
        if _global_cache is None:
            _global_cache = Cache()
        return _global_cache


def cached(
    key_func: Callable[..., str],
    ttl: int,
    value_type: CacheValueType = CacheValueType.OTHER
):
    """
    Decorator for caching function results.
    
    Args:
        key_func: Function to generate cache key from args
        ttl: Time-to-live in seconds
        value_type: Type of cached value
        
    Example:
        >>> @cached(lambda provider: CacheKeys.service(provider), ttl=600)
        ... def get_service(provider: str):
        ...     return contract.getService(provider)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = key_func(*args, **kwargs)
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                return result
            
            # Cache miss, call function
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl, value_type)
            
            return result
        return wrapper
    return decorator
