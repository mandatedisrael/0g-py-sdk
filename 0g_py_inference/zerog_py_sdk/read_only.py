"""
Read-only broker for the 0G Compute Network SDK.

This module provides a read-only interface for querying services without
requiring a wallet connection. Useful for browsing available providers
before connecting a wallet.

Reference: TypeScript SDK src.ts/sdk/inference/broker/read-only-broker.ts
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from web3 import Web3

from .constants import (
    get_contract_addresses,
    get_rpc_url,
    MAINNET_CHAIN_ID,
    TESTNET_CHAIN_ID,
)
from .contracts.abis import SERVING_CONTRACT_ABI


class VerifiabilityEnum(str, Enum):
    """Verifiability types for services."""
    OpML = "OpML"
    TeeML = "TeeML"
    ZKML = "ZKML"


class HealthStatus(str, Enum):
    """Health status for services."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Health metrics for a service."""
    status: str
    uptime: float
    avg_response_time: float
    last_check: str


@dataclass
class PricingTier:
    """One tier in the provider's tiered pricing schedule."""

    max_input_tokens: int
    input_multiplier: float
    output_multiplier: float


@dataclass
class TieredPricingInfo:
    """Tiered pricing configuration for a model or service."""

    tiers: List[PricingTier] = field(default_factory=list)


@dataclass
class CacheTokenBillingInfo:
    """Cache token billing configuration for a model or service."""

    divisor: int


@dataclass
class ProviderModelInfo:
    """Model metadata returned by the status API's ``/models`` endpoint."""

    id: str
    provider: Optional[str] = None
    object: Optional[str] = None
    created: Optional[int] = None
    owned_by: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    context_length: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    architecture: Optional[Dict[str, Any]] = None
    supported_parameters: Optional[List[str]] = None
    default_parameters: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    pricing_usd: Optional[Dict[str, Any]] = None
    expiration_date: Optional[str] = None
    verifiability: Optional[str] = None
    tee_attested: Optional[bool] = None
    tee_type: Optional[str] = None
    tee_verifier: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderModelInfo":
        return cls(
            id=data.get("id", ""),
            provider=data.get("provider"),
            object=data.get("object"),
            created=data.get("created"),
            owned_by=data.get("owned_by"),
            name=data.get("name"),
            description=data.get("description"),
            type=data.get("type"),
            context_length=data.get("context_length"),
            max_completion_tokens=data.get("max_completion_tokens"),
            architecture=data.get("architecture"),
            supported_parameters=data.get("supported_parameters"),
            default_parameters=data.get("default_parameters"),
            pricing=data.get("pricing"),
            pricing_usd=data.get("pricing_usd"),
            expiration_date=data.get("expiration_date"),
            verifiability=data.get("verifiability"),
            tee_attested=data.get("tee_attested"),
            tee_type=data.get("tee_type"),
            tee_verifier=data.get("tee_verifier"),
        )


@dataclass
class ServiceWithDetail:
    """Service information with optional health, model, and pricing detail."""
    provider: str
    service_type: str
    url: str
    input_price: int
    output_price: int
    updated_at: int
    model: str
    verifiability: str
    additional_info: str = ""
    tee_signer_address: str = ""
    tee_signer_acknowledged: bool = True
    health_metrics: Optional[HealthMetrics] = None
    model_info: Optional[ProviderModelInfo] = None
    tiered_pricing: Optional[TieredPricingInfo] = None
    cache_token_billing: Optional[CacheTokenBillingInfo] = None


def parse_tiered_pricing(additional_info: str) -> Optional[TieredPricingInfo]:
    """Parse tiered pricing from a service's ``additional_info`` JSON string."""
    try:
        parsed = json.loads(additional_info)
    except (TypeError, json.JSONDecodeError):
        return None

    raw_tiers = parsed.get("tieredPricing", {}).get("tiers")
    if not isinstance(raw_tiers, list):
        return None

    tiers = []
    for item in raw_tiers:
        if not isinstance(item, dict):
            continue
        max_input_tokens = item.get("maxInputTokens")
        input_multiplier = item.get("inputMultiplier")
        output_multiplier = item.get("outputMultiplier")
        if (
            isinstance(max_input_tokens, int)
            and isinstance(input_multiplier, (int, float))
            and isinstance(output_multiplier, (int, float))
        ):
            tiers.append(
                PricingTier(
                    max_input_tokens=max_input_tokens,
                    input_multiplier=float(input_multiplier),
                    output_multiplier=float(output_multiplier),
                )
            )

    return TieredPricingInfo(tiers=tiers) if tiers else None


def parse_tiered_pricing_from_model_info(
    model_info: Optional[ProviderModelInfo],
) -> Optional[TieredPricingInfo]:
    """Parse tiered pricing from the status API's model payload."""
    raw_pricing = (model_info.pricing or {}).get("tiered_pricing") if model_info else None
    if not isinstance(raw_pricing, list):
        return None

    tiers = []
    for item in raw_pricing:
        if not isinstance(item, dict):
            continue
        max_input_tokens = item.get("max_input_tokens")
        input_multiplier = item.get("input_multiplier")
        output_multiplier = item.get("output_multiplier")
        if (
            isinstance(max_input_tokens, int)
            and isinstance(input_multiplier, (int, float))
            and isinstance(output_multiplier, (int, float))
        ):
            tiers.append(
                PricingTier(
                    max_input_tokens=max_input_tokens,
                    input_multiplier=float(input_multiplier),
                    output_multiplier=float(output_multiplier),
                )
            )

    return TieredPricingInfo(tiers=tiers) if tiers else None


def parse_cache_token_billing(
    additional_info: str,
) -> Optional[CacheTokenBillingInfo]:
    """Parse cache token billing from a service's ``additional_info`` JSON string."""
    try:
        parsed = json.loads(additional_info)
    except (TypeError, json.JSONDecodeError):
        return None

    divisor = parsed.get("cacheTokenBilling", {}).get("divisor")
    if isinstance(divisor, int) and divisor > 0:
        return CacheTokenBillingInfo(divisor=divisor)
    return None


def parse_cache_token_billing_from_model_info(
    model_info: Optional[ProviderModelInfo],
) -> Optional[CacheTokenBillingInfo]:
    """Parse cache token billing from the status API's model payload."""
    divisor = (model_info.pricing or {}).get("cache_token_billing", {}).get("divisor") if model_info else None
    if isinstance(divisor, int) and divisor > 0:
        return CacheTokenBillingInfo(divisor=divisor)
    return None


class ReadOnlyInferenceBroker:
    """
    Read-only inference broker for wallet-less operations.
    
    Use this broker to:
    - List available AI providers before connecting wallet
    - Get service information and health metrics
    - Browse services without authentication
    
    Example:
        >>> from zerog_py_sdk import create_read_only_broker
        >>> 
        >>> # Create read-only broker (no wallet needed)
        >>> broker = create_read_only_broker()
        >>> 
        >>> # List all services
        >>> services = broker.list_service()
        >>> for svc in services:
        ...     print(f"{svc.model} - {svc.provider}")
        >>> 
        >>> # List services with health details
        >>> detailed = broker.list_service_with_detail()
        >>> for svc in detailed:
        ...     if svc.health_metrics:
        ...         print(f"{svc.model}: {svc.health_metrics.uptime}% uptime")
    """
    
    # Health API endpoints
    HEALTH_API_MAINNET = "https://compute-status.0g.ai"
    HEALTH_API_TESTNET = "https://compute-status-testnet.0g.ai"
    
    def __init__(self, web3: Web3, contract_address: str):
        """
        Initialize the read-only broker.
        
        Args:
            web3: Web3 instance (read-only provider is sufficient)
            contract_address: Inference contract address
        """
        self.web3 = web3
        self.contract_address = contract_address
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=SERVING_CONTRACT_ABI
        )
    
    def list_service(
        self,
        offset: int = 0,
        limit: int = 20,
        include_unacknowledged: bool = True,
    ) -> List[ServiceWithDetail]:
        """
        Retrieve a list of all available services.

        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of services to return (default: 20)
            include_unacknowledged: Include services whose TEE signer has not been
                acknowledged (default: True). Set False to only return services
                with a verified, acknowledged TEE signer.

        Returns:
            List of ServiceWithDetail objects (without health metrics)

        Example:
            >>> services = broker.list_service()
            >>> # Acknowledged-only
            >>> services = broker.list_service(include_unacknowledged=False)
        """
        try:
            result = self.contract.functions.getAllServices(offset, limit).call()

            # Returns [services[], total] or (services[], total)
            if isinstance(result, (list, tuple)) and len(result) == 2:
                services_data = result[0]
            else:
                services_data = result

            services = []
            for service in services_data:
                # Paginated struct: (provider, serviceType, url, inputPrice, outputPrice,
                #   updatedAt, model, verifiability, additionalInfo,
                #   teeSignerAddress[9], teeSignerAcknowledged[10])
                tee_acknowledged = service[10] if len(service) > 10 else True
                if not include_unacknowledged and not tee_acknowledged:
                    continue

                services.append(ServiceWithDetail(
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
            raise Exception(f"Failed to list services: {str(e)}")

    def list_service_with_detail(
        self,
        offset: int = 0,
        limit: int = 20,
        include_unacknowledged: bool = True,
    ) -> List[ServiceWithDetail]:
        """
        Retrieve services with health metrics and model metadata from the status APIs.

        This combines on-chain service data with real-time health metrics,
        status API model metadata, and parsed pricing details.

        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of services to return (default: 20)
            include_unacknowledged: Include services whose TEE signer has not been
                acknowledged (default: True).

        Returns:
            List of ServiceWithDetail objects enriched with optional
            ``health_metrics``, ``model_info``, ``tiered_pricing``, and
            ``cache_token_billing`` fields.

        Example:
            >>> services = broker.list_service_with_detail()
            >>> for svc in services:
            ...     if svc.health_metrics:
            ...         print(f"{svc.model}: {svc.health_metrics.uptime}% uptime")
        """
        services = self.list_service(
            offset=offset,
            limit=limit,
            include_unacknowledged=include_unacknowledged,
        )

        health_map = self._fetch_health_metrics()
        model_map = self._fetch_model_info()

        for service in services:
            health = health_map.get(service.provider.lower())
            if health:
                service.health_metrics = health
            provider_models = model_map.get(service.provider.lower(), [])
            service.model_info = next(
                (info for info in provider_models if info.id == service.model),
                None,
            )
            service.tiered_pricing = (
                parse_tiered_pricing(service.additional_info)
                or parse_tiered_pricing_from_model_info(service.model_info)
            )
            service.cache_token_billing = (
                parse_cache_token_billing(service.additional_info)
                or parse_cache_token_billing_from_model_info(service.model_info)
            )

        return services
    
    def _fetch_health_metrics(self) -> Dict[str, HealthMetrics]:
        """Fetch health metrics from monitoring API."""
        try:
            # Determine endpoint based on chain ID
            chain_id = self.web3.eth.chain_id
            if chain_id == MAINNET_CHAIN_ID:
                endpoint = self.HEALTH_API_MAINNET
            else:
                endpoint = self.HEALTH_API_TESTNET
            
            response = requests.get(f"{endpoint}/health", timeout=10)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            health_services = data.get("services", [])
            
            health_map = {}
            for metric in health_services:
                provider = metric.get("provider", "").lower()
                if provider:
                    checks = metric.get("checks", {})
                    performance = metric.get("performance", {})
                    response_time = performance.get("response_time", {})
                    
                    health_map[provider] = HealthMetrics(
                        status=metric.get("status", "unknown"),
                        uptime=checks.get("uptime", 0),
                        avg_response_time=response_time.get("avg", 0),
                        last_check=metric.get("lastCheck", ""),
                    )
            
            return health_map
            
        except Exception:
            # Return empty map if health API fails
            return {}

    def _fetch_model_info(self) -> Dict[str, List[ProviderModelInfo]]:
        """Fetch aggregated provider model metadata from the status API."""
        try:
            endpoint = self._get_status_api_endpoint()
            response = requests.get(f"{endpoint}/models", timeout=10)
            if response.status_code != 200:
                return {}

            data = response.json()
            models = data.get("data", [])

            model_map: Dict[str, List[ProviderModelInfo]] = {}
            for item in models:
                if not isinstance(item, dict):
                    continue
                info = ProviderModelInfo.from_dict(item)
                if not info.provider:
                    continue
                provider = info.provider.lower()
                model_map.setdefault(provider, []).append(info)
            return model_map

        except Exception:
            return {}

    def _get_status_api_endpoint(self) -> str:
        """Resolve the public status API base URL from the current chain ID."""
        chain_id = self.web3.eth.chain_id
        if chain_id == MAINNET_CHAIN_ID:
            return self.HEALTH_API_MAINNET
        return self.HEALTH_API_TESTNET
    
    def get_service(self, provider_address: str) -> ServiceWithDetail:
        """
        Get service information for a specific provider.
        
        Args:
            provider_address: Provider's wallet address
            
        Returns:
            ServiceWithDetail for the provider
        """
        provider_address = Web3.to_checksum_address(provider_address)
        
        try:
            service = self.contract.functions.getService(provider_address).call()
            
            return ServiceWithDetail(
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
            )
            
        except Exception as e:
            raise Exception(f"Failed to get service for {provider_address}: {str(e)}")


def create_read_only_broker(
    rpc_url: Optional[str] = None,
    network: Optional[str] = None,
    contract_address: Optional[str] = None,
) -> ReadOnlyInferenceBroker:
    """
    Create a read-only inference broker (no wallet required).
    
    Perfect for listing providers without wallet connection.
    
    Args:
        rpc_url: RPC endpoint URL (auto-detected if None)
        network: Network name ("mainnet" or "testnet")
        contract_address: Override contract address
        
    Returns:
        ReadOnlyInferenceBroker instance
        
    Example:
        >>> from zerog_py_sdk import create_read_only_broker
        >>> 
        >>> # Mainnet (default)
        >>> broker = create_read_only_broker()
        >>>
        >>> # Testnet
        >>> broker = create_read_only_broker(network="testnet")
        >>> 
        >>> # List services
        >>> services = broker.list_service()
    """
    # Determine RPC URL
    if rpc_url is None:
        if network == "testnet" or network == "testnet_dev":
            rpc_url = get_rpc_url("testnet")
        else:
            rpc_url = get_rpc_url("mainnet")
    
    # Initialize Web3
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not web3.is_connected():
        raise Exception(f"Failed to connect to RPC endpoint: {rpc_url}")
    
    # Get contract address
    if contract_address is None:
        if network:
            addresses = get_contract_addresses(network=network)
        else:
            chain_id = web3.eth.chain_id
            addresses = get_contract_addresses(chain_id=chain_id)
        contract_address = addresses.inference
    
    return ReadOnlyInferenceBroker(web3, contract_address)
