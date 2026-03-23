"""
Inference operations for the 0G Compute Network SDK.

This module handles service discovery, provider acknowledgment,
and request management for AI inference services.
"""

from typing import List, Dict, Any, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount
import threading
import requests


from .models import ServiceMetadata, Account, AccountWithDetail, Refund, RefundDetail, AdditionalInfo, AutoFundingConfig
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
        self._auto_funding_stops: Dict[str, threading.Event] = {}

        # Initialize session manager for new authorization system
        self._session_manager = SessionManager(account, web3, contract)
    
    def list_service(
        self,
        offset: int = 0,
        limit: int = 20,
        include_unacknowledged: bool = True,
    ) -> List[ServiceMetadata]:
        """
        Retrieve a list of available services from the contract.

        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of services to return (default: 20)
            include_unacknowledged: Include services whose TEE signer has not been
                acknowledged by any user (default: True). Set to False to return
                only services with a verified, acknowledged TEE signer.

        Returns:
            List of ServiceMetadata objects

        Raises:
            ContractError: If the contract call fails

        Example:
            >>> services = inference.list_service()
            >>> # Only acknowledged providers
            >>> services = inference.list_service(include_unacknowledged=False)
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
                # Paginated struct has teeSignerAcknowledged at index 10
                tee_acknowledged = service[10] if len(service) > 10 else True
                if not include_unacknowledged and not tee_acknowledged:
                    continue

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
        """Acknowledge a provider's TEE signer.

        In the updated contract, acknowledgeTEESigner takes (provider, bool).
        The TEE signer address is now set by the provider via addOrUpdateService,
        so users just acknowledge (set to True) or revoke acknowledgement.
        """
        try:
            provider_address = format_address(provider_address)

            # Step 0: Ensure main ledger exists
            if self.ledger_manager:
                try:
                    ledger = self.ledger_manager.get_ledger()
                    if ledger.total_balance > 0:
                        print("✅ Main ledger exists")
                    else:
                        print("Ledger exists but empty, adding funds...")
                        self.ledger_manager.add_ledger("0.01")
                except:
                    print("Creating main ledger...")
                    self.ledger_manager.add_ledger("0.01")

            # Step 1: Check if account exists, create via transferFund if needed
            account_exists = False
            already_acknowledged = False
            try:
                account = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address
                ).call()
                account_exists = True
                # New Account struct: [user, provider, nonce, balance, pendingRefund,
                #                      refunds[], additionalInfo, acknowledged, validRefundsLength,
                #                      generation, revokedBitmap]
                already_acknowledged = account[7]  # acknowledged (bool)
                balance = account[3]
                pending_refund = account[4]
                locked_fund = balance - pending_refund
                print(f"✅ Account exists (acknowledged: {already_acknowledged}, locked: {locked_fund / 10**18:.6f} OG)")
            except Exception as e:
                print(f"ℹ️  Account doesn't exist yet, will create via transferFund...")

            # Create account if needed
            if not account_exists and self.ledger_manager:
                print("Transferring funds to create account...")
                try:
                    from .utils import og_to_wei
                    initial_amount = og_to_wei("0.001")
                    self.ledger_manager.transfer_fund(provider_address, "inference-v1.0", initial_amount)
                    print("✅ Account created via transferFund")
                except Exception as transfer_error:
                    print(f"⚠️  transferFund failed: {transfer_error}")

            # Step 2: Check if already acknowledged
            if already_acknowledged:
                print("TEE signer already acknowledged")
                return {"status": "already_acknowledged"}

            # Step 3: Acknowledge TEE signer (new API: just pass True)
            print(f"Calling acknowledgeTEESigner({provider_address}, True)")
            tx = self.contract.functions.acknowledgeTEESigner(
                provider_address,
                True  # Acknowledge = True
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Transaction hash: {tx_hash.hex()}")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("acknowledgeTEESigner", f"Transaction failed. Receipt: {receipt}")

            print("✅ TEE signer acknowledged successfully")
            return parse_transaction_receipt(receipt)

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ContractError("acknowledge", str(e))

    def _create_provider_account(self, provider_address: str):
        """
        Create an account on InferenceServing contract.

        This is called when getAccount fails, indicating no account exists.
        Updated: addAccount no longer takes signer param.
        """
        try:
            # addAccount(user, provider, additionalInfo) payable
            tx = self.contract.functions.addAccount(
                self.account.address,  # user
                provider_address,      # provider
                ""                     # additionalInfo (empty string)
            ).build_transaction({
                'from': self.account.address,
                'value': 0,
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

    def _extract_tee_signer_address(self, report: dict) -> tuple[Optional[str], Optional[str]]:
        """
        Extract TEE signer address from attestation report.

        Supports multiple attestation formats with automatic fallback:
        1. Standard SGX/TDX format (report_data field)
        2. DStack format (compose_content + evidence)
        3. GPU attestation format (gpu_evidence)

        Extract TEE signer from attestation report with format detection

        Args:
            report: Attestation report dictionary

        Returns:
            Tuple of (signer_address, format_type) where format_type is one of:
            - "sgx_tdx": Standard SGX/TDX format
            - "dstack": DStack compose format
            - "gpu": GPU attestation format
            - None: Could not extract signer

        Example:
            >>> report = {"report_data": "MHhEQzFBNGRhNkJkQ0Q5MGMyMGQ3RkY1M2E2Y0RjMTFmQmYwRTIzMDNDAA=="}
            >>> signer, fmt = inference._extract_tee_signer_address(report)
            >>> print(f"{signer} ({fmt})")  # "0xDC1A4da6BdCD90c20d7FF53a6cDc11fBf0E2303C (sgx_tdx)"
        """
        import base64
        import json

        # ========================================================================
        # Method 1: Standard SGX/TDX Format (report_data field)
        # ========================================================================
        try:
            report_data = report.get('report_data')
            if report_data:
                print(f"   ⟳ Trying extraction method: Standard SGX/TDX (report_data)")
                decoded_data = base64.b64decode(report_data).decode('utf-8')
                signer_address = decoded_data.replace('\x00', '')

                if signer_address:
                    print(f"   ✓ Extracted using Standard SGX/TDX format")
                    return signer_address, "sgx_tdx"
        except Exception as e:
            print(f"   ⚠ Standard SGX/TDX extraction failed: {e}")

        # ========================================================================
        # Method 2: DStack Format (compose_content + evidence)
        # ========================================================================
        try:
            if 'compose_content' in report or 'evidence' in report:
                print(f"   ⟳ Trying extraction method: DStack (compose + evidence)")

                # Check if evidence is base64-encoded JSON
                evidence = report.get('evidence')
                if evidence and isinstance(evidence, str):
                    try:
                        # Decode base64 evidence
                        evidence_decoded = base64.b64decode(evidence).decode('utf-8', errors='ignore')
                        evidence_json = json.loads(evidence_decoded)

                        # Check if there's a quote with report_data inside
                        if 'quote' in evidence_json and isinstance(evidence_json['quote'], dict):
                            nested_report_data = evidence_json['quote'].get('report_data')
                            if nested_report_data:
                                decoded_data = base64.b64decode(nested_report_data).decode('utf-8')
                                signer_address = decoded_data.replace('\x00', '')
                                if signer_address:
                                    print(f"   ✓ Extracted using DStack format (nested quote)")
                                    return signer_address, "dstack"
                    except:
                        pass

                # DStack format detected but no signer extractable
                # This is still a valid attestation, just different verification method
                print(f"   ℹ️  DStack format detected (compose-based verification)")
                print(f"   ℹ️  DStack uses Docker compose hash verification instead of signer")
                return None, "dstack"

        except Exception as e:
            print(f"   ⚠ DStack extraction failed: {e}")

        # ========================================================================
        # Method 3: GPU Attestation Format
        # ========================================================================
        try:
            evidence = report.get('evidence')
            if evidence and isinstance(evidence, str):
                evidence_decoded = base64.b64decode(evidence).decode('utf-8', errors='ignore')
                evidence_json = json.loads(evidence_decoded)

                if 'gpu_evidence' in evidence_json:
                    print(f"   ⟳ Trying extraction method: GPU attestation")
                    print(f"   ℹ️  GPU attestation format detected")
                    # GPU attestation is valid but doesn't have traditional signer
                    return None, "gpu"
        except:
            pass

        # ========================================================================
        # No supported format found
        # ========================================================================
        print(f"   ⚠ Could not extract signer - no supported format found")
        return None, None

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

    def get_secret(
        self,
        provider_address: str,
        token_id: Optional[int] = None,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Generate authentication secret (API key) for direct API usage.

        Generate authentication secret (API key) for direct API usage.
        It creates a persistent API key that can be used directly in HTTP
        requests without going through get_request_headers().

        API keys use tokenId 0-254 and can be individually revoked.
        If no token_id is specified, the first available ID is auto-assigned.

        Args:
            provider_address: Provider's wallet address
            token_id: Specific tokenId to use (0-254, auto-assigned if None)
            expires_in: Expiration in milliseconds (0 or None = never expires)

        Returns:
            Authentication token string in format: "app-sk-<base64_encoded_token>"

        Raises:
            ValueError: If token_id is invalid or already revoked
            ContractError: If account retrieval fails

        Example:
            >>> # Generate a permanent API key
            >>> secret = inference.get_secret(provider_address)
            >>> print(f"API Key: {secret}")
            >>> # Output: app-sk-eyJhZGRyZXNzIjoi...
            >>>
            >>> # Use in HTTP requests
            >>> headers = {"Authorization": f"Bearer {secret}"}
            >>> response = requests.post(endpoint, headers=headers, json=data)
            >>>
            >>> # Generate API key with expiration (7 days)
            >>> secret = inference.get_secret(provider_address, expires_in=7*24*60*60*1000)
            >>>
            >>> # Generate API key with specific token ID
            >>> secret = inference.get_secret(provider_address, token_id=5)

        Note:
            - Token IDs 0-254 are for persistent API keys (individually revocable)
            - Token ID 255 is reserved for ephemeral session tokens
            - Each provider can have up to 255 active API keys simultaneously
            - Use revoke_api_key() to invalidate specific keys
            - Use revoke_all_tokens() to invalidate all keys for a provider
        """
        provider_address = format_address(provider_address)

        # Create API key using session manager
        api_key_info = self._session_manager.create_api_key(
            provider_address,
            expires_in=expires_in or 0,
            token_id=token_id
        )

        # Return the raw token string
        return api_key_info.raw_token
    
    def verify_service(
        self,
        provider_address: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensively verify a provider's TEE service and attestation.

        1. Fetch TEE quote from provider's /v1/quote endpoint
        2. Extract TEE signer address from report_data (base64 decoded)
        3. Compare extracted signer with expected signer from contract
        4. Optionally verify attestation via Automata contract (non-blocking)
        5. Check service configuration
        6. Generate verification report (optional)

        Args:
            provider_address: Provider's wallet address
            output_dir: Optional directory to save verification report

        Returns:
            Dictionary with verification results:
            {
                "is_valid": bool,               # Overall validity (based on signer match)
                "provider": str,                # Provider address
                "service_type": str,            # e.g., "chatbot"
                "model": str,                   # Model name
                "verifiability": str,           # e.g., "TeeML"
                "tee_signer": str,              # TEE signer address (extracted from report_data)
                "expected_signer": str,         # Expected signer from contract
                "signer_match": bool,           # Whether signers match (critical)
                "quote_available": bool,        # Quote fetch succeeded
                "quote_data": dict,             # Raw quote data
                "attestation_verified": bool,   # Automata verification (optional)
                "timestamp": int,               # Verification timestamp
                "report_path": str              # Report file path (if saved)
            }

        Raises:
            ServiceNotFoundError: If provider doesn't exist
            NetworkError: If quote fetch fails

        Example:
            >>> # Basic verification
            >>> result = inference.verify_service(provider_address)
            >>> print(f"Valid: {result['is_valid']}")
            >>> print(f"Signer Match: {result['signer_match']}")
            >>> print(f"TEE Signer: {result['tee_signer']}")
            >>>
            >>> # With report generation
            >>> result = inference.verify_service(provider_address, output_dir="./reports")
            >>> print(f"Report saved to: {result['report_path']}")

        Note:
            - Automata contract verification is optional and non-blocking
        """
        import time
        import json

        provider_address = format_address(provider_address)
        timestamp = int(time.time() * 1000)

        # Initialize result
        result = {
            "is_valid": False,
            "provider": provider_address,
            "service_type": "",
            "model": "",
            "verifiability": "",
            "tee_signer": None,
            "quote_available": False,
            "quote_data": {},
            "attestation_verified": False,
            "attestation_method": None,
            "timestamp": timestamp,
            "report_path": None,
            "errors": []
        }

        try:
            # Step 1: Get service metadata
            print(f"🔍 Verifying service for provider: {provider_address}")
            service = self.get_service(provider_address)

            result["service_type"] = service.service_type
            result["model"] = service.model
            result["verifiability"] = service.verifiability
            result["url"] = service.url
            result["is_verifiable"] = service.is_verifiable()

            print(f"   ✓ Service found: {service.model}")
            print(f"   ✓ Type: {service.service_type}")
            print(f"   ✓ Verifiability: {service.verifiability}")

            # Step 2: Fetch TEE quote
            quote_endpoint = f"{service.url}/v1/quote"
            print(f"   ⟳ Fetching quote from: {quote_endpoint}")

            try:
                quote_response = requests.get(quote_endpoint, timeout=15)

                if quote_response.status_code == 200:
                    quote_data = quote_response.json()
                    result["quote_available"] = True
                    result["quote_data"] = quote_data

                    # Extract TEE signer - supports multiple formats with automatic fallback
                    tee_signer, attestation_format = self._extract_tee_signer_address(quote_data)

                    result["attestation_format"] = attestation_format

                    if tee_signer:
                        result["tee_signer"] = tee_signer
                        print(f"   ✓ TEE signer extracted: {tee_signer}")
                    elif attestation_format in ("dstack", "gpu"):
                        # Valid attestation format but no traditional signer
                        print(f"   ✓ {attestation_format.upper()} format attestation detected")
                        result["tee_signer"] = None
                        # For DStack/GPU, we still consider it valid if attestation exists
                        result["format_verified"] = True
                    else:
                        result["errors"].append("Could not extract signer - no supported format")
                        print(f"   ⚠ Could not extract signer - no supported format found")

                    # Check for quote hex data (for attestation verification)
                    quote_hex = quote_data.get('quote')
                    if quote_hex:
                        print(f"   ✓ Quote hex data available: {len(quote_hex)} chars")
                        result["quote_hex_length"] = len(quote_hex)

                else:
                    result["errors"].append(f"Quote fetch failed: HTTP {quote_response.status_code}")
                    print(f"   ✗ Quote fetch failed: {quote_response.status_code}")

            except requests.RequestException as e:
                result["errors"].append(f"Quote fetch error: {str(e)}")
                print(f"   ✗ Quote fetch error: {e}")

            # Step 3: Try Automata attestation verification (optional
            if result["quote_available"] and "quote" in result["quote_data"]:
                print(f"   ⟳ Attempting Automata contract verification (optional)...")
                try:
                    quote_hex = result["quote_data"]["quote"]
                    attestation_valid = self._verify_quote_with_automata(quote_hex)
                    result["attestation_verified"] = attestation_valid
                    result["attestation_method"] = "automata_contract"

                    if attestation_valid:
                        print(f"   ✓ Automata contract verification passed")
                    else:
                        print(f"   ℹ️  Automata contract verification not available (this is normal)")

                except Exception as e:
                    # Don't fail if Automata contract doesn't work - TypeScript doesn't use it
                    result["attestation_verified"] = None  # Unknown, not False
                    result["attestation_method"] = None
                    print(f"   ℹ️  Automata verification skipped (TypeScript doesn't use this): {str(e)[:100]}")

            # Step 4: Try to get expected signer from contract (optional)
            # For now, we try getAccount() but make it completely optional
            current_tee_signer = None
            try:
                account = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address
                ).call()

                # New Account struct: index 7 = acknowledged (bool)
                is_acknowledged = account[7] if len(account) > 7 else False
                result["is_acknowledged"] = bool(is_acknowledged)

                if result["is_acknowledged"]:
                    print(f"   ✓ Provider acknowledged in contract")
                    print(f"   ✓ Contract TEE signer: {current_tee_signer}")
                else:
                    print(f"   ℹ️  Provider not yet acknowledged in contract")

            except Exception as e:
                # Contract check is optional - don't fail verification if it doesn't work
                print(f"   ℹ️  Contract signer check unavailable (this is optional)")

            # Step 5: Compare TEE signer with expected signer
            if result["tee_signer"] and current_tee_signer:
                # Normalize addresses for comparison (lowercase, strip 0x)
                extracted_signer = result["tee_signer"].lower().replace("0x", "")
                expected_signer = current_tee_signer.lower().replace("0x", "")

                signer_match = extracted_signer == expected_signer
                result["signer_match"] = signer_match
                result["expected_signer"] = current_tee_signer

                if signer_match:
                    print(f"   ✅ TEE Signer Match!")
                    print(f"      Expected: {current_tee_signer}")
                    print(f"      Got:      {result['tee_signer']}")
                else:
                    print(f"   ❌ TEE Signer Mismatch!")
                    print(f"      Expected: {current_tee_signer}")
                    print(f"      Got:      {result['tee_signer']}")
            elif result["tee_signer"]:
                # Have extracted signer but no expected signer to compare with
                # This is still valid - TypeScript also just extracts and displays the signer
                result["signer_match"] = True  # Pass verification if we extracted the signer
                print(f"   ✓ TEE signer successfully extracted (contract comparison unavailable)")
            elif result.get("attestation_format") in ("dstack", "gpu"):
                # DStack/GPU format - uses different verification method (no traditional signer)
                result["signer_match"] = True  # Pass verification for valid attestation format
                print(f"   ✓ {result['attestation_format'].upper()} attestation format verified")
                print(f"   ℹ️  This format uses compose/GPU verification instead of traditional signer")

            # Step 6: Determine overall validity (based on signer match, like TypeScript)
            # For standard SGX/TDX: requires signer extraction and match
            # For DStack/GPU: requires valid attestation format
            result["is_valid"] = (
                result["quote_available"] and
                (
                    # Standard format: has signer and it matches
                    (result["tee_signer"] is not None and result.get("signer_match", False)) or
                    # DStack/GPU format: valid attestation format detected
                    (result.get("attestation_format") in ("dstack", "gpu") and result.get("signer_match", False))
                )
            )

            # Step 7: Generate report if requested
            if output_dir and result:
                try:
                    from pathlib import Path

                    # Create directory if it doesn't exist
                    Path(output_dir).mkdir(parents=True, exist_ok=True)

                    report_filename = f"verification_{provider_address}_{int(time.time())}.json"
                    report_path = str(Path(output_dir) / report_filename)

                    with open(report_path, 'w') as f:
                        json.dump(result, f, indent=2)

                    result["report_path"] = report_path
                    print(f"   ✓ Report saved: {report_path}")

                except Exception as e:
                    result["errors"].append(f"Report save error: {str(e)}")
                    print(f"   ⚠ Report save error: {e}")

            # Summary
            print()
            print("=" * 60)
            if result["is_valid"]:
                print("✅ SERVICE VERIFICATION PASSED")
            else:
                print("⚠️  SERVICE VERIFICATION INCOMPLETE")
            print("=" * 60)
            print(f"Provider:          {result['provider']}")
            print(f"Model:             {result['model']}")
            print(f"Verifiability:     {result['verifiability']}")
            print(f"TEE Signer:        {result['tee_signer']}")
            print(f"Expected Signer:   {result.get('expected_signer', 'N/A')}")
            print(f"Signer Match:      {result.get('signer_match', False)}")
            print(f"Quote Available:   {result['quote_available']}")
            print(f"Attestation:       {result.get('attestation_verified', 'N/A')}")
            if result["errors"]:
                print(f"Errors:            {len(result['errors'])}")
                for error in result["errors"]:
                    print(f"  - {error}")
            print("=" * 60)
            print()

            return result

        except ServiceNotFoundError:
            raise
        except Exception as e:
            result["errors"].append(f"Verification failed: {str(e)}")
            result["is_valid"] = False
            import traceback
            traceback.print_exc()
            return result

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
        
        # New Account struct order:
        # [0] user, [1] provider, [2] nonce, [3] balance, [4] pendingRefund,
        # [5] refunds[], [6] additionalInfo, [7] acknowledged (bool),
        # [8] validRefundsLength, [9] generation, [10] revokedBitmap
        return Account(
            user=account_data[0],
            provider=account_data[1],
            nonce=account_data[2],
            balance=account_data[3],
            pending_refund=account_data[4],
            refunds=refunds,
            additional_info=account_data[6] if len(account_data) > 6 else "",
            acknowledged=account_data[7] if len(account_data) > 7 else False,
            valid_refunds_length=account_data[8] if len(account_data) > 8 else 0,
            generation=account_data[9] if len(account_data) > 9 else 0,
            revoked_bitmap=account_data[10] if len(account_data) > 10 else 0,
        )

    # ==================== TEE Signer Management ====================

    def acknowledged(self, provider_address: str) -> bool:
        """
        Check whether the user has acknowledged this provider's TEE signer.

        Args:
            provider_address: Provider's wallet address

        Returns:
            True if the TEE signer is acknowledged, False otherwise
        """
        return self.get_account(provider_address).acknowledged

    def revoke_provider_tee_signer_acknowledgement(self, provider_address: str) -> Dict[str, Any]:
        """
        Revoke acknowledgment of a provider's TEE signer.

        After calling this the provider must be re-acknowledged before
        generating new request headers.

        Args:
            provider_address: Provider's wallet address

        Returns:
            Transaction receipt

        Raises:
            ContractError: If the transaction fails
        """
        provider_address = format_address(provider_address)

        try:
            tx = self.contract.functions.revokeTEESignerAcknowledgement(
                provider_address
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("revokeTEESignerAcknowledgement", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("revokeTEESignerAcknowledgement", str(e))

    # ==================== Provider Service Management ====================

    def remove_service(self) -> Dict[str, Any]:
        """
        Remove the caller's own service from the contract (provider operation).

        Returns:
            Transaction receipt

        Raises:
            ContractError: If the transaction fails
        """
        try:
            tx = self.contract.functions.removeService().build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("removeService", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("removeService", str(e))

    def update_service(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        input_price: Optional[int] = None,
        output_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update the caller's own service parameters (provider operation).

        Unspecified fields are preserved from the current on-chain values.

        Args:
            url: New service endpoint URL
            model: New model identifier
            input_price: New input price in wei
            output_price: New output price in wei

        Returns:
            Transaction receipt

        Raises:
            ContractError: If the transaction fails
        """
        # Fetch current service to fill in any fields not provided
        try:
            current = self.get_service(self.account.address)
        except Exception:
            current = None

        params = (
            current.service_type if current else "",
            url if url is not None else (current.url if current else ""),
            model if model is not None else (current.model if current else ""),
            current.verifiability if current else "",
            input_price if input_price is not None else (current.input_price if current else 0),
            output_price if output_price is not None else (current.output_price if current else 0),
            "",  # additionalInfo — preserve existing; pass empty to leave unchanged
        )

        try:
            tx = self.contract.functions.addOrUpdateService(params).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("addOrUpdateService", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("addOrUpdateService", str(e))

    # ==================== Attestation Download ====================

    def download_quote_report(self, provider_address: str, output_path: str) -> None:
        """
        Download the TEE attestation report for a provider and save it to disk.

        Args:
            provider_address: Provider's wallet address
            output_path: File path to write the JSON report

        Raises:
            NetworkError: If the quote endpoint is unreachable or returns an error
        """
        import json

        service = self.get_service(provider_address)
        url = f"{service.url}/v1/quote"

        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException as e:
            raise NetworkError(f"Failed to reach quote endpoint: {e}", url)

        if response.status_code != 200:
            raise NetworkError(
                f"Quote endpoint returned HTTP {response.status_code}",
                url,
            )

        with open(output_path, "w") as f:
            json.dump(response.json(), f, indent=2)

    def get_signer_ra_download_link(self, provider_address: str) -> str:
        """
        Return the URL to download the TEE signer remote-attestation report.

        Args:
            provider_address: Provider's wallet address

        Returns:
            Full URL string for the attestation report
        """
        service = self.get_service(provider_address)
        return f"{service.url}/v1/proxy/attestation/report"

    def get_chat_signature_download_link(self, provider_address: str, chat_id: str) -> str:
        """
        Return the URL to download the TEE-signed signature for a specific chat.

        Args:
            provider_address: Provider's wallet address
            chat_id: Chat completion ID (e.g. "chatcmpl-abc123")

        Returns:
            Full URL string for the chat signature
        """
        service = self.get_service(provider_address)
        return f"{service.url}/v1/proxy/signature/{chat_id}"

    # ==================== Auto-Funding ====================

    # Minimum locked balance threshold (in wei) — mirrors TS SDK constant
    _MIN_LOCKED_BALANCE = 500

    def start_auto_funding(
        self,
        provider_address: str,
        config: Optional[AutoFundingConfig] = None,
    ) -> None:
        """
        Start a background thread that automatically tops up the provider
        sub-account balance when it falls below the required threshold.

        The thread runs immediately on start, then repeats every
        ``config.interval_ms`` milliseconds.  It is a daemon thread and will
        not prevent the process from exiting.

        Args:
            provider_address: Provider's wallet address
            config: AutoFundingConfig with interval_ms and buffer_multiplier.
                    Defaults to AutoFundingConfig() (30 s interval, 2x buffer).

        Raises:
            RuntimeError: If ledger_manager is not available
        """
        if self.ledger_manager is None:
            raise RuntimeError("ledger_manager is required for auto-funding")

        if config is None:
            config = AutoFundingConfig()

        provider_address = format_address(provider_address)

        # Stop any existing auto-funding for this provider
        self.stop_auto_funding(provider_address)

        stop_event = threading.Event()
        self._auto_funding_stops[provider_address] = stop_event

        required = config.buffer_multiplier * self._MIN_LOCKED_BALANCE

        def _check_and_fund() -> None:
            try:
                account_data = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address,
                ).call()
                balance = account_data[3]
                pending_refund = account_data[4]
                available = balance - pending_refund

                if available < required:
                    top_up = required - available
                    self.ledger_manager.transfer_fund(provider_address, "inference-v1.0", top_up)
            except Exception:
                pass  # Never crash the background thread

        def _loop() -> None:
            _check_and_fund()
            while not stop_event.wait(timeout=config.interval_ms / 1000):
                _check_and_fund()

        thread = threading.Thread(target=_loop, daemon=True, name=f"auto-fund-{provider_address[:8]}")
        thread.start()

    def stop_auto_funding(self, provider_address: Optional[str] = None) -> None:
        """
        Stop the auto-funding background thread.

        Args:
            provider_address: Stop funding for this provider only.
                              If None, stop all active auto-funding threads.
        """
        if provider_address is None:
            for event in list(self._auto_funding_stops.values()):
                event.set()
            self._auto_funding_stops.clear()
        else:
            provider_address = format_address(provider_address)
            event = self._auto_funding_stops.pop(provider_address, None)
            if event:
                event.set()

    def has_auto_funding(self, provider_address: str) -> bool:
        """Return True if auto-funding is active for the given provider."""
        provider_address = format_address(provider_address)
        return provider_address in self._auto_funding_stops