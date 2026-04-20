"""
Network constants and contract addresses for the 0G Compute Network SDK.

This module provides network configurations matching the official TypeScript SDK.
Use get_contract_addresses() to get the appropriate addresses for your network.

Reference: TypeScript SDK src.ts/sdk/constants.ts
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass


# Chain IDs
TESTNET_CHAIN_ID = 16602
MAINNET_CHAIN_ID = 16661
HARDHAT_CHAIN_ID = 31337

# Default RPC URLs
RPC_URLS = {
    "testnet": "https://evmrpc-testnet.0g.ai",
    "mainnet": "https://evmrpc.0g.ai",
}


@dataclass
class NetworkAddresses:
    """Contract addresses for a specific network."""
    ledger: str
    inference: str
    fine_tuning: str


# Contract addresses matching TypeScript SDK (as of Feb 2026)
CONTRACT_ADDRESSES: Dict[str, NetworkAddresses] = {
    "testnet": NetworkAddresses(
        ledger="0xE70830508dAc0A97e6c087c75f402f9Be669E406",
        inference="0xa79F4c8311FF93C06b8CfB403690cc987c93F91E",
        fine_tuning="0xC6C075D8039763C8f1EbE580be5ADdf2fd6941bA",
    ),
    "testnet_dev": NetworkAddresses(
        ledger="0x815B93ab4Ba4BDF530dbF1552649a3c534F8BbF7",
        inference="0x41bD7Ac5c19000A974D5c192bcd5FB67b56C85c5",
        fine_tuning="0x4e4158DF35CfdC0ac63264D3E112F5B8E9a5c569",
    ),
    "mainnet": NetworkAddresses(
        ledger="0x2dE54c845Cd948B72D2e32e39586fe89607074E3",
        inference="0x47340d900bdFec2BD393c626E12ea0656F938d84",
        fine_tuning="0x4e3474095518883744ddf135b7E0A23301c7F9c0",
    ),
    "hardhat": NetworkAddresses(
        ledger="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0",
        inference="0x0165878A594ca255338adfa4d48449f69242Eb8F",
        fine_tuning="0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0",
    ),
}

# Legacy aliases for backward compatibility
AUTOMATA_CONTRACT_ADDRESS = "0xE26E11B257856B0bEBc4C759aaBDdea72B64351F"


def is_dev_mode() -> bool:
    """
    Check if dev mode is enabled.
    
    Supports:
    - ZG_DEV_MODE environment variable
    - NEXT_PUBLIC_ZG_DEV_MODE environment variable (for Next.js)
    
    Returns:
        True if dev mode is enabled
    """
    dev_mode = os.environ.get("ZG_DEV_MODE", "").lower()
    if dev_mode in ("true", "1"):
        return True
    
    next_dev_mode = os.environ.get("NEXT_PUBLIC_ZG_DEV_MODE", "").lower()
    if next_dev_mode in ("true", "1"):
        return True
    
    return False


def get_network_from_chain_id(chain_id: int) -> str:
    """
    Get network name from chain ID.
    
    Args:
        chain_id: The blockchain chain ID
        
    Returns:
        Network name: "mainnet", "testnet", or "hardhat"
    """
    if chain_id == MAINNET_CHAIN_ID:
        return "mainnet"
    elif chain_id == TESTNET_CHAIN_ID:
        if is_dev_mode():
            return "testnet_dev"
        return "testnet"
    elif chain_id == HARDHAT_CHAIN_ID:
        return "hardhat"
    else:
        # Default to mainnet for unknown chain IDs
        return "mainnet"


def get_contract_addresses(
    network: Optional[str] = None,
    chain_id: Optional[int] = None
) -> NetworkAddresses:
    """
    Get contract addresses for a network.
    
    Args:
        network: Network name ("mainnet", "testnet", "testnet_dev", "hardhat")
        chain_id: Chain ID (alternative to network name)
        
    Returns:
        NetworkAddresses with ledger, inference, and fine_tuning addresses
        
    Example:
        >>> addrs = get_contract_addresses("mainnet")
        >>> print(addrs.inference)
        
        >>> # Or auto-detect from chain ID
        >>> addrs = get_contract_addresses(chain_id=16661)
    """
    if network is None and chain_id is not None:
        network = get_network_from_chain_id(chain_id)
    
    if network is None:
        # Default to mainnet (testnet_dev still applies when dev mode is on)
        network = "testnet_dev" if is_dev_mode() else "mainnet"
    
    if network not in CONTRACT_ADDRESSES:
        raise ValueError(f"Unknown network: {network}. Valid options: {list(CONTRACT_ADDRESSES.keys())}")
    
    return CONTRACT_ADDRESSES[network]


def get_rpc_url(network: str = "mainnet") -> str:
    """
    Get default RPC URL for a network.

    Args:
        network: "mainnet" or "testnet"

    Returns:
        RPC URL string
    """
    if network == "testnet":
        return RPC_URLS["testnet"]
    return RPC_URLS["mainnet"]


# Legacy exports for backward compatibility
DEFAULT_LEDGER_ADDRESS = CONTRACT_ADDRESSES["mainnet"].ledger
DEFAULT_SERVING_ADDRESS = CONTRACT_ADDRESSES["mainnet"].inference
DEFAULT_FINETUNING_ADDRESS = CONTRACT_ADDRESSES["mainnet"].fine_tuning
