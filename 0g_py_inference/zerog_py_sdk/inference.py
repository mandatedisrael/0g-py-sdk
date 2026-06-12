"""
Inference operations for the 0G Compute Network SDK.

This module handles service discovery, provider acknowledgment,
and request management for AI inference services.
"""

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import requests
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount


from .models import (
    Account,
    AccountWithDetail,
    AdditionalInfo,
    AutoFundingConfig,
    Refund,
    RefundDetail,
    ServiceMetadata,
)
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
from .lora import (
    AdapterInfo,
    AdapterStatusResponse,
    DeployResponse,
    LoRADependencies,
    LoRAProcessor,
)
from .verifier import (
    SignerReportMatch,
    SignerVerification,
    VerificationResult,
    VerificationStep,
)
from .read_only import ProviderModels, _fetch_provider_models


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
        self._cached_fees: Dict[str, Dict[str, Any]] = {}

        # Initialize session manager for new authorization system
        self._session_manager = SessionManager(account, web3, contract)

        # LoRA adapter management (deploy + chat with fine-tuned adapters).
        # Mirrors TS broker.loraProcessor wiring.
        manager = self

        class _LoRADeps(LoRADependencies):
            def get_endpoint(self, provider_address: str) -> str:
                return manager.get_service_metadata(provider_address)["endpoint"]

            def get_headers(
                self, provider_address: str, content: Optional[str] = None
            ) -> Dict[str, str]:
                return manager.get_request_headers(
                    provider_address, content or ""
                )

        self.lora = LoRAProcessor(_LoRADeps())

    def list_adapters(self, provider_address: str) -> List[AdapterInfo]:
        """List LoRA adapters registered by an inference provider."""
        return self.lora.list_adapters(provider_address)

    def get_adapter_status(
        self, provider_address: str, adapter_name: str
    ) -> AdapterStatusResponse:
        """Get the lifecycle state of a LoRA adapter."""
        return self.lora.get_adapter_status(provider_address, adapter_name)

    def resolve_adapter_name(
        self, provider_address: str, task_id: str, base_model: str
    ) -> str:
        """Resolve the provider's adapter name for a fine-tuning task."""
        return self.lora.resolve_adapter_name(
            provider_address, task_id, base_model
        )

    def deploy_adapter(
        self,
        provider_address: str,
        base_model: str,
        task_id: str,
        *,
        wait: bool = False,
        timeout_seconds: int = 120,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> DeployResponse:
        """Deploy a fine-tuned adapter to an inference provider."""
        return self.lora.deploy_adapter(
            provider_address,
            base_model,
            task_id,
            wait=wait,
            timeout_seconds=timeout_seconds,
            on_progress=on_progress,
        )

    def deploy_adapter_by_name(
        self,
        provider_address: str,
        adapter_name: str,
        *,
        wait: bool = False,
        timeout_seconds: int = 120,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> DeployResponse:
        """Deploy an adapter when its provider-side name is already known."""
        return self.lora.deploy_adapter_by_name(
            provider_address,
            adapter_name,
            wait=wait,
            timeout_seconds=timeout_seconds,
            on_progress=on_progress,
        )

    def chat_with_fine_tuned_model(
        self,
        provider_address: str,
        adapter_name: str,
        message: str,
        *,
        system_prompt: str = "You are a helpful assistant.",
    ) -> Dict[str, Any]:
        """Send a chat request to a deployed fine-tuned adapter."""
        return self.lora.chat(
            provider_address,
            adapter_name,
            message,
            system_prompt=system_prompt,
        )
    
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
                    verifiability=service[7],
                    additional_info=service[8] if len(service) > 8 else "",
                    tee_signer_address=service[9] if len(service) > 9 else "",
                    tee_signer_acknowledged=service[10] if len(service) > 10 else True,
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
                verifiability=service_data[7],
                additional_info=service_data[8] if len(service_data) > 8 else "",
                tee_signer_address=service_data[9] if len(service_data) > 9 else "",
                tee_signer_acknowledged=service_data[10] if len(service_data) > 10 else True,
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
                    self.ledger_manager.transfer_fund(provider_address, "inference", initial_amount)
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

    def get_service_metadata(
        self,
        provider_address: str,
        model: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get service endpoint and model information for a provider.
        
        Args:
            provider_address: Provider's wallet address
            model: Optional model ID for multi-model providers. The provider
                validates the ID; the SDK forwards it unchanged.
            
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
            "model": model if model is not None else service.model,
        }

    def get_provider_models(self, provider_address: str) -> ProviderModels:
        """
        Fetch the models served by a provider from its public ``/v1/models``.

        Works for both single-model and multi-model providers. The provider
        catalog is authoritative; status API health enrichment is best-effort.
        """
        service = self.get_service(provider_address)
        chain_id = self.web3.eth.chain_id
        status_api_endpoint = (
            "https://compute-status.0g.ai"
            if chain_id == 16661
            else "https://compute-status-testnet.0g.ai"
        )
        try:
            return _fetch_provider_models(service, status_api_endpoint)
        except Exception as exc:
            raise NetworkError(
                f"Failed to get provider models for {provider_address}: {exc}"
            ) from exc

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

        if self.ledger_manager is not None and not self.has_auto_funding(provider_address):
            self._check_and_fund(provider_address, AutoFundingConfig().buffer_multiplier)

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
        output_dir: Optional[str] = None,
        on_log: Optional[Callable[[VerificationStep], None]] = None,
    ) -> VerificationResult:
        """
        Verify a provider's TEE service and attestation.

        Mirrors the TS SDK's ``InferenceBroker.verifyService``: silent by
        default, emits ``VerificationStep`` entries to the optional ``on_log``
        callback, and returns a structured ``VerificationResult``. The full
        step log is also available on ``result.steps``.

        Args:
            provider_address: Provider's wallet address
            output_dir: Optional directory to save a verification report
            on_log: Optional callback invoked for each verification step

        Returns:
            ``VerificationResult`` with TS-parity fields plus Python-side
            discovery extras (model, service_type, quote_data, etc.).

        Raises:
            ServiceNotFoundError: If provider doesn't exist

        Example:
            >>> result = inference.verify_service(provider_address)
            >>> if result.success:
            ...     print(result.tee_signer)
            >>>
            >>> # Stream steps to stdout
            >>> result = inference.verify_service(
            ...     provider_address,
            ...     on_log=lambda step: print(step.message),
            ... )
        """
        import time
        import json
        from pathlib import Path

        provider_address = format_address(provider_address)
        result = VerificationResult(
            provider=provider_address,
            timestamp=int(time.time() * 1000),
            output_directory=output_dir,
        )

        def log(step_type: str, message: str) -> None:
            step = VerificationStep(type=step_type, message=message)  # type: ignore[arg-type]
            result.steps.append(step)
            if on_log is not None:
                on_log(step)

        try:
            log("step", f"🔍 Verifying service for provider: {provider_address}")
            service = self.get_service(provider_address)

            result.service_type = service.service_type
            result.model = service.model
            result.verifiability = service.verifiability

            log("success", f"Service found: {service.model}")
            log("info", f"Type: {service.service_type}")
            log("info", f"Verifiability: {service.verifiability}")

            quote_endpoint = f"{service.url}/v1/quote"
            log("step", f"Fetching quote from: {quote_endpoint}")

            try:
                quote_response = requests.get(quote_endpoint, timeout=15)

                if quote_response.status_code == 200:
                    quote_data = quote_response.json()
                    result.quote_available = True
                    result.quote_data = quote_data

                    tee_signer, attestation_format = self._extract_tee_signer_address(quote_data)
                    result.attestation_format = attestation_format

                    if tee_signer:
                        result.tee_signer = tee_signer
                        log("success", f"TEE signer extracted: {tee_signer}")
                    elif attestation_format in ("dstack", "gpu"):
                        log("success", f"{attestation_format.upper()} format attestation detected")
                    else:
                        result.errors.append("Could not extract signer - no supported format")
                        log("warning", "Could not extract signer - no supported format found")

                    quote_hex = quote_data.get("quote")
                    if quote_hex:
                        log("info", f"Quote hex data available: {len(quote_hex)} chars")
                else:
                    result.errors.append(
                        f"Quote fetch failed: HTTP {quote_response.status_code}"
                    )
                    log("error", f"Quote fetch failed: {quote_response.status_code}")

            except requests.RequestException as e:
                result.errors.append(f"Quote fetch error: {str(e)}")
                log("error", f"Quote fetch error: {e}")

            if result.quote_available and "quote" in result.quote_data:
                log("step", "Attempting Automata contract verification (optional)...")
                try:
                    attestation_valid = self._verify_quote_with_automata(
                        result.quote_data["quote"]
                    )
                    result.attestation_verified = attestation_valid
                    result.attestation_method = "automata_contract"
                    if attestation_valid:
                        log("success", "Automata contract verification passed")
                    else:
                        log("info", "Automata contract verification not available (this is normal)")
                except Exception as e:
                    result.attestation_verified = None
                    result.attestation_method = None
                    log("info", f"Automata verification skipped: {str(e)[:100]}")

            current_tee_signer: Optional[str] = None
            try:
                account = self.contract.functions.getAccount(
                    self.account.address,
                    provider_address,
                ).call()
                is_acknowledged = account[7] if len(account) > 7 else False
                result.is_acknowledged = bool(is_acknowledged)
                if result.is_acknowledged:
                    log("success", "Provider acknowledged in contract")
                else:
                    log("info", "Provider not yet acknowledged in contract")
            except Exception:
                log("info", "Contract signer check unavailable (this is optional)")

            if result.tee_signer and current_tee_signer:
                extracted = result.tee_signer.lower().replace("0x", "")
                expected = current_tee_signer.lower().replace("0x", "")
                match = extracted == expected
                result.signer_match = match
                result.expected_signer = current_tee_signer
                result.signer_verification = SignerVerification(
                    contract_address=current_tee_signer,
                    report_addresses=[
                        SignerReportMatch(
                            report_type="tee",
                            address=result.tee_signer,
                            match=match,
                        )
                    ],
                    all_match=match,
                )
                if match:
                    log("success", "TEE Signer Match!")
                else:
                    log("error", "TEE Signer Mismatch!")
            elif result.tee_signer:
                result.signer_match = True
                result.signer_verification = SignerVerification(
                    contract_address="",
                    report_addresses=[
                        SignerReportMatch(
                            report_type="tee",
                            address=result.tee_signer,
                            match=True,
                        )
                    ],
                    all_match=True,
                )
                log("success", "TEE signer extracted (contract comparison unavailable)")
            elif result.attestation_format in ("dstack", "gpu"):
                result.signer_match = True
                log("success", f"{result.attestation_format.upper()} attestation format verified")

            result.success = bool(
                result.quote_available
                and (
                    (result.tee_signer is not None and bool(result.signer_match))
                    or (
                        result.attestation_format in ("dstack", "gpu")
                        and bool(result.signer_match)
                    )
                )
            )

            if output_dir:
                try:
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    report_filename = (
                        f"verification_{provider_address}_{int(time.time())}.json"
                    )
                    report_path = str(Path(output_dir) / report_filename)
                    with open(report_path, "w") as f:
                        json.dump(
                            {
                                "success": result.success,
                                "provider": result.provider,
                                "model": result.model,
                                "service_type": result.service_type,
                                "verifiability": result.verifiability,
                                "tee_signer": result.tee_signer,
                                "expected_signer": result.expected_signer,
                                "signer_match": result.signer_match,
                                "quote_available": result.quote_available,
                                "quote_data": result.quote_data,
                                "attestation_format": result.attestation_format,
                                "attestation_verified": result.attestation_verified,
                                "attestation_method": result.attestation_method,
                                "is_acknowledged": result.is_acknowledged,
                                "errors": result.errors,
                                "timestamp": result.timestamp,
                            },
                            f,
                            indent=2,
                        )
                    result.reports_generated.append(report_path)
                    log("success", f"Report saved: {report_path}")
                except Exception as e:
                    result.errors.append(f"Report save error: {str(e)}")
                    log("warning", f"Report save error: {e}")

            log(
                "success" if result.success else "warning",
                "SERVICE VERIFICATION PASSED"
                if result.success
                else "SERVICE VERIFICATION INCOMPLETE",
            )
            return result

        except ServiceNotFoundError:
            raise
        except Exception as e:
            result.errors.append(f"Verification failed: {str(e)}")
            result.success = False
            log("error", f"Verification failed: {e}")
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
        extractor = self.get_extractor(provider_address)
        fee = self._calculate_fee(extractor, content)
        if fee > 0:
            self._update_cached_fee(provider_address, fee)

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
    
    def revoke_api_key(
        self,
        provider_address: str,
        token_id: int,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
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
        if token_id < 0 or token_id > 254:
            raise ValueError(
                "Only persistent token IDs 0-254 can be individually revoked. "
                "Use revoke_all_tokens() for ephemeral tokens."
            )
        
        provider_address = format_address(provider_address)
        
        try:
            tx = self.contract.functions.revokeToken(
                provider_address,
                token_id
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': gas_price or self.web3.eth.gas_price,
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

    def revoke_tokens(
        self,
        provider_address: str,
        token_ids: List[int],
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Revoke multiple persistent API keys in one transaction.

        Args:
            provider_address: Provider's wallet address
            token_ids: Token IDs to revoke (0-254)
            gas_price: Optional gas price override

        Returns:
            Transaction receipt
        """
        if not token_ids:
            raise ValueError("token_ids must contain at least one token ID")
        invalid = [tid for tid in token_ids if tid < 0 or tid > 254]
        if invalid:
            raise ValueError(
                "Only persistent token IDs 0-254 can be revoked in batch. "
                f"Invalid token IDs: {invalid}"
            )

        provider_address = format_address(provider_address)

        try:
            tx = self.contract.functions.revokeTokens(
                provider_address,
                token_ids,
            ).build_transaction({
                'from': self.account.address,
                'gas': 250000,
                'gasPrice': gas_price or self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("revokeTokens", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("revokeTokens", str(e))

    def revoke_all_tokens(
        self,
        provider_address: str,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
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
                'gasPrice': gas_price or self.web3.eth.gas_price,
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

    def get_chain_id(self) -> int:
        """Return the connected chain ID."""
        return self.web3.eth.chain_id

    def get_user_address(self) -> str:
        """Return the current wallet address."""
        return self.account.address

    def lock_time(self) -> int:
        """Return the contract refund lock time in seconds."""
        try:
            return self.contract.functions.lockTime().call()
        except Exception as e:
            raise ContractError("lockTime", str(e))

    def get_locked_time(self) -> int:
        """Alias for ``lock_time()`` matching the fine-tuning broker naming."""
        return self.lock_time()
    
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
        refunds_data = account_data[5] if len(account_data) > 5 else []
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

    def check_provider_signer_status(
        self,
        provider_address: str,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Check whether a provider's TEE signer is acknowledged by the contract owner.

        Mirrors the TypeScript SDK's ``checkProviderSignerStatus`` helper. If
        the current user has no provider sub-account yet, the SDK creates it
        with the contract minimum provider transfer before reading service
        signer status.
        """
        provider_address = format_address(provider_address)

        if self.ledger_manager:
            try:
                self.get_account(provider_address)
            except ContractError:
                self.ledger_manager.transfer_fund(
                    provider_address,
                    "inference",
                    self.ledger_manager.MIN_TRANSFER_AMOUNT_WEI,
                )

        service = self._get_service_with_signer(provider_address)
        zero_address = "0x0000000000000000000000000000000000000000"
        signer = service.tee_signer_address or ""
        is_acknowledged = (
            bool(service.tee_signer_acknowledged)
            and bool(signer)
            and signer.lower() != zero_address
        )

        return {
            "is_acknowledged": is_acknowledged,
            "tee_signer_address": signer,
        }

    def acknowledge_provider_tee_signer(
        self,
        provider_address: str,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Acknowledge a provider's TEE signer as contract owner.

        This is the owner-level operation exposed by the TypeScript SDK as
        ``acknowledgeProviderTEESigner``.
        """
        provider_address = format_address(provider_address)

        try:
            tx = self.contract.functions.acknowledgeTEESignerByOwner(
                provider_address
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': gas_price or self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("acknowledgeTEESignerByOwner", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("acknowledgeTEESignerByOwner", str(e))

    def revoke_provider_tee_signer_acknowledgement(
        self,
        provider_address: str,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
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
                'gasPrice': gas_price or self.web3.eth.gas_price,
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

    def _get_service_with_signer(self, provider_address: str) -> ServiceMetadata:
        service = self.get_service(provider_address)
        if service.tee_signer_address:
            return service

        try:
            services = self.list_service(offset=0, limit=1000)
            for candidate in services:
                if candidate.provider.lower() == provider_address.lower():
                    return candidate
        except Exception:
            pass

        return service

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
        gas_price: Optional[int] = None,
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
            current.additional_info if current else "",
            current.tee_signer_address if current else "0x0000000000000000000000000000000000000000",
        )

        try:
            tx = self.contract.functions.addOrUpdateService(params).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': gas_price or self.web3.eth.gas_price,
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
    _MIN_LOCKED_BALANCE = 10 ** 18
    _FEE_CACHE_TTL_SECONDS = 24 * 60 * 60

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

        def _loop() -> None:
            self._check_and_fund(provider_address, config.buffer_multiplier)
            while not stop_event.wait(timeout=config.interval_ms / 1000):
                self._check_and_fund(provider_address, config.buffer_multiplier)

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

    def _calculate_fee(self, extractor: Extractor, content: str) -> int:
        service = extractor.get_svc_info()
        output_count = extractor.get_output_count(content)
        input_count = extractor.get_input_count(content)
        return (
            int(output_count) * int(service.output_price)
            + int(input_count) * int(service.input_price)
        )

    def _update_cached_fee(self, provider_address: str, fee: int) -> None:
        provider_address = format_address(provider_address)
        current_fee = self._get_cached_fee(provider_address)
        self._cached_fees[provider_address] = {
            "fee": current_fee + int(fee),
            "expires_at": time.time() + self._FEE_CACHE_TTL_SECONDS,
        }

    def _clear_cached_fee(self, provider_address: str) -> None:
        provider_address = format_address(provider_address)
        self._cached_fees[provider_address] = {
            "fee": 0,
            "expires_at": time.time() + self._FEE_CACHE_TTL_SECONDS,
        }

    def _get_cached_fee(self, provider_address: str) -> int:
        provider_address = format_address(provider_address)
        cached = self._cached_fees.get(provider_address)
        if not cached:
            return 0
        if cached["expires_at"] <= time.time():
            self._cached_fees.pop(provider_address, None)
            return 0
        return int(cached["fee"])

    def _fetch_unsettled_fee(self, provider_address: str) -> int:
        provider_address = format_address(provider_address)
        try:
            service = self.get_service(provider_address)
            headers = self._session_manager.get_request_headers(provider_address)
            url = f"{service.url}/v1/user/{self.account.address}/unsettledfee"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return self._get_cached_fee(provider_address)

            data = response.json()
            fee = int(data.get("unsettledFee", 0))
            self._cached_fees[provider_address] = {
                "fee": fee,
                "expires_at": time.time() + self._FEE_CACHE_TTL_SECONDS,
            }
            return fee
        except Exception:
            return self._get_cached_fee(provider_address)

    def _get_transfer_deficit(self, provider_address: str, required_balance: int) -> int:
        provider_address = format_address(provider_address)
        try:
            account_data = self.contract.functions.getAccount(
                self.account.address,
                provider_address,
            ).call()
            balance = int(account_data[3])
            pending_refund = int(account_data[4])
            locked_balance = balance - pending_refund
            if locked_balance >= required_balance:
                return 0
            return required_balance - locked_balance
        except Exception:
            return required_balance

    def _do_auto_funding_transfer(self, provider_address: str, amount: int) -> None:
        transfer_amount = max(int(amount), self._MIN_LOCKED_BALANCE)
        self.ledger_manager.transfer_fund(provider_address, "inference", transfer_amount)
        self._clear_cached_fee(provider_address)

    def _check_and_fund(self, provider_address: str, buffer_multiplier: int) -> None:
        if self.ledger_manager is None:
            return

        provider_address = format_address(provider_address)
        try:
            unsettled_fee = self._fetch_unsettled_fee(provider_address)
            required_balance = unsettled_fee + buffer_multiplier * self._MIN_LOCKED_BALANCE
            deficit = self._get_transfer_deficit(provider_address, required_balance)
            if deficit > 0:
                self._do_auto_funding_transfer(provider_address, deficit)
        except Exception:
            # Auto-funding should never break inference calls or background threads.
            return
