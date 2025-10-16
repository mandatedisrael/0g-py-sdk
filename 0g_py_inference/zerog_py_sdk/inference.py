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
        auth_manager: Any,  # Avoid circular import, type will be AuthManager
        ledger_manager: Any = None  # Add ledger manager for account creation
    ):
        """
        Initialize the InferenceManager.

        Args:
            contract: Web3 contract instance
            account: Local account for signing transactions
            web3: Web3 instance
            auth_manager: AuthManager instance for header generation
            ledger_manager: LedgerManager instance for fund transfers
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
        self.auth_manager = auth_manager
        self.ledger_manager = ledger_manager
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
        """Acknowledge a provider's TEE signer."""
        try:
            provider_address = format_address(provider_address)

            # Step 0: Ensure main ledger exists
            if self.ledger_manager:
                try:
                    ledger = self.ledger_manager.get_ledger()
                    # Check if ledger actually has balance (not just a zero-initialized struct)
                    if ledger.total_balance > 0:
                        print("✅ Main ledger exists")
                    else:
                        print("Ledger exists but empty, adding funds...")
                        self.ledger_manager.add_ledger("0.01")
                except:
                    print("Creating main ledger...")
                    self.ledger_manager.add_ledger("0.01")  # Create with 0.01 OG

            # Step 1: Check if account exists, create it via transferFund if needed
            # This matches the official TS SDK's handleFirstRound logic
            need_transfer = False
            try:
                account = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address
                ).call()
                current_tee_signer = account[9]  # teeSignerAddress field
                print(f"✅ Account exists for provider (TEE signer: {current_tee_signer})")
                # Check if balance is too low (less than threshold)
                balance = account[3]  # balance field
                pending_refund = account[4]  # pendingRefund field
                locked_fund = balance - pending_refund
                # If balance is very low, we need to top up
                if locked_fund < 100000000000:  # Arbitrary small threshold
                    need_transfer = True
            except Exception as e:
                print(f"ℹ️  Account doesn't exist yet, will create via transferFund...")
                need_transfer = True

            # Transfer funds to create account or top up if needed
            # Use a reasonable initial amount: 0.001 OG = 1000000000000000 wei
            if need_transfer and self.ledger_manager:
                print("Transferring funds to create/top-up account...")
                try:
                    from .utils import og_to_wei
                    initial_amount = og_to_wei("0.001")  # 0.001 OG
                    self.ledger_manager.transfer_fund(provider_address, "inference", initial_amount)
                    print("✅ Account created/topped-up via transferFund")
                except Exception as transfer_error:
                    print(f"⚠️  transferFund failed: {transfer_error}")
                    # Continue anyway - maybe account was created by another process
            
            # Step 2: Get quote
            service = self.get_service(provider_address)
            quote_endpoint = f"{service.url}/v1/quote"
            
            print(f"Getting quote from: {quote_endpoint}")
            quote_response = requests.get(quote_endpoint, timeout=10)
            
            if quote_response.status_code != 200:
                raise ContractError("acknowledge", f"Failed to get quote: {quote_response.status_code}")
            
            quote_data = quote_response.json()
            provider_signer = quote_data.get('provider_signer')  # This is an ADDRESS
            
            if not provider_signer:
                raise ContractError("acknowledge", "No provider_signer in quote")
            
            print(f"Got provider signer (TEE address): {provider_signer}")
            
            # Step 3: Check if already acknowledged
            try:
                account = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address
                ).call()
                current_tee_signer = account[9]  # teeSignerAddress field
                
                if current_tee_signer.lower() == provider_signer.lower():
                    print("TEE signer already acknowledged")
                    return {"status": "already_acknowledged"}
            except:
                pass
            
            # Step 4: Use acknowledgeTEESigner, NOT acknowledgeProviderSigner!
            print(f"Calling acknowledgeTEESigner({provider_address}, {provider_signer})")
            tx = self.contract.functions.acknowledgeTEESigner(
                provider_address,
                provider_signer  # Just pass the address directly
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,  # Increased gas
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Transaction hash: {tx_hash.hex()}")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Receipt: {receipt}")

            if receipt['status'] != 1:
                raise ContractError("acknowledgeTEESigner", f"Transaction failed. Receipt: {receipt}")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ContractError("acknowledge", str(e))

    def _create_provider_account(self, provider_address: str):
        """
        Create an account on InferenceServing contract.

        This is called when getAccount fails, indicating no account exists.
        We use addAccount with minimal parameters.
        """
        try:
            # addAccount(user, provider, signer[2], additionalInfo) payable
            # Use empty signer and info for now
            tx = self.contract.functions.addAccount(
                self.account.address,  # user
                provider_address,      # provider
                [0, 0],               # signer (empty uint256[2])
                ""                    # additionalInfo (empty string)
            ).build_transaction({
                'from': self.account.address,
                'value': 0,  # No value needed
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("addAccount", "Transaction failed")

            print("✅ Account created on InferenceServing")

        except Exception as e:
            raise ContractError("addAccount", str(e))

    def _verify_quote_with_automata(self, quote: str) -> bool:
        """
        Verify TEE quote using Automata contract.
        
        Args:
            quote: Hex-encoded quote from provider
            
        Returns:
            True if quote is valid, False otherwise
        """
        from .contracts.abis import AUTOMATA_CONTRACT_ADDRESS
        
        # Automata contract ABI for verifyQuote function
        automata_abi = [{
            "inputs": [{"internalType": "bytes", "name": "quote", "type": "bytes"}],
            "name": "verifyQuote",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function"
        }]
        
        automata_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(AUTOMATA_CONTRACT_ADDRESS),
            abi=automata_abi
        )
        
        try:
            # Convert hex string to bytes
            quote_bytes = bytes.fromhex(quote.replace('0x', ''))
            is_valid = automata_contract.functions.verifyQuote(quote_bytes).call()
            return is_valid
        except Exception as e:
            print(f"Quote verification error: {e}")
            return False

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
            "endpoint": f"{service.url}/v1/proxy",
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