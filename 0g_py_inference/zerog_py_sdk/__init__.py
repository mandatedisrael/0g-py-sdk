"""
0G Compute Network Python SDK

A Python implementation of the 0G Compute Network broker for AI inference services.

Basic usage:
    >>> from zerog_py_sdk import create_broker
    >>> 
    >>> # With wallet (for transactions)
    >>> broker = create_broker(private_key="0x...")
    >>> services = broker.inference.list_service()
    >>> headers = broker.inference.get_request_headers(provider_address)
    >>> 
    >>> # Without wallet (read-only)
    >>> from zerog_py_sdk import create_read_only_broker
    >>> broker = create_read_only_broker()
    >>> services = broker.list_service_with_detail()
"""

from .broker import ZGServingBroker, create_broker, create_broker_from_env
from .read_only import (
    ReadOnlyInferenceBroker,
    create_read_only_broker,
    ServiceWithDetail,
    HealthMetrics,
    HealthStatus,
    VerifiabilityEnum,
)
from .models import (
    ServiceMetadata,
    LedgerAccount,
    RequestHeaders,
    ProviderInfo,
    ChatMessage,
    ChatResponse,
    Account,
    AccountWithDetail,
    Refund,
    RefundDetail,
    LedgerDetail,
    AdditionalInfo,
    AutoFundingConfig,
)
from .session import (
    SessionMode,
    SessionToken,
    CachedSession,
    ApiKeyInfo,
    SessionManager,
    EPHEMERAL_TOKEN_ID,
    EPHEMERAL_TOKEN_MAX_DURATION,
)
from .constants import (
    TESTNET_CHAIN_ID,
    MAINNET_CHAIN_ID,
    HARDHAT_CHAIN_ID,
    CONTRACT_ADDRESSES,
    get_contract_addresses,
    get_rpc_url,
    is_dev_mode,
)
from .extractors import (
    Extractor,
    ChatBotExtractor,
    TextToImageExtractor,
    ImageEditingExtractor,
    SpeechToTextExtractor,
    create_extractor,
    EXTRACTOR_REGISTRY,
)
from .cache import (
    Cache,
    CacheValueType,
    CacheKeys,
    get_cache,
    cached,
    TTL_SERVICE_INFO,
    TTL_ACCOUNT_INFO,
    TTL_SESSION_TOKEN,
    TTL_CACHED_FEE,
)
from .verifier import (
    ResponseVerifier,
    ResponseSignature,
    get_response_verifier,
    verify_tee_response,
)
from .exceptions import (
    ZGServingBrokerError,
    InsufficientBalanceError,
    ProviderNotAcknowledgedError,
    HeadersAlreadyUsedError,
    InvalidResponseError,
    ContractError,
    ServiceNotFoundError,
    NetworkError,
    AuthenticationError,
    ConfigurationError
)
from .fine_tuning.broker import (
    FineTuningBroker,
    ReadOnlyFineTuningBroker,
    create_read_only_fine_tuning_broker,
)
from .fine_tuning.contract.types import (
    Quota,
    Deliverable,
    FineTuningAccountDetails,
    FineTuningAccountDetail,
    FineTuningService,
    Task as FineTuningTask,
    CustomizedModel,
    TdxQuoteResponse,
)

__version__ = "0.5.0"

__all__ = [
    # Main classes
    "ZGServingBroker",
    "create_broker",
    "create_broker_from_env",
    
    # Read-only broker
    "ReadOnlyInferenceBroker",
    "create_read_only_broker",
    "ServiceWithDetail",
    "HealthMetrics",
    "HealthStatus",
    "VerifiabilityEnum",
    
    # Models
    "ServiceMetadata",
    "LedgerAccount",
    "RequestHeaders",
    "ProviderInfo",
    "ChatMessage",
    "ChatResponse",
    "Account",
    "AccountWithDetail",
    "Refund",
    "RefundDetail",
    "LedgerDetail",
    "AdditionalInfo",
    "AutoFundingConfig",

    # Session (new auth system)
    "SessionMode",
    "SessionToken",
    "CachedSession",
    "ApiKeyInfo",
    "SessionManager",
    "EPHEMERAL_TOKEN_ID",
    "EPHEMERAL_TOKEN_MAX_DURATION",
    
    # Network constants
    "TESTNET_CHAIN_ID",
    "MAINNET_CHAIN_ID",
    "HARDHAT_CHAIN_ID",
    "CONTRACT_ADDRESSES",
    "get_contract_addresses",
    "get_rpc_url",
    "is_dev_mode",
    
    # Service extractors
    "Extractor",
    "ChatBotExtractor",
    "TextToImageExtractor",
    "ImageEditingExtractor",
    "SpeechToTextExtractor",
    "create_extractor",
    "EXTRACTOR_REGISTRY",
    
    # Caching
    "Cache",
    "CacheValueType",
    "CacheKeys",
    "get_cache",
    "cached",
    "TTL_SERVICE_INFO",
    "TTL_ACCOUNT_INFO",
    "TTL_SESSION_TOKEN",
    "TTL_CACHED_FEE",
    
    # Response verification
    "ResponseVerifier",
    "ResponseSignature",
    "get_response_verifier",
    "verify_tee_response",
    
    # Exceptions
    "ZGServingBrokerError",
    "InsufficientBalanceError",
    "ProviderNotAcknowledgedError",
    "HeadersAlreadyUsedError",
    "InvalidResponseError",
    "ContractError",
    "ServiceNotFoundError",
    "NetworkError",
    "AuthenticationError",
    "ConfigurationError",

    # Fine-tuning
    "FineTuningBroker",
    "ReadOnlyFineTuningBroker",
    "create_read_only_fine_tuning_broker",
    "Quota",
    "Deliverable",
    "FineTuningAccountDetails",
    "FineTuningAccountDetail",
    "FineTuningService",
    "FineTuningTask",
    "CustomizedModel",
    "TdxQuoteResponse",
]