"""
Main broker class for the 0G Compute Network SDK.

This module provides the primary interface for interacting with the
0G Compute Network, integrating ledger, inference, and authentication operations.
"""

from typing import Optional
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from .ledger import LedgerManager
from .inference import InferenceManager
from .auth import AuthManager
from .contracts.abis import SERVING_CONTRACT_ABI, LEDGER_CONTRACT_ABI
from .constants import (
    get_contract_addresses,
    get_rpc_url,
    TESTNET_CHAIN_ID,
    MAINNET_CHAIN_ID,
)
from .exceptions import ConfigurationError


class ZGServingBroker:
    """
    Main broker for the 0G Compute Network.
    
    This class provides access to all SDK functionality:
    - Ledger operations (funding, balance checks)
    - Service discovery (listing providers)
    - Inference requests (authenticated API calls)
    
    Example:
        >>> from zerog_py_sdk import create_broker
        >>> 
        >>> # Connect to testnet (default)
        >>> broker = create_broker(private_key="0x...")
        >>> 
        >>> # Connect to mainnet
        >>> broker = create_broker(private_key="0x...", network="mainnet")
        >>> 
        >>> # Fund account
        >>> broker.ledger.add_ledger("0.1")
        >>> 
        >>> # List services
        >>> services = broker.inference.list_service()
        >>> 
        >>> # Generate request headers (new session token auth)
        >>> headers = broker.inference.get_request_headers(provider_address)
    """
    
    def __init__(
        self,
        account: LocalAccount,
        web3: Web3,
        inference_address: Optional[str] = None,
        ledger_address: Optional[str] = None,
    ):
        """
        Initialize the broker.
        
        Args:
            account: Local account for signing transactions
            web3: Web3 instance connected to 0G network
            inference_address: Inference contract address (auto-detected if None)
            ledger_address: Ledger contract address (auto-detected if None)
        """
        self.account = account
        self.web3 = web3
        
        # Auto-detect network from chain ID if addresses not provided
        if inference_address is None or ledger_address is None:
            chain_id = self.web3.eth.chain_id
            addresses = get_contract_addresses(chain_id=chain_id)
            inference_address = inference_address or addresses.inference
            ledger_address = ledger_address or addresses.ledger
        
        # Initialize contracts
        self.serving_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(inference_address),
            abi=SERVING_CONTRACT_ABI
        )
        
        self.ledger_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(ledger_address),
            abi=LEDGER_CONTRACT_ABI
        )
        
        # Initialize managers
        self._auth_manager = AuthManager(self.serving_contract, self.account, self.web3)
        self._ledger_manager = LedgerManager(self.ledger_contract, self.account, self.web3)
        self._inference_manager = InferenceManager(
            self.serving_contract,
            self.account,
            self.web3,
            self._auth_manager,
            self._ledger_manager
        )
    
    @property
    def ledger(self) -> LedgerManager:
        """
        Access ledger operations.
        
        Returns:
            LedgerManager instance
            
        Example:
            >>> broker.ledger.add_ledger("0.1")
            >>> account = broker.ledger.get_ledger()
            >>> print(f"Balance: {account.balance}")
        """
        return self._ledger_manager
    
    @property
    def inference(self) -> InferenceManager:
        """
        Access inference operations.
        
        Returns:
            InferenceManager instance
            
        Example:
            >>> services = broker.inference.list_service()
            >>> headers = broker.inference.get_request_headers(provider)
        """
        return self._inference_manager
    
    def get_address(self) -> str:
        """
        Get the user's wallet address.
        
        Returns:
            Checksum address of the user's account
        """
        return self.account.address


def create_broker(
    private_key: str,
    network: Optional[str] = None,
    rpc_url: Optional[str] = None,
    inference_address: Optional[str] = None,
    ledger_address: Optional[str] = None,
) -> ZGServingBroker:
    """
    Factory function to create a broker instance.
    
    Args:
        private_key: Private key for signing transactions (with or without 0x prefix)
        network: Network name ("mainnet", "testnet", "testnet_dev"). Auto-detected if None.
        rpc_url: RPC endpoint URL. Uses default for network if not provided.
        inference_address: Override inference contract address
        ledger_address: Override ledger contract address
        
    Returns:
        Initialized ZGServingBroker instance
        
    Raises:
        ConfigurationError: If configuration is invalid
        
    Example:
        >>> from zerog_py_sdk import create_broker
        >>> 
        >>> # Testnet (default)
        >>> broker = create_broker(private_key="0x1234...")
        >>> 
        >>> # Mainnet
        >>> broker = create_broker(private_key="0x1234...", network="mainnet")
        >>> 
        >>> # Custom RPC
        >>> broker = create_broker(
        ...     private_key="0x1234...",
        ...     rpc_url="https://my-rpc.example.com"
        ... )
    """
    try:
        # Determine RPC URL
        if rpc_url is None:
            if network == "mainnet":
                rpc_url = get_rpc_url("mainnet")
            else:
                rpc_url = get_rpc_url("testnet")
        
        # Initialize Web3
        web3 = Web3(Web3.HTTPProvider(rpc_url))

        # Check connection
        if not web3.is_connected():
            raise ConfigurationError(f"Failed to connect to RPC endpoint: {rpc_url}")

        # Validate private key
        if not private_key:
            raise ConfigurationError("Private key is required")

        # Create account from private key
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        account = Account.from_key(private_key)
        
        # Get contract addresses if not provided
        if inference_address is None or ledger_address is None:
            if network:
                addresses = get_contract_addresses(network=network)
            else:
                # Auto-detect from chain ID
                chain_id = web3.eth.chain_id
                addresses = get_contract_addresses(chain_id=chain_id)
            
            inference_address = inference_address or addresses.inference
            ledger_address = ledger_address or addresses.ledger
        
        # Create and return broker
        return ZGServingBroker(
            account=account,
            web3=web3,
            inference_address=inference_address,
            ledger_address=ledger_address,
        )
        
    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to create broker: {str(e)}")


def create_broker_from_env(
    env_file: str = ".env",
    network: Optional[str] = None,
) -> ZGServingBroker:
    """
    Create broker from environment variables.
    
    Expected environment variables:
    - PRIVATE_KEY: Wallet private key (required)
    - RPC_URL: RPC endpoint (optional)
    - NETWORK: Network name (optional, "mainnet" or "testnet")
    
    Args:
        env_file: Path to .env file
        network: Override network from env
        
    Returns:
        Initialized ZGServingBroker instance
        
    Example:
        >>> # In .env file:
        >>> # PRIVATE_KEY=0x1234...
        >>> # NETWORK=mainnet
        >>> 
        >>> from zerog_py_sdk import create_broker_from_env
        >>> broker = create_broker_from_env()
    """
    try:
        from dotenv import load_dotenv
        import os
        
        # Load environment variables
        load_dotenv(env_file)
        
        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            raise ConfigurationError("PRIVATE_KEY not found in environment")
        
        rpc_url = os.getenv('RPC_URL')
        network = network or os.getenv('NETWORK')
        
        return create_broker(
            private_key=private_key,
            network=network,
            rpc_url=rpc_url,
        )
        
    except ImportError:
        raise ConfigurationError(
            "python-dotenv is required for create_broker_from_env. "
            "Install with: pip install python-dotenv"
        )
    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to create broker from environment: {str(e)}")