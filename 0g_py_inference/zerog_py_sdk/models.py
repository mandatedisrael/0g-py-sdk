"""
Data models for the 0G Compute Network SDK.

This module contains all data classes and type definitions used throughout the SDK.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
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
        """Get available (unlocked) balance in wei."""
        return self.balance


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


@dataclass
class Refund:
    """
    Refund request information.
    
    Attributes:
        index: Refund index
        amount: Refund amount in wei
        created_at: Unix timestamp when refund was requested
        processed: Whether the refund has been processed
    """
    index: int
    amount: int
    created_at: int
    processed: bool


@dataclass
class RefundDetail:
    """
    Refund detail with remaining time calculation.
    
    Attributes:
        amount: Refund amount in wei
        remain_time: Seconds until refund can be processed
    """
    amount: int
    remain_time: int


@dataclass
class Account:
    """
    User account with a specific provider.

    Updated to match current contract struct (March 2026):
    (user, provider, nonce, balance, pendingRefund, refunds[], additionalInfo,
     acknowledged, validRefundsLength, generation, revokedBitmap)

    Attributes:
        user: User's wallet address
        provider: Provider's wallet address
        nonce: Current nonce for request signing
        balance: Current balance in wei
        pending_refund: Amount pending refund in wei
        refunds: List of refund requests
        additional_info: Additional account metadata
        acknowledged: Whether TEE signer is acknowledged
        valid_refunds_length: Number of valid refunds
        generation: Token generation number
        revoked_bitmap: Bitmap of revoked token IDs
    """
    user: str
    provider: str
    nonce: int
    balance: int
    pending_refund: int
    refunds: List[Refund] = field(default_factory=list)
    additional_info: str = ""
    acknowledged: bool = False
    valid_refunds_length: int = 0
    generation: int = 0
    revoked_bitmap: int = 0

    @property
    def locked_balance(self) -> int:
        """Get locked balance (balance - pending_refund)."""
        return self.balance - self.pending_refund


@dataclass
class AccountWithDetail:
    """
    Account with refund details including remaining time.
    
    Attributes:
        account: The base account information
        refund_details: List of refunds with remaining time
    """
    account: Account
    refund_details: List[RefundDetail] = field(default_factory=list)


@dataclass
class LedgerDetail:
    """
    Detailed ledger information with provider breakdowns.
    
    Attributes:
        total_balance: Total balance in wei
        locked_balance: Locked balance in wei
        available_balance: Available balance in wei
        inference_providers: List of (provider, balance, pending_refund) for inference
        fine_tuning_providers: List of (provider, balance, pending_refund) for fine-tuning
    """
    total_balance: int
    locked_balance: int
    available_balance: int
    inference_providers: List[tuple] = field(default_factory=list)  # (provider, balance, pending_refund)
    fine_tuning_providers: List[tuple] = field(default_factory=list)


@dataclass
class AutoFundingConfig:
    """
    Configuration for automatic provider sub-account funding.

    Attributes:
        interval_ms: How often to check balance (milliseconds, default 30s)
        buffer_multiplier: Multiplier over MIN_LOCKED_BALANCE to maintain (default 2)
    """
    interval_ms: int = 30000
    buffer_multiplier: int = 2


@dataclass
class AdditionalInfo:
    """
    Parsed additional info from service metadata.
    
    Used for determining TEE architecture and signing address.
    
    Attributes:
        verifier_url: URL for TEE verification
        target_separated: Whether broker and LLM run in separate TEE nodes
        tee_verifier: TEE verifier type
        target_tee_address: Override signing address for separated architecture
        image_name: Docker image name
        image_digest: Docker image digest
        provider_type: "decentralized" (broker + LLM in TEE) or
            "centralized" (broker in TEE, LLM is external e.g. OpenAI/Anthropic).
            Defaults to "decentralized" for backward compatibility.
    """
    verifier_url: Optional[str] = None
    target_separated: bool = False
    tee_verifier: Optional[str] = None
    target_tee_address: Optional[str] = None
    image_name: Optional[str] = None
    image_digest: Optional[str] = None
    provider_type: str = "decentralized"

    @classmethod
    def from_json(cls, json_str: str) -> 'AdditionalInfo':
        """Parse additional info from JSON string."""
        import json
        import logging
        try:
            data = json.loads(json_str)
            provider_type = data.get('ProviderType', 'decentralized')
            if provider_type not in ('decentralized', 'centralized'):
                logging.getLogger(__name__).warning(
                    "Invalid ProviderType %r, defaulting to 'decentralized'",
                    provider_type,
                )
                provider_type = 'decentralized'
            return cls(
                verifier_url=data.get('VerifierURL'),
                target_separated=data.get('TargetSeparated', False),
                tee_verifier=data.get('TEEVerifier'),
                target_tee_address=data.get('TargetTeeAddress'),
                image_name=data.get('ImageName'),
                image_digest=data.get('ImageDigest'),
                provider_type=provider_type,
            )
        except (json.JSONDecodeError, TypeError):
            return cls()