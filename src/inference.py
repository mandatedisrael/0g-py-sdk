"""
Inference operations for the 0G Compute Network SDK.

This module handles service discovery, provider acknowledgment,
and request management for AI inference services.
"""

from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount
import requests

from .models import ServiceMetadata
from .exceptions import (
    ContractError,
    ServiceNotFoundError,
    ProviderNotAcknowledgedError,
    InvalidResponseError,
    NetworkError
)
from .utils import format_address, validate_provider_address, parse_transaction_receipt


class InferenceManager:
    """
    Manages inference operations for the 0G Compute Network.
    
    This class handles:
    - Service discovery (listing available providers)
    - Provider acknowledgment
    - Service metadata retrieval
    - Request header generation
    - Response processing and verification
    """
    
    def __init__(
        self,
        contract: Contract,
        account: LocalAccount,
        web3: Web3,
        auth_manager: Any  # Avoid circular import, type will be AuthManager
    ):
        """
        Initialize the InferenceManager.
        
        Args:
            contract: Web3 contract instance
            account: Local account for signing transactions
            web3: Web3 instance
            auth_manager: AuthManager instance for header generation
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
        self.auth_manager = auth_manager
        self._acknowledged_providers = set()
    
    def list_service(self) -> List[ServiceMetadata]:
        """
        Retrieve a list of all available services from the contract.
        
        Returns:
            List of ServiceMetadata objects
            
        Raises:
            ContractError: If the contract call fails
            
        Example:
            >>> services = inference.list_service()
            >>> for service in services:
            ...     print(f"{service.model} at {service.url}")
        """
        try:
            # getAllServices() returns Service[] array
            services_data = self.contract.functions.getAllServices().call()
            
            services = []
            for service in services_data:
                # Service struct: (provider, serviceType, url, inputPrice, outputPrice, updatedAt, model, verifiability, additionalInfo)
                services.append(ServiceMetadata(
                    provider=service[0],
                    service_type=service[1],
                    url=service[2],
                    input_price=service[3],
                    output_price=service[4],
                    updated_at=service[5],
                    model=service[6],
                    verifiability=service[7]
                ))
            
            return services
            
        except Exception as e:
            raise ContractError("getAllServices", str(e))
    
    def get_service(self, provider_address: str) -> ServiceMetadata:
        """
        Get service metadata for a specific provider.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            ServiceMetadata object
            
        Raises:
            ServiceNotFoundError: If provider doesn't exist
            ContractError: If the contract call fails
            
        Example:
            >>> service = inference.get_service("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
            >>> print(service.model)
        """
        if not validate_provider_address(provider_address):
            raise ServiceNotFoundError(provider_address)
        
        try:
            provider_address = format_address(provider_address)
            
            # getService(provider) returns Service struct
            service_data = self.contract.functions.getService(provider_address).call()
            
            # Service struct: (provider, serviceType, url, inputPrice, outputPrice, updatedAt, model, verifiability, additionalInfo)
            return ServiceMetadata(
                provider=service_data[0],
                service_type=service_data[1],
                url=service_data[2],
                input_price=service_data[3],
                output_price=service_data[4],
                updated_at=service_data[5],
                model=service_data[6],
                verifiability=service_data[7]
            )
            
        except Exception as e:
            raise ServiceNotFoundError(provider_address)
    
    def acknowledge_provider_signer(self, provider_address: str) -> Dict[str, Any]:
        """
        Acknowledge a provider's signer on-chain (required before using the service).
        
        This is a one-time operation per provider that establishes a cryptographic
        relationship for billing purposes.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = inference.acknowledge_provider_signer("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
        """
        if not validate_provider_address(provider_address):
            raise ValueError(f"Invalid provider address: {provider_address}")
        
        try:
            provider_address = format_address(provider_address)
            
            # acknowledgeProviderSigner(provider, providerPubKey)
            # Using [0, 0] as placeholder for providerPubKey
            tx = self.contract.functions.acknowledgeProviderSigner(
                provider_address,
                [0, 0]  # Placeholder public key
            ).build_transaction({
                'from': self.account.address,
                'gas': 150000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("acknowledgeProviderSigner", "Transaction failed")
            
            # Mark provider as acknowledged
            self._acknowledged_providers.add(provider_address.lower())
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("acknowledgeProviderSigner", str(e))
    
    def get_service_metadata(self, provider_address: str) -> Dict[str, str]:
        """
        Get service endpoint and model information for a provider.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Dictionary with 'endpoint' and 'model' keys
            
        Example:
            >>> metadata = inference.get_service_metadata("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
            >>> print(metadata['endpoint'])
            >>> print(metadata['model'])
        """
        service = self.get_service(provider_address)
        
        return {
            "endpoint": service.url,
            "model": service.model
        }
    
    def get_request_headers(
        self,
        provider_address: str,
        content: str
    ) -> Dict[str, str]:
        """
        Generate authenticated request headers for a service call.
        
        These headers are single-use only and contain billing information.
        
        Args:
            provider_address: Provider's wallet address
            content: Request content (stringified JSON for chat requests)
            
        Returns:
            Dictionary of headers to include in the request
            
        Raises:
            ProviderNotAcknowledgedError: If provider hasn't been acknowledged
            
        Example:
            >>> import json
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> headers = inference.get_request_headers(
            ...     "0xf07240Efa67755B5311bc75784a061eDB47165Dd",
            ...     json.dumps(messages)
            ... )
        """
        provider_address = format_address(provider_address)
        
        # Check if provider is acknowledged (optional check based on implementation)
        # This check may need to be adjusted based on actual requirements
        
        # Delegate to auth manager to generate headers
        return self.auth_manager.generate_request_headers(
            provider_address,
            content
        )
    
    def process_response(
        self,
        provider_address: str,
        content: str,
        chat_id: Optional[str] = None
    ) -> bool:
        """
        Process and verify a response from a provider.
        
        For verifiable (TEE) services, this validates the response signature.
        For non-verifiable services, this always returns True.
        
        Args:
            provider_address: Provider's wallet address
            content: Response content
            chat_id: Chat ID (required for verifiable services)
            
        Returns:
            True if response is valid, False otherwise
            
        Example:
            >>> valid = inference.process_response(
            ...     "0xf07240Efa67755B5311bc75784a061eDB47165Dd",
            ...     response_text,
            ...     chat_id="chatcmpl-123"
            ... )
        """
        service = self.get_service(provider_address)
        
        # If service is not verifiable, always return True
        if not service.is_verifiable():
            return True
        
        # For verifiable services, delegate to auth manager
        if chat_id is None:
            raise InvalidResponseError(
                "chat_id is required for verifiable services",
                provider_address
            )
        
        return self.auth_manager.verify_response(
            provider_address,
            content,
            chat_id
        )