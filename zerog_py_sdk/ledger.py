"""
Ledger management for the 0G Compute Network SDK.

This module handles all account and balance operations including:
- Adding funds to create/top up accounts
- Depositing additional funds
- Checking account balance
- Requesting refunds
"""

from typing import Dict, Any
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount

from .models import LedgerAccount
from .exceptions import ContractError, InsufficientBalanceError
from .utils import og_to_wei, wei_to_og, parse_transaction_receipt


class LedgerManager:
    """
    Manages ledger operations for the 0G Compute Network.
    
    This class handles all interactions with the ledger contract including
    account creation, deposits, balance checks, and refunds.
    """
    
    def __init__(self, contract: Contract, account: LocalAccount, web3: Web3):
        """
        Initialize the LedgerManager.
        
        Args:
            contract: Web3 contract instance
            account: Local account for signing transactions
            web3: Web3 instance
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
    
    def add_ledger(self, amount: str, provider: str) -> Dict[str, Any]:
        """
        Add funds to create or top up a ledger account for a specific provider.
        
        This creates an account if it doesn't exist, or adds funds to an existing account.
        
        Args:
            amount: Amount in OG tokens (e.g., "0.1")
            provider: Provider address to create account with
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.add_ledger("0.1", "0xf07240Efa67755B5311bc75784a061eDB47165Dd")
        """
        try:
            amount_wei = og_to_wei(amount)
            
            # addAccount(user, provider, signer, additionalInfo)
            # signer is [0, 0] as placeholder, additionalInfo is empty string
            tx = self.contract.functions.addAccount(
                self.account.address,
                provider,
                [0, 0],  # Signer placeholder
                ""  # Additional info
            ).build_transaction({
                'from': self.account.address,
                'value': amount_wei,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("addAccount", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("addAccount", str(e))
    
    def deposit_fund(self, amount: str, provider: str) -> Dict[str, Any]:
        """
        Deposit additional funds to an existing ledger account.
        
        Args:
            amount: Amount in OG tokens (e.g., "0.5")
            provider: Provider address for the account
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.deposit_fund("0.5", "0xf07240Efa67755B5311bc75784a061eDB47165Dd")
        """
        try:
            amount_wei = og_to_wei(amount)
            
            # depositFund(user, provider, cancelRetrievingAmount)
            tx = self.contract.functions.depositFund(
                self.account.address,
                provider,
                0  # cancelRetrievingAmount - 0 means no cancellation
            ).build_transaction({
                'from': self.account.address,
                'value': amount_wei,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("depositFund", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("depositFund", str(e))
    
    def get_ledger(self, provider: str) -> LedgerAccount:
        """
        Get ledger account information for a specific provider.
        
        Args:
            provider: Provider address
            
        Returns:
            LedgerAccount object with balance information
            
        Raises:
            ContractError: If the account doesn't exist or query fails
            
        Example:
            >>> account = ledger.get_ledger("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
            >>> print(f"Balance: {account.balance}")
        """
        try:
            # getAccount(user, provider) returns Account struct
            account_data = self.contract.functions.getAccount(
                self.account.address,
                provider
            ).call()
            
            # Account struct: (user, provider, nonce, balance, pendingRefund, signer, refunds, additionalInfo, providerPubKey, teeSignerAddress, validRefundsLength)
            balance = account_data[3]  # balance field
            pending_refund = account_data[4]  # pendingRefund field
            
            return LedgerAccount(
                balance=balance,
                locked=pending_refund,
                total_balance=balance + pending_refund
            )
            
        except Exception as e:
            raise ContractError("getAccount", str(e))
    
    def retrieve_fund(self, provider: str) -> Dict[str, Any]:
        """
        Request refund of all available funds from a provider account.
        
        This initiates a refund request which will be processed after a lock period.
        
        Args:
            provider: Provider address
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.retrieve_fund("0xf07240Efa67755B5311bc75784a061eDB47165Dd")
        """
        try:
            # requestRefundAll(user, provider)
            tx = self.contract.functions.requestRefundAll(
                self.account.address,
                provider
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("requestRefundAll", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("requestRefundAll", str(e))
    
    def _build_transaction(self, function_call, value: int = 0, gas: int = 100000) -> Dict[str, Any]:
        """
        Build a transaction with common parameters.
        
        Args:
            function_call: Contract function call
            value: ETH value to send (in wei)
            gas: Gas limit
            
        Returns:
            Transaction dictionary
        """
        return function_call.build_transaction({
            'from': self.account.address,
            'value': value,
            'gas': gas,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.account.address)
        })
    
    def _send_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign and send a transaction.
        
        Args:
            tx: Transaction dictionary
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If transaction fails
        """
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] != 1:
            raise ContractError("transaction", "Transaction failed")
        
        return parse_transaction_receipt(receipt)