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
from .contracts.abis import SERVING_CONTRACT_ABI, DEFAULT_SERVING_ADDRESS, DEFAULT_LEDGER_ADDRESS, LEDGER_CONTRACT_ABI
from .exceptions import ConfigurationError


class ZGServingBroker:
    """
    Main broker for the 0G Compute Network.
    
    This class provides access to all SDK functionality:
    - Ledger operations (funding, balance checks)
    - Service discovery (listing providers)
    - Inference requests (authenticated API calls)
    
    Example:
        >>> from og_compute_sdk import create_broker
        >>> 
        >>> broker = create_broker(
        ...     private_key="0x...",
        ...     rpc_url="https://evmrpc-testnet.0g.ai"
        ... )
        >>> 
        >>> # Fund account
        >>> broker.ledger.add_ledger("0.1", provider_address)
        >>> 
        >>> # List services
        >>> services = broker.inference.list_service()
        >>> 
        >>> # Generate request headers
        >>> headers = broker.inference.get_request_headers(provider_address, content)
    """
    
    def __init__(
        self,
        account: LocalAccount,
        web3: Web3,
        contract_address: Optional[str] = None
    ):
        """
        Initialize the broker.
        
        Args:
            account: Local account for signing transactions
            web3: Web3 instance connected to 0G network
            contract_address: Contract address (uses default if not provided)
        """
        self.account = account
        self.web3 = web3
        
        # Use default contract addresses if not provided
        if contract_address is None:
            contract_address = DEFAULT_SERVING_ADDRESS
        
        # Initialize contracts
        self.serving_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=SERVING_CONTRACT_ABI
        )
        
        self.ledger_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(DEFAULT_LEDGER_ADDRESS),
            abi=LEDGER_CONTRACT_ABI
        )
        
        # Initialize managers
        self._auth_manager = AuthManager(self.serving_contract, self.account, self.web3)
        self._ledger_manager = LedgerManager(self.ledger_contract, self.account, self.web3)
        self._inference_manager = InferenceManager(
            self.serving_contract,
            self.account,
            self.web3,
            self._auth_manager
        )
    
    @property
    def ledger(self) -> LedgerManager:
        """
        Access ledger operations.
        
        Returns:
            LedgerManager instance
            
        Example:
            >>> broker.ledger.add_ledger("0.1", provider_address)
            >>> account = broker.ledger.get_ledger(provider_address)
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
            >>> headers = broker.inference.get_request_headers(provider, content)
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
    rpc_url: str = "https://evmrpc-testnet.0g.ai",
    contract_address: Optional[str] = None
) -> ZGServingBroker:
    """
    Factory function to create a broker instance.
    
    Args:
        private_key: Private key for signing transactions (with or without 0x prefix)
        rpc_url: RPC endpoint URL (defaults to 0G testnet)
        contract_address: Contract address (uses default if not provided)
        
    Returns:
        Initialized ZGServingBroker instance
        
    Raises:
        ConfigurationError: If configuration is invalid
        
    Example:
        >>> from og_compute_sdk import create_broker
        >>> 
        >>> broker = create_broker(
        ...     private_key="0x1234...",
        ...     rpc_url="https://evmrpc-testnet.0g.ai"
        ... )
        >>> 
        >>> # Now use the broker
        >>> services = broker.inference.list_service()
    """
    try:
        # Initialize Web3
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Check connection
        if not web3.is_connected():
            raise ConfigurationError(f"Failed to connect to RPC endpoint: {rpc_url}")
        
        # Create account from private key
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        account = Account.from_key(private_key)
        
        # Create and return broker
        return ZGServingBroker(
            account=account,
            web3=web3,
            contract_address=contract_address
        )
        
    except Exception as e:
        raise ConfigurationError(f"Failed to create broker: {str(e)}")


def create_broker_from_env(
    env_file: str = ".env",
    contract_address: Optional[str] = None
) -> ZGServingBroker:
    """
    Create broker from environment variables.
    
    Expected environment variables:
    - PRIVATE_KEY: Wallet private key
    - RPC_URL: RPC endpoint (optional, defaults to testnet)
    
    Args:
        env_file: Path to .env file
        contract_address: Contract address (uses default if not provided)
        
    Returns:
        Initialized ZGServingBroker instance
        
    Example:
        >>> # In .env file:
        >>> # PRIVATE_KEY=0x1234...
        >>> # RPC_URL=https://evmrpc-testnet.0g.ai
        >>> 
        >>> from og_compute_sdk import create_broker_from_env
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
        
        rpc_url = os.getenv('RPC_URL', 'https://evmrpc-testnet.0g.ai')
        
        return create_broker(
            private_key=private_key,
            rpc_url=rpc_url,
            contract_address=contract_address
        )
        
    except ImportError:
        raise ConfigurationError(
            "python-dotenv is required for create_broker_from_env. "
            "Install with: pip install python-dotenv"
        )
    except Exception as e:
        raise ConfigurationError(f"Failed to create broker from environment: {str(e)}")