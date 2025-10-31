"""
0G Storage Market Contract Wrapper

Provides access to the market contract for pricing and storage fee calculations.
"""

from typing import Optional
from web3 import Web3
from web3.contract import Contract

# Market contract ABI (FixedPrice contract with pricePerSector function)
MARKET_CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "pricePerSector",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]


def get_market_contract(
    market_address: str, web3: Web3
) -> Contract:
    """
    Get market contract instance.

    Args:
        market_address: Address of the market contract
        web3: Web3 instance connected to the network

    Returns:
        Market contract instance

    Raises:
        Exception: If market address is invalid
    """
    if not market_address or market_address == "0x0000000000000000000000000000000000000000":
        raise Exception("Invalid market contract address")

    # Normalize address
    market_address = Web3.to_checksum_address(market_address)

    # Create contract instance
    contract = web3.eth.contract(address=market_address, abi=MARKET_CONTRACT_ABI)

    return contract
