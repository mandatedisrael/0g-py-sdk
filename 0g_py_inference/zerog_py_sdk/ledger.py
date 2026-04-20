"""
Ledger management for the 0G Compute Network SDK.

This module handles all account and balance operations including:
- Adding funds to create/top up accounts
- Depositing additional funds
- Checking account balance
- Requesting refunds
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount

from .models import LedgerAccount, LedgerDetail
from .exceptions import ContractError
from .utils import og_to_wei, parse_transaction_receipt

logger = logging.getLogger(__name__)


class LedgerManager:
    """
    Manages ledger operations for the 0G Compute Network.
    
    This class handles all interactions with the LedgerManager contract including
    account creation, deposits, balance checks, and refunds.
    
    Note: The ledger is per-user (wallet), not per-provider.
    """

    # Minimum 0G balance required by the LedgerManager contract to create a ledger.
    # Matches MIN_ACCOUNT_BALANCE on-chain; deposits that would create a new
    # ledger must meet this threshold.
    MIN_LEDGER_BALANCE_OG = 3

    # Recommended minimum transfer to a provider sub-account (1 0G in wei).
    # Matches the broker proxy's MinimumLockedBalance — transfers below this
    # still succeed on-chain, but requests may be rejected by the provider.
    MIN_TRANSFER_AMOUNT_WEI = 10 ** 18

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
            >>> receipt = ledger.add_ledger("3")
        """
        amount_wei = og_to_wei(amount)
        min_wei = self.MIN_LEDGER_BALANCE_OG * 10 ** 18
        if amount_wei < min_wei:
            raise ValueError(
                f"Minimum balance to create a ledger is "
                f"{self.MIN_LEDGER_BALANCE_OG} 0G, but got {amount} 0G. "
                f"Please use: broker.ledger.add_ledger(\"{self.MIN_LEDGER_BALANCE_OG}\")"
            )

        try:
            # addLedger(additionalInfo) - just takes additional info string now
            tx = self.contract.functions.addLedger(
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
        amount_wei = og_to_wei(amount)
        if amount_wei <= 0:
            raise ValueError(
                f"Deposit amount must be greater than 0 0G, but got {amount} 0G"
            )

        # depositFund creates a ledger if one doesn't exist, so the contract's
        # MIN_ACCOUNT_BALANCE applies in that case.
        min_wei = self.MIN_LEDGER_BALANCE_OG * 10 ** 18
        if amount_wei < min_wei:
            try:
                self.get_ledger()
                ledger_exists = True
            except ContractError:
                ledger_exists = False
            if not ledger_exists:
                raise ValueError(
                    f"No ledger exists yet. deposit_fund will create one, but "
                    f"the contract requires a minimum of "
                    f"{self.MIN_LEDGER_BALANCE_OG} 0G. Got {amount} 0G. "
                    f"Please use: broker.ledger.deposit_fund(\"{self.MIN_LEDGER_BALANCE_OG}\")"
                )

        try:
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
    
    def deposit_fund_for(self, recipient: str, amount: str) -> Dict[str, Any]:
        """
        Deposit funds into the ledger for another address.
        
        This allows depositing funds on behalf of another wallet address.
        Useful for funding accounts that will be used by other services
        or users.
        
        Args:
            recipient: Address to deposit funds for
            amount: Amount in OG tokens (e.g., "0.5")
            
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> # Fund another wallet's ledger
            >>> receipt = ledger.deposit_fund_for(
            ...     "0x1234567890123456789012345678901234567890",
            ...     "0.5"
            ... )
        """
        try:
            amount_wei = og_to_wei(amount)
            recipient = self.web3.to_checksum_address(recipient)
            
            # depositFundFor(recipient) - recipient as parameter, amount as value
            tx = self.contract.functions.depositFundFor(
                recipient
            ).build_transaction({
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
                raise ContractError("depositFundFor", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("depositFundFor", str(e))
    
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
            
            # New Ledger struct: (user, availableBalance, totalBalance, additionalInfo)
            available_balance = ledger_data[1] / 10**18  # availableBalance field
            total_balance = ledger_data[2] / 10**18  # totalBalance field
            locked_balance = total_balance - available_balance
            
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
            # Use getLedgerProviders to get the provider list for this service type
            providers = self.contract.functions.getLedgerProviders(
                self.account.address,
                service_type
            ).call()
            
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
        if amount < 0:
            raise ValueError(
                f"Transfer amount must not be negative, but got {amount} wei"
            )
        # amount == 0 is a valid no-op used to provision a provider sub-account.
        # Below the recommended minimum, the transfer succeeds on-chain but the
        # provider may reject requests, so warn the caller.
        if 0 < amount < self.MIN_TRANSFER_AMOUNT_WEI:
            amount_og = amount / 10 ** 18
            logger.warning(
                "Transferring %.6f 0G to provider sub-account. The recommended "
                "minimum is 1 0G; the provider may reject requests if the "
                "sub-account balance is below its minimum threshold.",
                amount_og,
            )

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
    
    def delete_ledger(self) -> Dict[str, Any]:
        """
        Delete the ledger for the current wallet address.
        
        This removes the ledger account entirely. Any remaining balance
        should be withdrawn first using retrieve_fund() and refund().
        
        WARNING: This is a destructive operation. Make sure to withdraw
        all funds before deleting the ledger.
        
        Returns:
            Transaction receipt information
            
        Raises:
            ContractError: If the transaction fails
            
        Example:
            >>> # First withdraw all funds
            >>> ledger.retrieve_fund("inference")
            >>> ledger.refund("0.5")
            >>> 
            >>> # Then delete the ledger
            >>> receipt = ledger.delete_ledger()
        """
        try:
            tx = self.contract.functions.deleteLedger().build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] != 1:
                raise ContractError("deleteLedger", "Transaction failed")
            
            return parse_transaction_receipt(receipt)
            
        except Exception as e:
            raise ContractError("deleteLedger", str(e))
    
    def get_providers_with_balance(self, service_type: str = "inference") -> List[str]:
        """
        Return the list of provider addresses that the user has a sub-account with
        for the given service type.

        Args:
            service_type: "inference" or "fineTuning"

        Returns:
            List of provider addresses (checksummed)

        Raises:
            ContractError: If the contract call fails
        """
        try:
            providers = self.contract.functions.getLedgerProviders(
                self.account.address,
                service_type,
            ).call()
            return [self.web3.to_checksum_address(p) for p in providers]
        except Exception as e:
            raise ContractError("getLedgerProviders", str(e))

    def retrieve_fund_from_provider(
        self,
        provider_address: str,
        service_type: str = "inference",
    ) -> Dict[str, Any]:
        """
        Retrieve funds from a single specific provider sub-account.

        Args:
            provider_address: Provider's wallet address
            service_type: "inference" or "fineTuning"

        Returns:
            Transaction receipt information

        Raises:
            ContractError: If the transaction fails
        """
        try:
            provider_address = self.web3.to_checksum_address(provider_address)

            tx = self.contract.functions.retrieveFund(
                [provider_address],
                service_type,
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
            })

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] != 1:
                raise ContractError("retrieveFund", "Transaction failed")

            return parse_transaction_receipt(receipt)

        except Exception as e:
            raise ContractError("retrieveFundFromProvider", str(e))

    def get_ledger_with_detail(
        self,
        inference_contract: Optional[Contract] = None,
        fine_tuning_contract: Optional[Contract] = None
    ) -> LedgerDetail:
        """
        Get detailed ledger information with provider breakdowns.
        
        Returns comprehensive ledger info including balances for each
        provider in inference and fine-tuning services.
        
        Args:
            inference_contract: Optional InferenceServing contract for account details
            fine_tuning_contract: Optional FineTuning contract for account details
            
        Returns:
            LedgerDetail with total/locked/available balances and provider lists
            
        Example:
            >>> detail = ledger.get_ledger_with_detail()
            >>> print(f"Total: {detail.total_balance}")
            >>> print(f"Available: {detail.available_balance}")
            >>> for provider, balance, pending in detail.inference_providers:
            ...     print(f"Provider {provider}: {balance} (pending: {pending})")
        """
        try:
            # Get base ledger info
            ledger_data = self.contract.functions.getLedger(self.account.address).call()
            
            # Ledger struct: (user, availableBalance, totalBalance, inferenceSigner, additionalInfo, inferenceProviders, fineTuningProviders)
            available_balance = ledger_data[1]
            total_balance = ledger_data[2]
            locked_balance = total_balance - available_balance
            inference_provider_addresses = ledger_data[5] if len(ledger_data) > 5 else []
            fine_tuning_provider_addresses = ledger_data[6] if len(ledger_data) > 6 else []
            
            # Get inference provider details
            inference_providers = []
            if inference_contract and inference_provider_addresses:
                for provider in inference_provider_addresses:
                    try:
                        account = inference_contract.functions.getAccount(
                            self.account.address,
                            provider
                        ).call()
                        # Account: (user, provider, nonce, balance, pendingRefund, ...)
                        balance = account[3]
                        pending_refund = account[4]
                        inference_providers.append((provider, balance, pending_refund))
                    except Exception:
                        # If account doesn't exist, skip
                        pass
            else:
                # Just return addresses without details
                inference_providers = [(addr, 0, 0) for addr in inference_provider_addresses]
            
            # Get fine-tuning provider details
            fine_tuning_providers = []
            if fine_tuning_contract and fine_tuning_provider_addresses:
                for provider in fine_tuning_provider_addresses:
                    try:
                        account = fine_tuning_contract.functions.getAccount(
                            self.account.address,
                            provider
                        ).call()
                        balance = account[3]
                        pending_refund = account[4]
                        fine_tuning_providers.append((provider, balance, pending_refund))
                    except Exception:
                        pass
            else:
                fine_tuning_providers = [(addr, 0, 0) for addr in fine_tuning_provider_addresses]
            
            return LedgerDetail(
                total_balance=total_balance,
                locked_balance=locked_balance,
                available_balance=available_balance,
                inference_providers=inference_providers,
                fine_tuning_providers=fine_tuning_providers
            )
            
        except Exception as e:
            raise ContractError("getLedgerWithDetail", str(e))