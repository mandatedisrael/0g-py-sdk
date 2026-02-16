"""
Session token management for the 0G Compute Network SDK.

This module implements the new session-based authorization system that replaces
the deprecated header-based authentication. It supports both ephemeral tokens
(for SDK usage) and persistent API keys (for long-term access).

Reference: TypeScript SDK src.ts/sdk/inference/broker/base.ts
"""

import json
import time
import secrets
import base64
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from web3 import Web3
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_defunct


# Constants matching TypeScript SDK
EPHEMERAL_TOKEN_ID = 255
EPHEMERAL_TOKEN_MAX_DURATION = 24 * 60 * 60 * 1000  # 24 hours in milliseconds


class SessionMode(Enum):
    """Session mode for token generation."""
    EPHEMERAL = "ephemeral"  # tokenId=255, not individually revocable
    PERSISTENT = "persistent"  # tokenId 0-254, individually revocable


@dataclass
class SessionToken:
    """Session token structure matching TypeScript SDK."""
    address: str
    provider: str
    timestamp: int
    expires_at: int  # 0 = never expires
    nonce: str
    generation: int  # Token generation for batch revocation
    token_id: int  # 0-254: persistent, 255: ephemeral

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization (camelCase for TS compatibility)."""
        return {
            "address": self.address,
            "provider": self.provider,
            "timestamp": self.timestamp,
            "expiresAt": self.expires_at,
            "nonce": self.nonce,
            "generation": self.generation,
            "tokenId": self.token_id,
        }


@dataclass
class CachedSession:
    """Cached session with token, signature, and raw message."""
    token: SessionToken
    signature: str
    raw_message: str


@dataclass 
class ApiKeyInfo:
    """API Key information for persistent tokens."""
    token_id: int
    created_at: int
    expires_at: int
    raw_token: str


class SessionManager:
    """
    Manages session tokens for the 0G Compute Network.
    
    This replaces the old header-based authentication with the new
    session token system. Supports both ephemeral (SDK usage) and
    persistent (API keys) tokens.
    
    Example:
        >>> session_mgr = SessionManager(account, web3, contract)
        >>> headers = session_mgr.get_request_headers(provider_address)
        >>> # headers = {"Authorization": "Bearer app-sk-..."}
    """
    
    def __init__(
        self,
        account: LocalAccount,
        web3: Web3,
        contract: Any  # InferenceServing contract
    ):
        self.account = account
        self.web3 = web3
        self.contract = contract
        self._session_cache: Dict[str, CachedSession] = {}
    
    def generate_session_token(
        self,
        provider_address: str,
        mode: SessionMode = SessionMode.EPHEMERAL,
        duration: Optional[int] = None,
        token_id: Optional[int] = None
    ) -> CachedSession:
        """
        Generate a new session token.
        
        Args:
            provider_address: Provider's wallet address
            mode: EPHEMERAL (default) or PERSISTENT
            duration: Token duration in milliseconds (0 = never expires for persistent)
            token_id: Specific tokenId for persistent mode (0-254)
            
        Returns:
            CachedSession with token, signature, and raw message
        """
        provider_address = Web3.to_checksum_address(provider_address)
        timestamp = int(time.time() * 1000)  # milliseconds
        nonce = self._generate_nonce()
        
        # Determine duration and expiration
        if mode == SessionMode.EPHEMERAL:
            if duration is None:
                duration = EPHEMERAL_TOKEN_MAX_DURATION
            if duration <= 0:
                duration = EPHEMERAL_TOKEN_MAX_DURATION
            if duration > EPHEMERAL_TOKEN_MAX_DURATION:
                raise ValueError(
                    f"Ephemeral token duration cannot exceed 24 hours ({EPHEMERAL_TOKEN_MAX_DURATION}ms)"
                )
            expires_at = timestamp + duration
        else:
            # Persistent tokens can have any duration
            duration = duration or 0
            expires_at = timestamp + duration if duration > 0 else 0
        
        # Determine tokenId and generation
        if mode == SessionMode.EPHEMERAL:
            token_id = EPHEMERAL_TOKEN_ID
            generation = self._get_account_generation(provider_address)
        else:
            generation = self._get_account_generation(provider_address)
            if token_id is not None:
                if token_id < 0 or token_id >= EPHEMERAL_TOKEN_ID:
                    raise ValueError(
                        f"Invalid tokenId: {token_id}. Must be between 0 and {EPHEMERAL_TOKEN_ID - 1}"
                    )
                # Check if revoked
                revoked_bitmap = self._get_revoked_bitmap(provider_address)
                if (revoked_bitmap >> token_id) & 1:
                    raise ValueError(
                        f"TokenId {token_id} is already revoked. Use a different tokenId."
                    )
            else:
                # Find available tokenId
                token_id = self._find_available_token_id(provider_address)
        
        # Create token
        token = SessionToken(
            address=self.account.address,
            provider=provider_address,
            timestamp=timestamp,
            expires_at=expires_at,
            nonce=nonce,
            generation=generation,
            token_id=token_id,
        )
        
        # Serialize to JSON (matching TypeScript format)
        message = json.dumps(token.to_dict(), separators=(',', ':'))
        
        # Sign the message hash (keccak256 of message bytes)
        message_hash = Web3.keccak(text=message)
        signable = encode_defunct(primitive=message_hash)
        signed = self.account.sign_message(signable)
        signature = signed.signature.hex()
        if not signature.startswith('0x'):
            signature = '0x' + signature
        
        session = CachedSession(
            token=token,
            signature=signature,
            raw_message=message,
        )
        
        # Cache ephemeral sessions
        if mode == SessionMode.EPHEMERAL:
            cache_key = f"{self.account.address}_{provider_address}"
            self._session_cache[cache_key] = session
        
        return session
    
    def get_or_create_session(self, provider_address: str) -> CachedSession:
        """
        Get cached session or create new ephemeral session.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            CachedSession for the provider
        """
        provider_address = Web3.to_checksum_address(provider_address)
        cache_key = f"{self.account.address}_{provider_address}"
        
        # Check cache
        if cache_key in self._session_cache:
            cached = self._session_cache[cache_key]
            # Check if token has enough time remaining (at least 1 hour)
            now = int(time.time() * 1000)
            if cached.token.expires_at > now + (60 * 60 * 1000):
                return cached
        
        # Generate new ephemeral session
        return self.generate_session_token(provider_address, SessionMode.EPHEMERAL)
    
    def get_request_headers(self, provider_address: str) -> Dict[str, str]:
        """
        Get request headers with session token authorization.
        
        This is the main method for SDK usage. It returns headers with
        the new Authorization format that replaces deprecated headers.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Headers dict with Authorization header
            
        Example:
            >>> headers = session_mgr.get_request_headers(provider)
            >>> response = requests.post(url, headers=headers, json=data)
        """
        session = self.get_or_create_session(provider_address)
        
        # Create Authorization header matching TypeScript format
        token_data = session.raw_message + "|" + session.signature
        encoded = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
        
        return {
            "Authorization": f"Bearer app-sk-{encoded}"
        }
    
    def create_api_key(
        self,
        provider_address: str,
        expires_in: Optional[int] = None,
        token_id: Optional[int] = None
    ) -> ApiKeyInfo:
        """
        Create a persistent API key.
        
        API keys use tokenId 0-254 and can be individually revoked.
        They persist until revoked or expired.
        
        Args:
            provider_address: Provider's wallet address
            expires_in: Expiration in milliseconds (0 or None = never expires)
            token_id: Specific tokenId to use (0-254)
            
        Returns:
            ApiKeyInfo with the raw token for use in requests
        """
        session = self.generate_session_token(
            provider_address,
            mode=SessionMode.PERSISTENT,
            duration=expires_in or 0,
            token_id=token_id,
        )
        
        token_data = session.raw_message + "|" + session.signature
        encoded = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
        raw_token = f"app-sk-{encoded}"
        
        return ApiKeyInfo(
            token_id=session.token.token_id,
            created_at=session.token.timestamp,
            expires_at=session.token.expires_at,
            raw_token=raw_token,
        )
    
    def _generate_nonce(self) -> str:
        """Generate a random nonce."""
        return secrets.token_hex(16)
    
    def _get_account_generation(self, provider_address: str) -> int:
        """Get token generation from contract account."""
        try:
            account = self.contract.functions.getAccount(
                self.account.address,
                provider_address
            ).call()
            # Account struct has generation field
            # Try to get generation, default to 0 if not present
            if len(account) > 10:
                return int(account[10])  # generation field index
            return 0
        except Exception:
            return 0
    
    def _get_revoked_bitmap(self, provider_address: str) -> int:
        """Get revoked token bitmap from contract."""
        try:
            account = self.contract.functions.getAccount(
                self.account.address,
                provider_address
            ).call()
            if len(account) > 11:
                return int(account[11])  # revokedBitmap field index
            return 0
        except Exception:
            return 0
    
    def _find_available_token_id(self, provider_address: str) -> int:
        """Find smallest available tokenId from revoked bitmap."""
        revoked_bitmap = self._get_revoked_bitmap(provider_address)
        
        for token_id in range(EPHEMERAL_TOKEN_ID):
            if not ((revoked_bitmap >> token_id) & 1):
                return token_id
        
        raise ValueError("API Key limit reached (255). Revoke existing keys to continue.")
    
    def clear_session_cache(self, provider_address: Optional[str] = None):
        """
        Clear cached sessions.
        
        Args:
            provider_address: Clear only for this provider, or all if None
        """
        if provider_address:
            provider_address = Web3.to_checksum_address(provider_address)
            cache_key = f"{self.account.address}_{provider_address}"
            self._session_cache.pop(cache_key, None)
        else:
            self._session_cache.clear()
