"""
0G Compute Network Python SDK

A Python implementation of the 0G Compute Network broker for AI inference services.

Basic usage:
    >>> from og_compute_sdk import create_broker
    >>> 
    >>> broker = create_broker(
    ...     private_key="0x...",
    ...     rpc_url="https://evmrpc-testnet.0g.ai"
    ... )
    >>> 
    >>> # Fund account
    >>> broker.ledger.add_ledger("0.1", provider_address)
    >>> 
    >>> # List available services
    >>> services = broker.inference.list_service()
    >>> for service in services:
    ...     print(f"{service.model} - {service.provider}")
    >>> 
    >>> # Generate request headers
    >>> headers = broker.inference.get_request_headers(provider_address, content)
    >>> 
    >>> # Make request to provider
    >>> import requests
    >>> response = requests.post(
    ...     f"{service.url}/chat/completions",
    ...     headers={"Content-Type": "application/json", **headers},
    ...     json={"messages": [{"role": "user", "content": "Hello"}], "model": service.model}
    ... )
"""

from .broker import ZGServingBroker, create_broker, create_broker_from_env
from .models import (
    ServiceMetadata,
    LedgerAccount,
    RequestHeaders,
    ProviderInfo,
    ChatMessage,
    ChatResponse
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

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "ZGServingBroker",
    "create_broker",
    "create_broker_from_env",
    
    # Models
    "ServiceMetadata",
    "LedgerAccount",
    "RequestHeaders",
    "ProviderInfo",
    "ChatMessage",
    "ChatResponse",
    
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
]