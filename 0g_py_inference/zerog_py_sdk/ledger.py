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
from .exceptions import ContractError
from .utils import og_to_wei, parse_transaction_receipt


class LedgerManager:
    """
    Manages ledger operations for the 0G Compute Network.
    
    This class handles all interactions with the LedgerManager contract including
    account creation, deposits, balance checks, and refunds.
    
    Note: The ledger is per-user (wallet), not per-provider.
    """
    
    def __init__(self, contract: Contract, account: LocalAccount, web3: Web3, ):
        """
        Initialize the LedgerManager.
        
        Args:
            contract: LedgerManager contract instance
            account: Local account for signing transactions
            web3: Web3 instance
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
    
    def add_ledger(self, amount: str) -> Dict[str, Any]:
        """
        Add funds to create or top up a ledger account.
        
        This creates an account if it doesn't exist, or adds funds to an existing account.
        
        Args:
            amount: Amount in OG tokens (e.g., "0.1")
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.add_ledger("0.1")
        """
        try:
            amount_wei = og_to_wei(amount)
            
            # addLedger(inferenceSigner, additionalInfo)
            # inferenceSigner is [0, 0] as placeholder
            # additionalInfo is empty string (or encrypted private key)
            tx = self.contract.functions.addLedger(
                [0, 0],  # Inference signer placeholder
                ""  # Additional info (empty for now)
            ).build_transaction({
                'from': self.account.address,
                'value': amount_wei,
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("addLedger", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("addLedger", str(e))
    
    def deposit_fund(self, amount: str) -> Dict[str, Any]:
        """
        Deposit additional funds to an existing ledger account.
        
        Args:
            amount: Amount in OG tokens (e.g., "0.5")
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.deposit_fund("0.5")
        """
        try:
            amount_wei = og_to_wei(amount)
            
            # depositFund() - no parameters, just value
            tx = self.contract.functions.depositFund().build_transaction({
                'from': self.account.address,
                'value': amount_wei,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("depositFund", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("depositFund", str(e))
    
    def get_ledger(self) -> LedgerAccount:
        """
        Get ledger account information for the current user.
        
        Returns:
            LedgerAccount object with balance information
            
        Raises:
            ContractError: If the account doesn't exist or query fails
            
        Example:
            >>> account = ledger.get_ledger()
            >>> print(f"Balance: {account.balance}")
        """
        try:
            # getLedger(user) returns Ledger struct
            ledger_data = self.contract.functions.getLedger(self.account.address).call()
            
            # Ledger struct: (user, availableBalance, totalBalance, inferenceSigner, additionalInfo, inferenceProviders, fineTuningProviders)
            available_balance = ledger_data[1] / 10**18  # availableBalance field
            total_balance = ledger_data[2] / 10**18  # totalBalance field
            locked_balance = total_balance - available_balance  # Already in OG, don't divide again!
            
            return LedgerAccount(
                balance=available_balance,
                locked=locked_balance,
                total_balance=total_balance
            )
            
        except Exception as e:
            raise ContractError("getLedger", str(e))
    
    def retrieve_fund(self, service_type: str = "inference") -> Dict[str, Any]:
        """
        Request refund from all providers of a specific service type.
        
        This withdraws unused funds from the specified service sub-account.
        
        Args:
            service_type: Service type ("inference" or "fineTuning")
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails or no providers found
            
        Example:
            >>> receipt = ledger.retrieve_fund("inference")
        """
        try:
            # Get ledger data to extract provider list
            ledger_data = self.contract.functions.getLedger(self.account.address).call()
            
            # Ledger struct: (user, availableBalance, totalBalance, inferenceSigner, additionalInfo, inferenceProviders, fineTuningProviders)
            if service_type == "inference":
                providers = ledger_data[5]  # inferenceProviders field
            elif service_type == "fineTuning":
                providers = ledger_data[6]  # fineTuningProviders field
            else:
                raise ContractError("retrieveFund", f"Invalid service type: {service_type}")
            
            if not providers or len(providers) == 0:
                raise ContractError("retrieveFund", f"No providers found for service type: {service_type}")
            
            # retrieveFund(providers[], serviceType)
            tx = self.contract.functions.retrieveFund(
                providers,
                service_type
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("retrieveFund", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("retrieveFund", str(e))
    
    def refund(self, amount: str) -> Dict[str, Any]:

        """
        Request refund of specific amount.
        
        Args:
            amount: Amount to refund in OG tokens
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> receipt = ledger.refund("0.1")
        """
        try:
            amount_wei = og_to_wei(amount)
            
            # refund(amount)
            tx = self.contract.functions.refund(amount_wei).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("refund", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:

            raise ContractError("refund", str(e))
        
    def transfer_fund(self, provider_address: str, service_type: str, amount: int = 0) -> Dict[str, Any]:
        """
        Transfer funds to provider (creates account on InferenceServing if amount is 0).

        Args:
            provider_address: Provider address
            service_type: "inference" or "fineTuning"
            amount: Amount in wei (0 to just create account)
        """
        try:
            # Call transferFund on THIS contract (LedgerManager)
            tx = self.contract.functions.transferFund(
                provider_address,
                service_type,
                amount
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,  # Increased gas limit
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("transferFund", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("transferFund", str(e))