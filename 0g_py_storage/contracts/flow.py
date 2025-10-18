from typing import List, Dict, Any, Optional, Tuple
from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt
from eth_account import Account
from eth_account.signers.local import LocalAccount
import time

try:
    from .abis import FLOW_CONTRACT_ABI, get_flow_contract_address
except ImportError:
    from abis import FLOW_CONTRACT_ABI, get_flow_contract_address


class FlowContract:
    """
    Wrapper for 0G Flow smart contract.

    Provides methods to submit file metadata to the Flow contract
    which tracks uploaded files on-chain.
    """

    def __init__(
        self,
        web3: Web3,
        contract_address: Optional[str] = None,
        network: str = "testnet"
    ):
        """
        Initialize Flow contract wrapper.

        Args:
            web3: Web3 instance connected to 0G network
            contract_address: Flow contract address (optional, defaults to network address)
            network: Network name ("testnet" or "mainnet")
        """
        self.web3 = web3
        self.network = network

        # Get contract address
        if contract_address is None:
            contract_address = get_flow_contract_address(network)

        self.contract_address = Web3.to_checksum_address(contract_address)

        # Create contract instance
        self.contract: Contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=FLOW_CONTRACT_ABI
        )

    def submit(
        self,
        submission: Dict[str, Any],
        account: LocalAccount,
        value: int = 0,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None
    ) -> TxReceipt:
        """
        Submit file metadata to Flow contract.

        Matches TS SDK Uploader.submitTransaction() behavior.

        Args:
            submission: Submission data structure containing:
                - length: File size in bytes
                - tags: Additional metadata (bytes)
                - nodes: List of merkle tree nodes, each containing:
                    - root: Merkle root hash (bytes32)
                    - height: Tree height (uint256)
            account: Account to sign transaction
            value: ETH value to send with transaction (fee)
            gas_limit: Gas limit for transaction (optional)
            gas_price: Gas price in wei (optional)

        Returns:
            Transaction receipt

        Raises:
            Exception: If transaction fails
        """
        # Build transaction params
        tx_params = {
            'from': account.address,
            'value': value,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        }

        # Gas price handling (TS SDK lines 100-112)
        if gas_price is not None and gas_price > 0:
            tx_params['gasPrice'] = gas_price
        else:
            # Get suggested gas price from network
            suggested_gas = self.web3.eth.gas_price
            if suggested_gas is None:
                raise Exception("Failed to get suggested gas price, set your own gas price")
            tx_params['gasPrice'] = suggested_gas

        # Gas limit
        if gas_limit is not None and gas_limit > 0:
            tx_params['gas'] = gas_limit

        # Build transaction
        tx = self.contract.functions.submit(submission).build_transaction(tx_params)

        # Sign transaction
        signed_tx = account.sign_transaction(tx)

        # Send transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        # Check if transaction succeeded
        if receipt['status'] != 1:
            raise Exception(f"Transaction failed: {tx_hash.hex()}")

        return receipt

    def batch_submit(
        self,
        submissions: List[Dict[str, Any]],
        account: LocalAccount,
        value: int = 0,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None
    ) -> Tuple[str, List[int], List[str], List[int], List[int]]:
        """
        Submit multiple files in a single transaction.

        Args:
            submissions: List of submission data structures
            account: Account to sign transaction
            value: ETH value to send with transaction (default: 0)
            gas_limit: Gas limit for transaction (optional)
            gas_price: Gas price in wei (optional)

        Returns:
            Tuple of (tx_hash, indexes, digests, start_indexes, lengths)

        Raises:
            Exception: If transaction fails
        """
        # Build transaction
        tx_params = {
            'from': account.address,
            'value': value,
            'nonce': self.web3.eth.get_transaction_count(account.address),
        }

        if gas_limit is not None:
            tx_params['gas'] = gas_limit

        if gas_price is not None:
            tx_params['gasPrice'] = gas_price

        # Build and send transaction
        tx = self.contract.functions.batchSubmit(submissions).build_transaction(tx_params)

        # Sign transaction
        signed_tx = account.sign_transaction(tx)

        # Send transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        # Check if transaction succeeded
        if receipt['status'] != 1:
            raise Exception(f"Batch transaction failed: {tx_hash.hex()}")

        # Return transaction hash and submission count
        return (
            tx_hash.hex(),
            [],  # indexes - would need to parse from logs
            [],  # digests - would need to parse from logs
            [],  # start_indexes - would need to parse from logs
            [s['length'] for s in submissions]  # lengths
        )

    def process_logs(self, receipt: TxReceipt) -> List[int]:
        """
        Parse transaction logs to extract submission indexes.

        Matches TS SDK Uploader.processLogs() (lines 140-173).

        Args:
            receipt: Transaction receipt

        Returns:
            List of submission indexes (txSeqs)
        """
        contract_address = self.contract_address.lower()

        # Get Submit event signature
        submit_event = self.contract.events.Submit()
        event_signature = submit_event.build_filter().topics[0]

        # Normalize event signature to hex string
        def _to_hex_str(x):
            try:
                return Web3.to_hex(x).lower()
            except Exception:
                return (x if isinstance(x, str) else str(x)).lower()

        event_sig_hex = _to_hex_str(event_signature)

        tx_seqs = []

        for log in receipt['logs']:
            # Only process logs from this contract
            if log['address'].lower() != contract_address:
                continue

            # Check if this is a Submit event
            if len(log['topics']) == 0:
                continue

            topic0_hex = _to_hex_str(log['topics'][0])
            if topic0_hex != event_sig_hex:
                continue

            try:
                # Parse the log using contract's event
                parsed_log = submit_event.process_log(log)

                # Extract submissionIndex from event args
                if 'submissionIndex' in parsed_log['args']:
                    tx_seqs.append(parsed_log['args']['submissionIndex'])
            except Exception:
                # If parsing fails, skip this log
                continue

        return tx_seqs

    def get_submission_info(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get submission information from transaction receipt.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dictionary with submission details

        Raises:
            Exception: If transaction not found
        """
        receipt = self.web3.eth.get_transaction_receipt(tx_hash)

        if receipt is None:
            raise Exception(f"Transaction not found: {tx_hash}")

        return {
            'transaction_hash': tx_hash,
            'block_number': receipt['blockNumber'],
            'status': receipt['status'],
            'gas_used': receipt['gasUsed'],
        }

    def wait_for_receipt(
        self,
        tx_hash: str,
        max_retries: int = 10,
        interval: int = 5
    ) -> Optional[TxReceipt]:
        """
        Wait for transaction receipt with retries.

        Matches TS SDK Uploader.waitForReceipt() (lines 174-189).

        Args:
            tx_hash: Transaction hash
            max_retries: Maximum number of retries
            interval: Interval between retries in seconds

        Returns:
            Transaction receipt or None if timeout
        """
        n_tries = 0

        while n_tries < max_retries:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)

                if receipt is not None and receipt['status'] == 1:
                    return receipt
            except Exception:
                pass

            time.sleep(interval)
            n_tries += 1

        return None

    @staticmethod
    def create_submission(
        length: int,
        nodes: List[Tuple[str, int]],
        tags: bytes = b''
    ) -> Dict[str, Any]:
        """
        Create a submission data structure.

        Args:
            length: File size in bytes
            nodes: List of (root_hash, height) tuples
            tags: Optional metadata bytes

        Returns:
            Submission dictionary ready for contract call
        """
        return {
            'length': length,
            'tags': tags,
            'nodes': [
                {'root': root, 'height': height}
                for root, height in nodes
            ]
        }
