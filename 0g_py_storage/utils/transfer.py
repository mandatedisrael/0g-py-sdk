"""
Transfer utilities.

Ported from official TypeScript SDK:
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/transfer/utils.js
- node_modules/@0glabs/0g-ts-sdk/lib.commonjs/utils.js

CRITICAL: Must EXACTLY match TypeScript SDK behavior.
"""
from typing import List, Dict, Any, Optional, Tuple, Callable, TYPE_CHECKING
from dataclasses import dataclass
import time

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt
from eth_account.signers.local import LocalAccount

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ..core.storage_node import StorageNode


@dataclass
class RetryOpts:
    """
    Options for transaction retry with gas adjustment.
    
    TS SDK types.ts RetryOpts.
    """
    retries: int = 10
    interval: int = 5  # seconds
    max_gas_price: int = 0  # 0 means no limit


def _get_storage_node_class():
    """Lazy import to avoid circular dependency."""
    try:
        from ..core.storage_node import StorageNode
        return StorageNode
    except ImportError:
        from core.storage_node import StorageNode
        return StorageNode


def _get_is_valid_config():
    """Lazy import to avoid circular dependency."""
    try:
        from ..core.node_selector import is_valid_config
        return is_valid_config
    except ImportError:
        from core.node_selector import is_valid_config
        return is_valid_config


def get_shard_configs(nodes: List["StorageNode"]) -> Optional[List[Dict[str, Any]]]:
    """
    Get shard configurations from storage nodes.

    TS SDK transfer/utils.js lines 6-16.

    Args:
        nodes: List of storage nodes

    Returns:
        List of shard configs or None if any invalid
    """
    is_valid_config = _get_is_valid_config()
    configs = []
    for c_node in nodes:
        c_config = c_node.get_shard_config()
        if not is_valid_config(c_config):
            return None
        configs.append(c_config)
    return configs


def calculate_price(submission: Dict[str, Any], price_per_sector: int) -> int:
    """
    Calculate storage price for submission.

    TS SDK transfer/utils.js lines 17-23.

    Args:
        submission: Submission structure
        price_per_sector: Price per sector

    Returns:
        Total price
    """
    sectors = 0
    for node in submission['nodes']:
        sectors += 1 << int(node['height'])

    return sectors * price_per_sector


def delay(seconds: float) -> None:
    """
    Delay execution.

    TS SDK utils.js line 22.

    Args:
        seconds: Seconds to delay
    """
    time.sleep(seconds)


def get_split_num(total: int, unit: int) -> int:
    """
    Calculate number of splits.

    TS SDK utils.js lines 38-40.

    Args:
        total: Total size
        unit: Unit size

    Returns:
        Number of splits
    """
    return (total - 1) // unit + 1


def segment_range(start_chunk_index: int, file_size: int) -> tuple:
    """
    Calculate segment range for file.

    TS SDK utils.js lines 49-58.

    Args:
        start_chunk_index: Starting chunk index
        file_size: File size in bytes

    Returns:
        Tuple of (start_segment_index, end_segment_index)
    """
    try:
        from ..config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS
    except ImportError:
        from config import DEFAULT_CHUNK_SIZE, DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 51
    total_chunks = get_split_num(file_size, DEFAULT_CHUNK_SIZE)

    # TS line 53
    start_segment_index = start_chunk_index // DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 55-56
    end_chunk_index = start_chunk_index + total_chunks - 1
    end_segment_index = end_chunk_index // DEFAULT_SEGMENT_MAX_CHUNKS

    # TS line 57
    return (start_segment_index, end_segment_index)


def wait_for_receipt(
    web3: Web3,
    tx_hash: str,
    opts: Optional[RetryOpts] = None
) -> Optional[TxReceipt]:
    """
    Wait for transaction receipt with retries.
    
    TS SDK utils.ts lines 125-156.
    
    Args:
        web3: Web3 instance
        tx_hash: Transaction hash
        opts: Retry options
        
    Returns:
        Transaction receipt or None if timeout
    """
    if opts is None:
        opts = RetryOpts(retries=10, interval=5, max_gas_price=0)
    
    if opts.retries == 0:
        opts.retries = 10
    if opts.interval == 0:
        opts.interval = 5
    
    n_tries = 0
    
    while n_tries < opts.retries:
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            
            if receipt is not None and receipt['status'] == 1:
                return receipt
        except Exception:
            pass
        
        delay(opts.interval)
        n_tries += 1
    
    return None


def tx_with_gas_adjustment(
    web3: Web3,
    contract: Contract,
    account: LocalAccount,
    method: str,
    params: List[Any],
    tx_opts: Dict[str, Any],
    retry_opts: Optional[RetryOpts] = None
) -> Tuple[Optional[TxReceipt], Optional[Exception]]:
    """
    Execute transaction with automatic gas price adjustment on timeout.
    
    TS SDK utils.ts lines 72-123.
    
    If a transaction times out, this function will retry with a 10% higher gas price
    until the max_gas_price is reached.
    
    Args:
        web3: Web3 instance
        contract: Contract instance
        account: Account to sign transaction
        method: Contract method name
        params: Method parameters
        tx_opts: Transaction options (must include 'value' and 'gasPrice')
        retry_opts: Retry options with max_gas_price
        
    Returns:
        Tuple of (receipt, error) - one will be None
    """
    current_gas_price = tx_opts.get('gasPrice', web3.eth.gas_price)
    max_gas_price = current_gas_price
    
    if retry_opts is not None and retry_opts.max_gas_price > 0:
        max_gas_price = retry_opts.max_gas_price
    
    err: Optional[Exception] = None
    
    while current_gas_price <= max_gas_price:
        print(f"Sending transaction with gas price {current_gas_price}")
        tx_opts['gasPrice'] = current_gas_price
        
        try:
            # Get the contract function
            contract_fn = getattr(contract.functions, method)
            
            # Build transaction
            tx_params = {
                'from': account.address,
                'value': tx_opts.get('value', 0),
                'nonce': web3.eth.get_transaction_count(account.address),
                'gasPrice': current_gas_price,
            }
            
            # Add gas limit if specified
            if 'gasLimit' in tx_opts or 'gas' in tx_opts:
                tx_params['gas'] = tx_opts.get('gasLimit', tx_opts.get('gas'))
            else:
                # Estimate gas
                try:
                    tx_params['gas'] = contract_fn(*params).estimate_gas(tx_params)
                except Exception:
                    tx_params['gas'] = 500000  # Fallback
            
            # Build and sign transaction
            tx = contract_fn(*params).build_transaction(tx_params)
            signed_tx = account.sign_transaction(tx)
            
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for transaction to be mined
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt is None:
                raise Exception('Send transaction timeout')
            
            # Wait for receipt with retries
            final_receipt = wait_for_receipt(
                web3,
                tx_hash.hex() if hasattr(tx_hash, 'hex') else tx_hash,
                retry_opts
            )
            
            if final_receipt is None:
                raise Exception('Get transaction receipt timeout')
            
            return (final_receipt, None)
            
        except Exception as e:
            err = e
            error_msg = str(e).lower()
            
            # Check if it's a timeout error
            if 'timeout' in error_msg:
                print(
                    f"Failed to send transaction with gas price {current_gas_price}, "
                    f"with error {e}, retrying with higher gas price"
                )
                # Increase gas price by 10% (multiply by 11/10)
                current_gas_price = (11 * current_gas_price) // 10
                
                delay(1)  # Wait 1 second before retry
            else:
                # Non-timeout error, return immediately
                return (None, err)
    
    return (None, err)


def submit_with_gas_adjustment(
    web3: Web3,
    flow_contract: Contract,
    account: LocalAccount,
    submission: Dict[str, Any],
    fee: int,
    gas_price: int,
    gas_limit: Optional[int] = None,
    retry_opts: Optional[RetryOpts] = None
) -> Tuple[Optional[TxReceipt], Optional[Exception]]:
    """
    Submit to Flow contract with gas auto-adjustment.
    
    Convenience wrapper for tx_with_gas_adjustment for Flow.submit().
    
    Args:
        web3: Web3 instance
        flow_contract: Flow contract instance
        account: Account to sign transaction
        submission: Submission data structure
        fee: Storage fee in wei
        gas_price: Initial gas price
        gas_limit: Optional gas limit
        retry_opts: Retry options with max_gas_price
        
    Returns:
        Tuple of (receipt, error) - one will be None
    """
    tx_opts = {
        'value': fee,
        'gasPrice': gas_price,
    }
    
    if gas_limit is not None and gas_limit > 0:
        tx_opts['gasLimit'] = gas_limit
    
    return tx_with_gas_adjustment(
        web3=web3,
        contract=flow_contract,
        account=account,
        method='submit',
        params=[submission],
        tx_opts=tx_opts,
        retry_opts=retry_opts
    )
