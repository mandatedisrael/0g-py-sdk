"""
Data models for the 0G Compute Network SDK.

This module contains all data classes and type definitions used throughout the SDK.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from typing_extensions import TypedDict


@dataclass
class ServiceMetadata:
    """
    Metadata for a provider service.
    
    Attributes:
        provider: Provider's wallet address (unique identifier)
        service_type: Type of service offered
        url: Service endpoint URL
        input_price: Price for input processing (in wei)
        output_price: Price for output generation (in wei)
        updated_at: Last update timestamp (unix timestamp)
        model: Model identifier (e.g., 'llama-3.3-70b-instruct')
        verifiability: Verification type ('TeeML' for TEE, empty for none)
    """
    provider: str
    service_type: str
    url: str
    input_price: int
    output_price: int
    updated_at: int
    model: str
    verifiability: str

    def is_verifiable(self) -> bool:
        """Check if this service provides verifiable outputs."""
        return bool(self.verifiability)


@dataclass
class LedgerAccount:
    """
    Ledger account information.
    
    Attributes:
        balance: Current account balance (in wei)
        locked: Locked funds (in wei)
        total_balance: Total balance including locked funds (in wei)
    """
    balance: int
    locked: int
    total_balance: int
    
    @property
    def available(self) -> int:
        """Get available (unlocked) balance."""
        return self.balance - self.locked


class RequestHeaders(TypedDict):
    """
    Request headers for authenticated service calls.
    
    These headers contain billing information and authentication data.
    They are single-use only to prevent replay attacks.
    """
    X_Signature: str
    Address: str
    Nonce: str
    Content: str


@dataclass
class ProviderInfo:
    """
    Extended provider information.
    
    Attributes:
        address: Provider's wallet address
        endpoint: Service endpoint URL
        model: Model identifier
        verifiability: Verification type
        acknowledged: Whether provider has been acknowledged on-chain
    """
    address: str
    endpoint: str
    model: str
    verifiability: str
    acknowledged: bool = False


@dataclass
class ChatMessage:
    """
    Chat message structure compatible with OpenAI format.
    
    Attributes:
        role: Message role ('system', 'user', or 'assistant')
        content: Message content
    """
    role: str
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class ChatResponse:
    """
    Parsed response from chat completion.
    
    Attributes:
        id: Chat ID (used for verification in TEE services)
        content: Response content
        model: Model that generated the response
        provider: Provider address that served the request
    """
    id: str
    content: str
    model: str
    provider: str