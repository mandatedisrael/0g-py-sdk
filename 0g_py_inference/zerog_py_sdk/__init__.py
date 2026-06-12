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

from .broker import (
    ZGServingBroker,
    create_broker,
    create_broker_from_env,
    create_fine_tuning_broker,
    create_inference_broker,
    create_ledger_broker,
)
from .inference import InferenceManager
from .ledger import LedgerManager
from .read_only import (
    ReadOnlyInferenceBroker,
    create_read_only_broker,
    ZGComputeNetworkReadOnlyBroker,
    create_zg_compute_network_read_only_broker,
    is_verifiability,
    ServiceWithDetail,
    HealthMetrics,
    HealthStatus,
    ServiceHealthMetric,
    VerifiabilityEnum,
    ProviderModelInfo,
    ProviderModels,
    MultiModelInfo,
    PricingTier,
    TieredPricingInfo,
    CacheTokenBillingInfo,
    parse_tiered_pricing,
    parse_tiered_pricing_from_model_info,
    parse_cache_token_billing,
    parse_cache_token_billing_from_model_info,
    parse_multi_model_info,
)
from .models import (
    ServiceMetadata,
    LedgerAccount,
    RequestHeaders,
    ServingRequestHeaders,
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
    get_network_type,
    get_rpc_url,
    is_dev_mode,
)
from .extractors import (
    Extractor,
    ChatBotExtractor,
    TextToImageExtractor,
    ImageEditingExtractor,
    SpeechToTextExtractor,
    ChatBot,
    TextToImage,
    ImageEditing,
    SpeechToText,
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
    VerificationStep,
    VerificationStepType,
    VerificationResult,
    VerificationSummary,
    SignerReportMatch,
    SignerVerification,
    SignerRAVerificationResult,
    EventLogEntry,
    AttestationReport,
    ReportsData,
    ComposeVerification,
    ComposeVerificationDetail,
    ComposeVerificationResult,
    ProviderType,
    VerificationLogger,
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

__version__ = "0.8.0"

# TS-SDK name aliases for the combined broker / factory.
ZGComputeNetworkBroker = ZGServingBroker
create_zg_compute_network_broker = create_broker
InferenceBroker = InferenceManager
LedgerBroker = LedgerManager
create_read_only_inference_broker = create_read_only_broker

__all__ = [
    # Main classes
    "ZGServingBroker",
    "create_broker",
    "create_broker_from_env",
    "create_fine_tuning_broker",
    "create_inference_broker",
    "create_ledger_broker",
    "ZGComputeNetworkBroker",
    "create_zg_compute_network_broker",
    "InferenceBroker",
    "LedgerBroker",

    # Read-only broker
    "ReadOnlyInferenceBroker",
    "create_read_only_broker",
    "create_read_only_inference_broker",
    "ZGComputeNetworkReadOnlyBroker",
    "create_zg_compute_network_read_only_broker",
    "ServiceWithDetail",
    "HealthMetrics",
    "HealthStatus",
    "ServiceHealthMetric",
    "VerifiabilityEnum",
    "ProviderModelInfo",
    "ProviderModels",
    "MultiModelInfo",
    "PricingTier",
    "TieredPricingInfo",
    "CacheTokenBillingInfo",
    "parse_tiered_pricing",
    "parse_tiered_pricing_from_model_info",
    "parse_cache_token_billing",
    "parse_cache_token_billing_from_model_info",
    "parse_multi_model_info",
    
    # Models
    "ServiceMetadata",
    "LedgerAccount",
    "RequestHeaders",
    "ServingRequestHeaders",
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
    "get_network_type",
    "get_rpc_url",
    "is_dev_mode",
    
    # Service extractors
    "Extractor",
    "ChatBotExtractor",
    "TextToImageExtractor",
    "ImageEditingExtractor",
    "SpeechToTextExtractor",
    "ChatBot",
    "TextToImage",
    "ImageEditing",
    "SpeechToText",
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
    "VerificationStep",
    "VerificationStepType",
    "VerificationResult",
    "VerificationSummary",
    "SignerReportMatch",
    "SignerVerification",
    "SignerRAVerificationResult",
    "EventLogEntry",
    "AttestationReport",
    "ReportsData",
    "ComposeVerification",
    "ComposeVerificationDetail",
    "ComposeVerificationResult",
    "ProviderType",
    "VerificationLogger",
    "is_verifiability",
    
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
