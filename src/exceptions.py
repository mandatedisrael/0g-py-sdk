"""
Custom exceptions for the 0G Compute Network SDK.

This module defines all exception types that can be raised during SDK operations.
"""


class ZGServingBrokerError(Exception):
    """
    Base exception for all 0G Serving Broker errors.
    
    All custom exceptions in this SDK inherit from this base class.
    """
    pass


class InsufficientBalanceError(ZGServingBrokerError):
    """
    Raised when account has insufficient balance for an operation.
    
    This typically occurs when:
    - Trying to make a request without enough funds
    - Account balance is lower than required amount
    """
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient balance. Required: {required} wei, Available: {available} wei. "
            f"Please add funds using broker.ledger.add_ledger()"
        )


class ProviderNotAcknowledgedError(ZGServingBrokerError):
    """
    Raised when attempting to use a provider that hasn't been acknowledged.
    
    Before using a provider's services, you must acknowledge them on-chain
    using broker.inference.acknowledge_provider_signer(provider_address).
    """
    def __init__(self, provider_address: str):
        self.provider_address = provider_address
        super().__init__(
            f"Provider {provider_address} has not been acknowledged. "
            f"Call broker.inference.acknowledge_provider_signer('{provider_address}') first."
        )


class HeadersAlreadyUsedError(ZGServingBrokerError):
    """
    Raised when attempting to reuse request headers.
    
    Request headers are single-use only to prevent replay attacks.
    Generate new headers for each request.
    """
    def __init__(self):
        super().__init__(
            "Request headers are single-use only and cannot be reused. "
            "Generate new headers for each request using broker.inference.get_request_headers()"
        )


class InvalidResponseError(ZGServingBrokerError):
    """
    Raised when a provider returns an invalid or malformed response.
    
    This can occur when:
    - Response format doesn't match expected structure
    - Response verification fails (for TEE services)
    - Provider returns an error
    """
    def __init__(self, message: str, provider_address: str = None):
        self.provider_address = provider_address
        error_msg = f"Invalid response from provider"
        if provider_address:
            error_msg += f" {provider_address}"
        error_msg += f": {message}"
        super().__init__(error_msg)


class ContractError(ZGServingBrokerError):
    """
    Raised when a smart contract interaction fails.
    
    This can occur when:
    - Transaction reverts
    - Contract function call fails
    - Network issues
    """
    def __init__(self, operation: str, reason: str = None):
        self.operation = operation
        self.reason = reason
        error_msg = f"Contract operation '{operation}' failed"
        if reason:
            error_msg += f": {reason}"
        super().__init__(error_msg)


class ServiceNotFoundError(ZGServingBrokerError):
    """
    Raised when a requested service or provider cannot be found.
    
    This occurs when:
    - Provider address doesn't exist in the network
    - Service has been removed or is no longer available
    """
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(
            f"Service or provider '{identifier}' not found. "
            f"Use broker.inference.list_service() to see available services."
        )


class NetworkError(ZGServingBrokerError):
    """
    Raised when network communication fails.
    
    This can occur when:
    - RPC endpoint is unreachable
    - Provider service is offline
    - Network timeout
    """
    def __init__(self, message: str, endpoint: str = None):
        self.endpoint = endpoint
        error_msg = "Network error"
        if endpoint:
            error_msg += f" connecting to {endpoint}"
        error_msg += f": {message}"
        super().__init__(error_msg)


class AuthenticationError(ZGServingBrokerError):
    """
    Raised when authentication or signature verification fails.
    
    This can occur when:
    - Invalid private key
    - Signature generation fails
    - Header validation fails
    """
    def __init__(self, message: str):
        super().__init__(f"Authentication error: {message}")


class ConfigurationError(ZGServingBrokerError):
    """
    Raised when SDK configuration is invalid or incomplete.
    
    This can occur when:
    - Missing required environment variables
    - Invalid contract address
    - Invalid RPC URL
    """
    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")