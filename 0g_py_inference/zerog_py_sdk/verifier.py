"""
Response verification for TEE services in the 0G Compute Network SDK.

This module handles verification of responses from TEE (Trusted Execution Environment)
services by validating cryptographic signatures.

The verification process:
1. Parse service additionalInfo to determine signing address
2. Fetch signature from provider by chatID
3. Verify ECDSA signature using eth_account
"""

import json
import requests
from typing import Callable, List, Literal, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from eth_account.messages import encode_defunct
from eth_account import Account as EthAccount

from .models import ServiceMetadata, AdditionalInfo
from .exceptions import InvalidResponseError


@dataclass
class ResponseSignature:
    """
    Signature data fetched from provider.

    Attributes:
        text: The original response text
        signature: The cryptographic signature
    """
    text: str
    signature: str


# ---------------------------------------------------------------------------
# verify_service() typed result + step types — mirror TS
# ``src.ts/sdk/inference/broker/verifier.ts`` exports 1:1.
# ---------------------------------------------------------------------------

VerificationStepType = Literal["info", "success", "error", "warning", "step"]
ProviderType = Literal["decentralized", "centralized"]


@dataclass
class VerificationStep:
    """A single step emitted during ``verify_service``."""

    type: VerificationStepType
    message: str


@dataclass
class SignerRAVerificationResult:
    """Whether a signer's RA report is valid plus the signing address."""

    valid: Optional[bool]
    signing_address: str


@dataclass
class SignerReportMatch:
    """One report's signer-address comparison against the contract value."""

    report_type: str
    address: str
    match: bool


@dataclass
class SignerVerification:
    """Aggregated signer verification across the broker/llm/combined reports."""

    contract_address: str
    report_addresses: List[SignerReportMatch] = field(default_factory=list)
    all_match: bool = False


@dataclass
class EventLogEntry:
    """One entry from a TEE attestation event log."""

    event: str
    event_payload: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttestationReport:
    """A TEE attestation report (broker, llm, or combined)."""

    tcb_info: Optional[Dict[str, Any]] = None
    info: Optional[Dict[str, Any]] = None
    event_log: List[EventLogEntry] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportsData:
    """Bundle of broker / llm / combined attestation reports."""

    broker: Optional[AttestationReport] = None
    llm: Optional[AttestationReport] = None
    combined: Optional[AttestationReport] = None


@dataclass
class ComposeVerificationDetail:
    """Per-report compose-hash verification detail."""

    calculated_hash: Optional[str] = None
    event_log_hash: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ComposeVerification:
    """Aggregated compose-hash verification across reports."""

    passed: bool
    details: Dict[str, ComposeVerificationDetail] = field(default_factory=dict)


@dataclass
class ComposeVerificationResult:
    """Result of a single compose-hash verification."""

    is_valid: bool
    error: Optional[str] = None
    calculated_hash: Optional[str] = None
    event_log_hash: Optional[str] = None
    compose_hash_event: Optional[EventLogEntry] = None


@dataclass
class VerificationSummary:
    """High-level summary of all verifications performed."""

    compose_verification: bool = False
    signer_address_verification: bool = False
    signer_address_matches: int = 0
    total_reports: int = 0
    all_verifications_passed: bool = False


@dataclass
class VerificationResult:
    """
    Structured result from ``InferenceManager.verify_service``.

    Mirrors the TS SDK's ``VerificationResult`` interface field-for-field
    (snake_case) and adds Python-side discovery fields collected during
    verification (provider, model, service_type, quote data, etc.) so callers
    don't lose access to information the Python SDK already gathered.
    """

    # --- TS-parity fields ---
    success: bool = False
    tee_verifier: Optional[str] = None
    target_separated: bool = False
    verifier_url: Optional[str] = None
    reports_generated: List[str] = field(default_factory=list)
    output_directory: Optional[str] = None
    reports_data: Optional[ReportsData] = None
    signer_verification: Optional[SignerVerification] = None
    compose_verification: Optional[ComposeVerification] = None
    docker_images: List[str] = field(default_factory=list)
    steps: List[VerificationStep] = field(default_factory=list)

    # --- Python-side extras (data already collected; kept to avoid loss) ---
    provider: Optional[str] = None
    service_type: Optional[str] = None
    model: Optional[str] = None
    verifiability: Optional[str] = None
    tee_signer: Optional[str] = None
    quote_available: bool = False
    quote_data: Dict[str, Any] = field(default_factory=dict)
    attestation_format: Optional[str] = None
    attestation_verified: Optional[bool] = None
    attestation_method: Optional[str] = None
    is_acknowledged: Optional[bool] = None
    expected_signer: Optional[str] = None
    signer_match: Optional[bool] = None
    errors: List[str] = field(default_factory=list)
    timestamp: Optional[int] = None


VerificationLogger = Callable[[VerificationStep], None]


class ResponseVerifier:
    """
    Verifies responses from TEE services.
    
    This class handles the complete verification flow:
    1. Determine the signing address from service metadata
    2. Fetch the signature from the provider
    3. Verify the ECDSA signature
    
    Example:
        >>> verifier = ResponseVerifier()
        >>> is_valid = verifier.verify_response(service, chat_id)
    """
    
    @staticmethod
    def is_verifiable(verifiability: str) -> bool:
        """
        Check if a service is verifiable.
        
        Args:
            verifiability: The verifiability field from service metadata
            
        Returns:
            True if service provides verifiable outputs
        """
        return bool(verifiability and verifiability.lower() in ['teeml', 'tee', 'zkml'])
    
    @staticmethod
    def get_signing_address(
        service: ServiceMetadata,
        tee_signer_address: str
    ) -> Optional[str]:
        """
        Determine the correct signing address for verification.
        
        Uses service.additionalInfo to check for separated TEE architecture.
        If TargetSeparated is true and TargetTeeAddress is provided for a
        decentralized provider, use that instead of the default
        tee_signer_address.

        For centralized providers (ProviderType="centralized"), the broker TEE
        signs responses (since the LLM — e.g. OpenAI/Anthropic — has no TEE
        key), so we keep the default tee_signer_address even when
        TargetSeparated=true.
        
        Args:
            service: Service metadata from contract
            tee_signer_address: Default TEE signer address from account
            
        Returns:
            The address to verify signatures against, or None if unavailable
        """
        # Default to the account's TEE signer address
        signing_address = tee_signer_address
        
        # Try to parse additionalInfo for override
        if hasattr(service, 'additional_info') and service.additional_info:
            additional_info_str = service.additional_info
        else:
            # ServiceMetadata might not have additional_info, use empty
            additional_info_str = ""
        
        if additional_info_str:
            try:
                info = AdditionalInfo.from_json(additional_info_str)
                is_centralized = info.provider_type == 'centralized'
                if (
                    info.target_separated
                    and info.target_tee_address
                    and not is_centralized
                ):
                    signing_address = info.target_tee_address
            except Exception:
                # JSON parsing failed, use default
                pass
        
        return signing_address
    
    @staticmethod
    def fetch_signature_by_chat_id(
        provider_url: str,
        chat_id: str,
        model: str,
        timeout: int = 10
    ) -> ResponseSignature:
        """
        Fetch signature from provider by chat ID.
        
        Makes a GET request to the provider's signature endpoint
        to retrieve the signed response.
        
        Args:
            provider_url: Provider's base URL
            chat_id: Chat completion ID
            model: Model name
            timeout: Request timeout in seconds
            
        Returns:
            ResponseSignature with text and signature
            
        Raises:
            InvalidResponseError: If signature fetch fails
        """
        # Clean URL
        url = provider_url.rstrip('/')
        endpoint = f"{url}/v1/proxy/signature/{chat_id}"
        
        try:
            response = requests.get(
                endpoint,
                params={'model': model},
                headers={'Content-Type': 'application/json'},
                timeout=timeout
            )
            
            if not response.ok:
                raise InvalidResponseError(
                    f"Failed to fetch signature: {response.status_code}",
                    provider_url
                )
            
            data = response.json()
            return ResponseSignature(
                text=data.get('text', ''),
                signature=data.get('signature', '')
            )
            
        except requests.RequestException as e:
            raise InvalidResponseError(
                f"Failed to fetch signature: {str(e)}",
                provider_url
            )
    
    @staticmethod
    def verify_signature(
        message: str,
        signature: str,
        expected_address: str
    ) -> bool:
        """
        Verify ECDSA signature matches expected address.
        
        Uses eth_account to recover the signer address from the
        signature and compares it to the expected address.
        
        Args:
            message: The original message that was signed
            signature: The signature to verify
            expected_address: The expected signer address
            
        Returns:
            True if signature is valid and matches expected address
        """
        try:
            # Create message hash (EIP-191 personal sign)
            message_obj = encode_defunct(text=message)
            
            # Recover address from signature
            recovered_address = EthAccount.recover_message(
                message_obj,
                signature=signature
            )
            
            # Compare addresses (case-insensitive)
            return recovered_address.lower() == expected_address.lower()
            
        except Exception:
            return False
    
    def process_response(
        self,
        service: ServiceMetadata,
        tee_signer_address: str,
        tee_signer_acknowledged: bool,
        chat_id: Optional[str] = None,
        content: Optional[str] = None
    ) -> Optional[bool]:
        """
        Process and verify a response from a provider.
        
        Args:
            service: Service metadata
            tee_signer_address: TEE signer address from account
            tee_signer_acknowledged: Whether TEE signer is acknowledged
            chat_id: Chat completion ID (required for verification)
            content: Response content (optional, for fee calculation)
            
        Returns:
            - True if verification passed
            - False if verification failed
            - None if verification was skipped (no chat_id or not verifiable)
        """
        # Skip if no chat_id provided
        if not chat_id:
            return None
        
        # Skip if service is not verifiable
        if not self.is_verifiable(service.verifiability):
            return None
        
        # Fail if TEE signer not acknowledged
        if not tee_signer_acknowledged:
            return False
        
        # Get signing address
        signing_address = self.get_signing_address(service, tee_signer_address)
        if not signing_address:
            return False
        
        try:
            # Fetch signature from provider
            sig_data = self.fetch_signature_by_chat_id(
                service.url,
                chat_id,
                service.model
            )
            
            # Verify signature
            return self.verify_signature(
                sig_data.text,
                sig_data.signature,
                signing_address
            )
            
        except InvalidResponseError:
            return False


# Create a default verifier instance
_default_verifier = None


def get_response_verifier() -> ResponseVerifier:
    """Get the default response verifier instance."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = ResponseVerifier()
    return _default_verifier


def verify_tee_response(
    service: ServiceMetadata,
    tee_signer_address: str,
    tee_signer_acknowledged: bool,
    chat_id: str
) -> bool:
    """
    Convenience function to verify a TEE response.
    
    Args:
        service: Service metadata
        tee_signer_address: TEE signer address
        tee_signer_acknowledged: Whether TEE signer is acknowledged
        chat_id: Chat completion ID
        
    Returns:
        True if verification passed, False otherwise
    """
    verifier = get_response_verifier()
    result = verifier.process_response(
        service,
        tee_signer_address,
        tee_signer_acknowledged,
        chat_id
    )
    return result is True
