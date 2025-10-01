"""
Utility functions for the 0G Compute Network SDK.

This module provides helper functions for data conversions, validations,
and other common operations.
"""

from typing import Union
from web3 import Web3
from eth_utils import is_address, to_checksum_address


def wei_to_og(amount_wei: int) -> str:
    """
    Convert wei to OG tokens.
    
    Args:
        amount_wei: Amount in wei
        
    Returns:
        Amount in OG tokens as string
        
    Example:
        >>> wei_to_og(1000000000000000000)
        '1.0'
    """
    return Web3.from_wei(amount_wei, 'ether')


def og_to_wei(amount_og: Union[str, float, int]) -> int:
    """
    Convert OG tokens to wei.
    
    Args:
        amount_og: Amount in OG tokens (can be string, float, or int)
        
    Returns:
        Amount in wei
        
    Example:
        >>> og_to_wei("0.1")
        100000000000000000
    """
    return Web3.to_wei(amount_og, 'ether')


def format_address(address: str) -> str:
    """
    Format Ethereum address to checksum format.
    
    Args:
        address: Ethereum address (with or without 0x prefix)
        
    Returns:
        Checksummed Ethereum address
        
    Raises:
        ValueError: If address is invalid
        
    Example:
        >>> format_address("0xf07240efa67755b5311bc75784a061edb47165dd")
        '0xf07240Efa67755B5311bc75784a061eDB47165Dd'
    """
    if not is_address(address):
        raise ValueError(f"Invalid Ethereum address: {address}")
    return to_checksum_address(address)


def validate_provider_address(address: str) -> bool:
    """
    Validate if a provider address is a valid Ethereum address.
    
    Args:
        address: Provider address to validate
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> validate_provider_address("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
        True
        >>> validate_provider_address("invalid")
        False
    """
    return is_address(address)


def format_balance(balance_wei: int, decimals: int = 4) -> str:
    """
    Format balance in wei to human-readable OG token amount.
    
    Args:
        balance_wei: Balance in wei
        decimals: Number of decimal places to display
        
    Returns:
        Formatted balance string with OG suffix
        
    Example:
        >>> format_balance(100000000000000000)
        '0.1000 OG'
    """
    og_amount = float(wei_to_og(balance_wei))
    return f"{og_amount:.{decimals}f} OG"


def validate_amount(amount: Union[str, float, int]) -> bool:
    """
    Validate if an amount is valid (positive number).
    
    Args:
        amount: Amount to validate
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> validate_amount("0.1")
        True
        >>> validate_amount("-1")
        False
    """
    try:
        value = float(amount)
        return value > 0
    except (ValueError, TypeError):
        return False


def parse_transaction_receipt(receipt: dict) -> dict:
    """
    Parse transaction receipt and extract useful information.
    
    Args:
        receipt: Transaction receipt from web3
        
    Returns:
        Dictionary with parsed transaction information
    """
    return {
        "transaction_hash": receipt.get("transactionHash", "").hex() if receipt.get("transactionHash") else None,
        "block_number": receipt.get("blockNumber"),
        "gas_used": receipt.get("gasUsed"),
        "status": receipt.get("status"),
        "success": receipt.get("status") == 1
    }