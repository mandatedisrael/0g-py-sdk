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


from .models import ServiceMetadata, Account, AccountWithDetail, Refund, RefundDetail, AdditionalInfo
from .exceptions import (
    ContractError,
    ServiceNotFoundError,
    ProviderNotAcknowledgedError,
    InvalidResponseError,
    NetworkError
)
from .utils import format_address, validate_provider_address, parse_transaction_receipt
from .session import SessionManager, SessionMode, ApiKeyInfo
from .extractors import (
    Extractor,
    create_extractor,
    ChatBotExtractor,
    TextToImageExtractor,
    ImageEditingExtractor,
    SpeechToTextExtractor
)


class InferenceManager:
    """
    Manages inference operations for the 0G Compute Network.
    
    This class handles:
    - Service discovery (listing available providers)
    - Provider acknowledgment
    - Service metadata retrieval
    - Request header generation (new session token system)
    - API key management
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
            auth_manager: AuthManager instance for header generation (legacy)
            ledger_manager: LedgerManager instance for fund transfers
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
        self.auth_manager = auth_manager
        self.ledger_manager = ledger_manager
        self._acknowledged_providers = set()
        
        # Initialize session manager for new authorization system
        self._session_manager = SessionManager(account, web3, contract)
    
    def list_service(
        self,
        offset: int = 0,
        limit: int = 20
    ) -> List[ServiceMetadata]:
        """
        Retrieve a list of available services from the contract.
        
        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of services to return (default: 50)
        
        Returns:
            List of ServiceMetadata objects
            
        Raises:
            ContractError: If the contract call fails
            
        Example:
            >>> # Get first 50 services
            >>> services = inference.list_service()
            >>> 
            >>> # Get next 50 services
            >>> services = inference.list_service(offset=50, limit=50)
        """
        try:
            # Try paginated version first (new contract)
            try:
                result = self.contract.functions.getAllServices(offset, limit).call()
                # New contract returns [services[], total] or (services[], total)
                if isinstance(result, (list, tuple)) and len(result) == 2:
                    services_data = result[0]
                else:
                    services_data = result
            except Exception:
                # Fall back to non-paginated version (old contract)
                services_data = self.contract.functions.getAllServices().call()

            services = []
            for service in services_data:
                # Service struct: (provider, serviceType, url, inputPrice, outputPrice, updatedAt, model, verifiability, additionalInfo, ...)
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
    
    def get_extractor(self, provider_address: str) -> Extractor:
        """
        Get the appropriate billing extractor for a service.
        
        Creates an extractor that can extract input/output counts from
        requests and responses for billing purposes. The extractor type
        is determined by the service type (chatbot, text-to-image, etc.).
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Extractor instance for the service type
            
        Raises:
            ServiceNotFoundError: If provider doesn't exist
            ValueError: If service type is unknown
            
        Example:
            >>> extractor = inference.get_extractor(provider_address)
            >>> 
            >>> # For chatbot services, extract token counts from response
            >>> usage_json = '{"prompt_tokens": 150, "completion_tokens": 300}'
            >>> input_tokens = extractor.get_input_count(usage_json)
            >>> output_tokens = extractor.get_output_count(usage_json)
            >>> 
            >>> # Calculate cost
            >>> service = extractor.get_svc_info()
            >>> total_cost = (input_tokens * service.input_price + 
            ...               output_tokens * service.output_price)
        """
        service = self.get_service(provider_address)
        return create_extractor(service)
    
    def get_request_headers(
        self,
        provider_address: str,
        content: str = "",
        use_legacy: bool = False
    ) -> Dict[str, str]:
        """
        Generate authenticated request headers for a service call.
        
        Uses the new session token authorization system by default.
        The content parameter is optional for the new system but kept
        for backward compatibility.
        
        Args:
            provider_address: Provider's wallet address
            content: Request content (optional, used for legacy headers)
            use_legacy: Use deprecated header-based auth (default: False)
            
        Returns:
            Dictionary of headers to include in the request
            
        Example:
            >>> # New session token auth (recommended)
            >>> headers = inference.get_request_headers(provider_address)
            >>> 
            >>> # Legacy auth (deprecated)
            >>> headers = inference.get_request_headers(provider_address, content, use_legacy=True)
        """
        provider_address = format_address(provider_address)
        
        if use_legacy:
            # Use deprecated header-based authentication
            return self.auth_manager.generate_request_headers(
                provider_address,
                content
            )
        
        # Use new session token authentication
        return self._session_manager.get_request_headers(provider_address)
    
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
    
    # ==================== API Key Management ====================
    
    def create_api_key(
        self,
        provider_address: str,
        expires_in: Optional[int] = None,
        token_id: Optional[int] = None
    ) -> ApiKeyInfo:
        """
        Create a persistent API key for a provider.
        
        API keys use tokenId 0-254 and can be individually revoked.
        They're useful for long-term access or sharing with applications.
        
        Args:
            provider_address: Provider's wallet address
            expires_in: Expiration in milliseconds (None = never expires)
            token_id: Specific tokenId to use (0-254, auto-assigned if None)
            
        Returns:
            ApiKeyInfo with token_id, created_at, expires_at, and raw_token
            
        Example:
            >>> api_key = inference.create_api_key(provider_address)
            >>> print(f"Token: {api_key.raw_token}")
            >>> # Use in requests:
            >>> headers = {"Authorization": f"Bearer {api_key.raw_token}"}
        """
        provider_address = format_address(provider_address)
        return self._session_manager.create_api_key(
            provider_address,
            expires_in=expires_in,
            token_id=token_id
        )
    
    def revoke_api_key(self, provider_address: str, token_id: int) -> Dict[str, Any]:
        """
        Revoke a specific API key by its tokenId.
        
        Args:
            provider_address: Provider's wallet address
            token_id: Token ID to revoke (0-254)
            
        Returns:
            Transaction receipt
            
        Raises:
            ValueError: If token_id is 255 (ephemeral tokens can't be individually revoked)
            ContractError: If the transaction fails
        """
        if token_id == 255:
            raise ValueError(
                "Cannot revoke ephemeral token individually. Use revoke_all_tokens() instead."
            )
        
        provider_address = format_address(provider_address)
        
        try:
            tx = self.contract.functions.revokeToken(
                provider_address,
                token_id
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("revokeToken", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("revokeToken", str(e))
    
    def revoke_all_tokens(self, provider_address: str) -> Dict[str, Any]:
        """
        Revoke all tokens (ephemeral and persistent) for a provider.
        
        This increments the generation, invalidating all existing tokens.
        After calling this, new tokens must be generated.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Transaction receipt
        """
        provider_address = format_address(provider_address)
        
        try:
            tx = self.contract.functions.revokeAllTokens(
                provider_address
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("revokeAllTokens", "Transaction failed")
            
            # Clear session cache
            self._session_manager.clear_session_cache(provider_address)
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("revokeAllTokens", str(e))
    
    # ==================== Account Management ====================
    
    def get_account(self, provider_address: str) -> Account:
        """
        Get account information for a specific provider.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            Account object with balance, nonce, refunds, etc.
            
        Raises:
            ContractError: If account doesn't exist or query fails
            
        Example:
            >>> account = inference.get_account(provider_address)
            >>> print(f"Balance: {account.balance}")
            >>> print(f"Nonce: {account.nonce}")
        """
        provider_address = format_address(provider_address)
        
        try:
            account_data = self.contract.functions.getAccount(
                self.account.address,
                provider_address
            ).call()
            
            return self._parse_account(account_data)
            
        except Exception as e:
            raise ContractError("getAccount", str(e))
    
    def get_account_with_detail(
        self,
        provider_address: str
    ) -> AccountWithDetail:
        """
        Get account with detailed refund information.
        
        Returns account data plus refund details with remaining time
        until each refund can be processed.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            AccountWithDetail with account and refund_details
            
        Example:
            >>> detail = inference.get_account_with_detail(provider_address)
            >>> for refund in detail.refund_details:
            ...     print(f"Amount: {refund.amount}, Remaining: {refund.remain_time}s")
        """
        provider_address = format_address(provider_address)
        
        try:
            # Fetch account and lock time in parallel would be ideal,
            # but Python doesn't have easy async here, so sequential
            account_data = self.contract.functions.getAccount(
                self.account.address,
                provider_address
            ).call()
            
            # Get lock time from contract
            try:
                lock_time = self.contract.functions.lockTime().call()
            except Exception:
                lock_time = 86400  # Default 24 hours
            
            account = self._parse_account(account_data)
            
            # Calculate refund details
            import time
            now = int(time.time())
            refund_details = []
            
            for i, refund in enumerate(account.refunds):
                if i >= account.valid_refunds_length:
                    break
                if refund.amount == 0:
                    continue
                
                elapsed = now - refund.created_at
                remain_time = max(0, lock_time - elapsed)
                
                refund_details.append(RefundDetail(
                    amount=refund.amount,
                    remain_time=remain_time
                ))
            
            return AccountWithDetail(
                account=account,
                refund_details=refund_details
            )
            
        except Exception as e:
            raise ContractError("getAccountWithDetail", str(e))
    
    def list_accounts(
        self,
        offset: int = 0,
        limit: int = 50
    ) -> List[Account]:
        """
        List all accounts for the current user.
        
        Returns accounts across all providers that this user
        has interacted with.
        
        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of accounts to return (default: 50)
            
        Returns:
            List of Account objects
            
        Example:
            >>> accounts = inference.list_accounts()
            >>> for acc in accounts:
            ...     print(f"Provider: {acc.provider}, Balance: {acc.balance}")
        """
        try:
            # Try paginated version first
            try:
                result = self.contract.functions.getAllAccounts(offset, limit).call()
                if isinstance(result, tuple) and len(result) >= 1:
                    accounts_data = result[0] if isinstance(result[0], (list, tuple)) else result
                else:
                    accounts_data = result
            except Exception:
                # Fall back to non-paginated or alternative method
                try:
                    accounts_data = self.contract.functions.getAllAccounts().call()
                except Exception:
                    # Contract might not have this method, return empty
                    return []
            
            return [self._parse_account(acc) for acc in accounts_data]
            
        except Exception as e:
            raise ContractError("listAccounts", str(e))
    
    def _parse_account(self, account_data: tuple) -> Account:
        """
        Parse account data from contract response.
        
        Account struct:
        (user, provider, nonce, balance, pendingRefund, signer[2],
         refunds[], additionalInfo, providerPubKey[2], teeSignerAddress,
         validRefundsLength, generation?, revokedBitmap?)
        """
        # Parse refunds
        refunds = []
        refunds_data = account_data[6] if len(account_data) > 6 else []
        for ref in refunds_data:
            refunds.append(Refund(
                index=ref[0],
                amount=ref[1],
                created_at=ref[2],
                processed=ref[3]
            ))
        
        return Account(
            user=account_data[0],
            provider=account_data[1],
            nonce=account_data[2],
            balance=account_data[3],
            pending_refund=account_data[4],
            signer=list(account_data[5]) if len(account_data) > 5 else [0, 0],
            refunds=refunds,
            additional_info=account_data[7] if len(account_data) > 7 else "",
            provider_pub_key=list(account_data[8]) if len(account_data) > 8 else [0, 0],
            tee_signer_address=account_data[9] if len(account_data) > 9 else "",
            valid_refunds_length=account_data[10] if len(account_data) > 10 else 0,
            generation=account_data[11] if len(account_data) > 11 else 0,
            revoked_bitmap=account_data[12] if len(account_data) > 12 else 0,
        )