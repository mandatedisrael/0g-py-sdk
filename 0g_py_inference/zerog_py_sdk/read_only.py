"""
Read-only broker for the 0G Compute Network SDK.

This module provides a read-only interface for querying services without
requiring a wallet connection. Useful for browsing available providers
before connecting a wallet.

Reference: TypeScript SDK src.ts/sdk/inference/broker/read-only-broker.ts
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from web3 import Web3
import requests

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
class ServiceWithDetail:
    """Service information with optional health metrics."""
    provider: str
    service_type: str
    url: str
    input_price: int
    output_price: int
    updated_at: int
    model: str
    verifiability: str
    additional_info: str = ""
    health_metrics: Optional[HealthMetrics] = None


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
        Retrieve services with health metrics from monitoring API.

        This combines on-chain service data with real-time health metrics
        including uptime percentage and average response time.

        Args:
            offset: Pagination offset (default: 0)
            limit: Maximum number of services to return (default: 20)
            include_unacknowledged: Include services whose TEE signer has not been
                acknowledged (default: True).

        Returns:
            List of ServiceWithDetail objects with health_metrics populated

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

        for service in services:
            health = health_map.get(service.provider.lower())
            if health:
                service.health_metrics = health

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
        >>> # Testnet (default)
        >>> broker = create_read_only_broker()
        >>> 
        >>> # Mainnet
        >>> broker = create_read_only_broker(network="mainnet")
        >>> 
        >>> # List services
        >>> services = broker.list_service()
    """
    # Determine RPC URL
    if rpc_url is None:
        if network == "mainnet":
            rpc_url = get_rpc_url("mainnet")
        else:
            rpc_url = get_rpc_url("testnet")
    
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
