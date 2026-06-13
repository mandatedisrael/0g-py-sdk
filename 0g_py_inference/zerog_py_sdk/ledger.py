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
from .contract_errors import contract_error_from_exception
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

    # Canonical service-type keys accepted by transfer_fund. Internally these
    # are resolved to the deployed service's registered fullName via
    # LedgerManager.getServiceInfo, matching the TS SDK.
    _CANONICAL_SERVICE_TYPES = ("inference", "fine-tuning")

    def __init__(
        self,
        contract: Contract,
        account: LocalAccount,
        web3: Web3,
        inference_address: Optional[str] = None,
        fine_tuning_address: Optional[str] = None,
        inference_contract: Optional[Contract] = None,
        fine_tuning_contract: Optional[Contract] = None,
    ):
        """
        Initialize the LedgerManager.

        Args:
            contract: LedgerManager contract instance
            account: Local account for signing transactions
            web3: Web3 instance
            inference_address: InferenceServing contract address. Required to
                resolve the registered service name for inference transfers.
            fine_tuning_address: FineTuningServing contract address. Optional;
                if omitted, fine-tuning transfers must supply an explicit name.
            inference_contract: Optional pre-built inference contract.
            fine_tuning_contract: Optional pre-built fine-tuning contract.
        """
        self.contract = contract
        self.account = account
        self.web3 = web3
        self._inference_address = inference_address
        self._fine_tuning_address = fine_tuning_address
        self._service_names: Optional[Dict[str, Optional[str]]] = None

        if inference_contract is None and inference_address:
            from .contracts.abis import SERVING_CONTRACT_ABI

            inference_contract = web3.eth.contract(
                address=Web3.to_checksum_address(inference_address),
                abi=SERVING_CONTRACT_ABI,
            )
        if fine_tuning_contract is None and fine_tuning_address:
            from .fine_tuning.contract.abi import FINE_TUNING_SERVING_ABI

            fine_tuning_contract = web3.eth.contract(
                address=Web3.to_checksum_address(fine_tuning_address),
                abi=FINE_TUNING_SERVING_ABI,
            )

        self._inference_contract = inference_contract
        self._fine_tuning_contract = fine_tuning_contract

    def _resolve_service_names(self) -> Dict[str, Optional[str]]:
        """
        Fetch and cache the on-chain registered service names.

        Mirrors the TS SDK: looks up each service contract address via
        LedgerManager.getServiceInfo(serviceAddress).fullName. Fine-tuning
        lookup is tolerated to fail — not every deployment registers it.
        """
        if self._service_names is not None:
            return self._service_names

        names: Dict[str, Optional[str]] = {"inference": None, "fine-tuning": None}

        if self._inference_address:
            try:
                info = self.contract.functions.getServiceInfo(
                    Web3.to_checksum_address(self._inference_address)
                ).call()
                # ServiceInfo tuple: (serviceAddress, serviceContract, serviceType,
                # version, fullName, description, serviceId, registeredAt)
                names["inference"] = info[4] or None
            except Exception as e:
                logger.warning("Failed to resolve inference service name: %s", e)

        if self._fine_tuning_address:
            try:
                info = self.contract.functions.getServiceInfo(
                    Web3.to_checksum_address(self._fine_tuning_address)
                ).call()
                names["fine-tuning"] = info[4] or None
            except Exception as e:
                logger.debug("Fine-tuning service not registered: %s", e)

        self._service_names = names
        return names

    def _resolve_service_name(self, service_type: str, operation: str) -> str:
        """Resolve a canonical service key to its registered on-chain name."""
        if service_type not in self._CANONICAL_SERVICE_TYPES:
            return service_type

        resolved = self._resolve_service_names().get(service_type)
        if not resolved:
            raise ContractError(
                operation,
                f"Could not resolve on-chain service name for "
                f"{service_type!r}. The service contract may not be "
                f"registered on this network.",
            )
        return resolved
    
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
            raise contract_error_from_exception("addLedger", e) from e
    
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
            raise contract_error_from_exception("depositFund", e) from e
    
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
            raise contract_error_from_exception("depositFundFor", e) from e
    
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
            available_balance = ledger_data[1]  # availableBalance field (wei)
            total_balance = ledger_data[2]      # totalBalance field (wei)
            locked_balance = total_balance - available_balance

            return LedgerAccount(
                balance=available_balance,
                locked=locked_balance,
                total_balance=total_balance
            )
            
        except Exception as e:
            raise contract_error_from_exception("getLedger", e) from e
    
    def list_ledger(self, offset: int = 0, limit: int = 50) -> List[tuple]:
        """
        List all ledger accounts on the contract (paginated).

        Mirrors the TS SDK's ``LedgerProcessor.listLedger`` which proxies
        ``getAllLedgers(offset, limit)``.

        Returns:
            List of raw ledger tuples (user, availableBalance, totalBalance, additionalInfo).
        """
        try:
            ledgers, _total = self.contract.functions.getAllLedgers(offset, limit).call()
            return list(ledgers)
        except Exception as e:
            raise contract_error_from_exception("listLedger", e) from e

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
            resolved_name = self._resolve_service_name(
                service_type, "retrieveFund"
            )
            detail = self.get_ledger_with_detail()
            provider_details = (
                detail.inference_providers
                if service_type == "inference"
                else detail.fine_tuning_providers
            )
            providers = [
                provider
                for provider, balance, pending_refund in provider_details
                if balance - pending_refund >= 0
            ]
            
            if not providers or len(providers) == 0:
                raise ContractError("retrieveFund", f"No providers found for service type: {service_type}")
            
            # retrieveFund(providers[], serviceType)
            tx = self.contract.functions.retrieveFund(
                providers,
                resolved_name
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
            raise contract_error_from_exception("retrieveFund", e) from e
    
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
            raise contract_error_from_exception("refund", e) from e
        
    def transfer_fund(self, provider_address: str, service_type: str, amount: int = 0) -> Dict[str, Any]:
        """
        Transfer funds to provider (creates account on InferenceServing if amount is 0).

        Args:
            provider_address: Provider address
            service_type: Canonical key ``"inference"`` or ``"fine-tuning"``.
                The SDK resolves this to the on-chain registered service name
                via LedgerManager.getServiceInfo. Any other string is passed
                through unchanged for callers that already hold an exact name.
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

        resolved_name = self._resolve_service_name(
            service_type, "transferFund"
        )

        try:
            # Call transferFund on THIS contract (LedgerManager)
            tx = self.contract.functions.transferFund(
                provider_address,
                resolved_name,
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
            raise contract_error_from_exception("transferFund", e) from e
    
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
            raise contract_error_from_exception("deleteLedger", e) from e
    
    def get_providers_with_balance(
        self, service_type: str = "inference"
    ) -> List[Tuple[str, int, int]]:
        """
        Return providers with a non-zero balance or pending refund.

        Args:
            service_type: "inference" or "fineTuning"

        Returns:
            List of (provider, balance, pending_refund) tuples

        Raises:
            ContractError: If the contract call fails
        """
        detail = self.get_ledger_with_detail()
        providers = (
            detail.inference_providers
            if service_type == "inference"
            else detail.fine_tuning_providers
        )
        return [
            provider
            for provider in providers
            if provider[1] > 0 or provider[2] > 0
        ]

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
            resolved_name = self._resolve_service_name(
                service_type, "retrieveFundFromProvider"
            )

            tx = self.contract.functions.retrieveFund(
                [provider_address],
                resolved_name,
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
            raise contract_error_from_exception(
                "retrieveFundFromProvider", e
            ) from e

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
            inference_contract = (
                inference_contract or self._inference_contract
            )
            fine_tuning_contract = (
                fine_tuning_contract or self._fine_tuning_contract
            )

            # Get base ledger info
            ledger_data = self.contract.functions.getLedger(self.account.address).call()
            
            # Ledger struct: (user, availableBalance, totalBalance, inferenceSigner, additionalInfo, inferenceProviders, fineTuningProviders)
            available_balance = ledger_data[1]
            total_balance = ledger_data[2]
            locked_balance = total_balance - available_balance

            service_names = self._resolve_service_names()
            inference_name = service_names.get("inference")
            if not inference_name:
                raise ContractError(
                    "getLedgerWithDetail",
                    "Inference service name is not available",
                )

            inference_provider_addresses = self.contract.functions.getLedgerProviders(
                self.account.address, inference_name
            ).call()

            fine_tuning_name = service_names.get("fine-tuning")
            fine_tuning_provider_addresses = []
            if fine_tuning_contract and fine_tuning_name:
                fine_tuning_provider_addresses = (
                    self.contract.functions.getLedgerProviders(
                        self.account.address, fine_tuning_name
                    ).call()
                )
            
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
                        inference_providers.append((
                            self.web3.to_checksum_address(provider),
                            balance,
                            pending_refund,
                        ))
                    except Exception:
                        # If account doesn't exist, skip
                        pass
            else:
                inference_providers = []
            
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
                        fine_tuning_providers.append((
                            self.web3.to_checksum_address(provider),
                            balance,
                            pending_refund,
                        ))
                    except Exception:
                        pass
            else:
                fine_tuning_providers = []
            
            return LedgerDetail(
                total_balance=total_balance,
                locked_balance=locked_balance,
                available_balance=available_balance,
                inference_providers=inference_providers,
                fine_tuning_providers=fine_tuning_providers
            )
            
        except Exception as e:
            raise contract_error_from_exception("getLedgerWithDetail", e) from e
