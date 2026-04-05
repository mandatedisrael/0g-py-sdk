from typing import Dict, Any, List, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount

from ...exceptions import ContractError
from ...utils import parse_transaction_receipt
from .abi import FINE_TUNING_SERVING_ABI
from .types import (
    Quota,
    Deliverable,
    FineTuningAccountDetails,
    FineTuningService,
    FineTuningRefund,
)

RETRY_ERROR_SUBSTRINGS = [
    "transaction underpriced",
    "replacement transaction underpriced",
    "fee too low",
    "mempool",
]

DEFAULT_GAS_LIMIT = 300000
TX_TIMEOUT = 300


class FineTuningContract:
    def __init__(
        self,
        account: LocalAccount,
        web3: Web3,
        contract_address: str,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
        step: int = 11,
    ):
        self.account = account
        self.web3 = web3
        self.contract: Contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=FINE_TUNING_SERVING_ABI,
        )
        self._gas_price = gas_price
        self._max_gas_price = max_gas_price
        self._step = step

    def _get_gas_price(self, override: Optional[int] = None) -> int:
        if override is not None:
            return override
        if self._gas_price is not None:
            return self._gas_price
        return self.web3.eth.gas_price

    def _send_tx(
        self,
        fn_name: str,
        tx_func,
        value: int = 0,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        current_gas_price = self._get_gas_price(gas_price)

        while True:
            try:
                tx = tx_func.build_transaction({
                    "from": self.account.address,
                    "value": value,
                    "gas": DEFAULT_GAS_LIMIT,
                    "gasPrice": current_gas_price,
                    "nonce": self.web3.eth.get_transaction_count(self.account.address),
                })

                signed_tx = self.account.sign_transaction(tx)
                tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.web3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=TX_TIMEOUT
                )

                if receipt["status"] != 1:
                    raise ContractError(fn_name, "Transaction reverted")

                return parse_transaction_receipt(receipt)

            except Exception as e:
                err_msg = str(e).lower()
                should_retry = any(sub in err_msg for sub in RETRY_ERROR_SUBSTRINGS)

                if should_retry and self._max_gas_price:
                    new_price = (current_gas_price * self._step) // 10
                    if new_price <= self._max_gas_price:
                        current_gas_price = new_price
                        continue

                raise ContractError(fn_name, str(e))

    # --- Read-only methods ---

    def lock_time(self) -> int:
        try:
            return self.contract.functions.lockTime().call()
        except Exception as e:
            raise ContractError("lockTime", str(e))

    def get_chain_id(self) -> int:
        return self.web3.eth.chain_id

    def list_service(self, include_unacknowledged: bool = False) -> List[FineTuningService]:
        try:
            raw_services = self.contract.functions.getAllServices().call()
            services = [self._parse_service(s) for s in raw_services]
            if not include_unacknowledged:
                services = [s for s in services if s.tee_signer_acknowledged]
            return services
        except Exception as e:
            raise ContractError("getAllServices", str(e))

    def get_service(self, provider_address: str) -> FineTuningService:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            raw = self.contract.functions.getService(provider_address).call()
            return self._parse_service(raw)
        except Exception as e:
            raise ContractError("getService", str(e))

    def get_account(self, provider_address: str) -> FineTuningAccountDetails:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            raw = self.contract.functions.getAccount(
                self.account.address, provider_address
            ).call()
            return self._parse_account(raw)
        except Exception as e:
            raise ContractError("getAccount", str(e))

    def account_exists(self, provider_address: str) -> bool:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            return self.contract.functions.accountExists(
                self.account.address, provider_address
            ).call()
        except Exception as e:
            raise ContractError("accountExists", str(e))

    def get_deliverable(
        self, provider_address: str, deliverable_id: str
    ) -> Deliverable:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            raw = self.contract.functions.getDeliverable(
                self.account.address, provider_address, deliverable_id
            ).call()
            return self._parse_deliverable(raw)
        except Exception as e:
            raise ContractError("getDeliverable", str(e))

    def get_deliverables(self, provider_address: str) -> List[Deliverable]:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            raw_list = self.contract.functions.getDeliverables(
                self.account.address, provider_address
            ).call()
            return [self._parse_deliverable(d) for d in raw_list]
        except Exception as e:
            raise ContractError("getDeliverables", str(e))

    def get_pending_refund(self, provider_address: str) -> int:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            return self.contract.functions.getPendingRefund(
                self.account.address, provider_address
            ).call()
        except Exception as e:
            raise ContractError("getPendingRefund", str(e))

    # --- Write methods ---

    def acknowledge_tee_signer(
        self, provider_address: str, acknowledged: bool = True, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        provider_address = Web3.to_checksum_address(provider_address)
        return self._send_tx(
            "acknowledgeTEESigner",
            self.contract.functions.acknowledgeTEESigner(provider_address, acknowledged),
            gas_price=gas_price,
        )

    def acknowledge_tee_signer_by_owner(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        provider_address = Web3.to_checksum_address(provider_address)
        return self._send_tx(
            "acknowledgeTEESignerByOwner",
            self.contract.functions.acknowledgeTEESignerByOwner(provider_address),
            gas_price=gas_price,
        )

    def revoke_tee_signer_acknowledgement(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        provider_address = Web3.to_checksum_address(provider_address)
        return self._send_tx(
            "revokeTEESignerAcknowledgement",
            self.contract.functions.revokeTEESignerAcknowledgement(provider_address),
            gas_price=gas_price,
        )

    def acknowledge_deliverable(
        self, provider_address: str, deliverable_id: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        provider_address = Web3.to_checksum_address(provider_address)
        return self._send_tx(
            "acknowledgeDeliverable",
            self.contract.functions.acknowledgeDeliverable(
                provider_address, deliverable_id
            ),
            gas_price=gas_price,
        )

    def remove_service(self, gas_price: Optional[int] = None) -> Dict[str, Any]:
        return self._send_tx(
            "removeService",
            self.contract.functions.removeService(),
            gas_price=gas_price,
        )

    # --- Parsing helpers ---

    @staticmethod
    def _parse_quota(raw) -> Quota:
        return Quota(
            cpu_count=raw[0],
            node_memory=raw[1],
            gpu_count=raw[2],
            node_storage=raw[3],
            gpu_type=raw[4],
        )

    @staticmethod
    def _parse_deliverable(raw) -> Deliverable:
        return Deliverable(
            id=raw[0],
            model_root_hash=raw[1],
            encrypted_secret=raw[2],
            acknowledged=raw[3],
            timestamp=raw[4],
            settled=raw[5],
        )

    @staticmethod
    def _parse_refund(raw) -> FineTuningRefund:
        return FineTuningRefund(
            index=raw[0],
            amount=raw[1],
            created_at=raw[2],
            deprecated_processed=raw[3],
        )

    @classmethod
    def _parse_service(cls, raw) -> FineTuningService:
        return FineTuningService(
            provider=raw[0],
            url=raw[1],
            quota=cls._parse_quota(raw[2]),
            price_per_token=raw[3],
            occupied=raw[4],
            models=list(raw[5]) if raw[5] else [],
            tee_signer_address=raw[6],
            tee_signer_acknowledged=raw[7],
        )

    @classmethod
    def _parse_account(cls, raw) -> FineTuningAccountDetails:
        refunds = [cls._parse_refund(r) for r in raw[5]] if raw[5] else []
        deliverables = [cls._parse_deliverable(d) for d in raw[7]] if raw[7] else []

        return FineTuningAccountDetails(
            user=raw[0],
            provider=raw[1],
            nonce=raw[2],
            balance=raw[3],
            pending_refund=raw[4],
            refunds=refunds,
            additional_info=raw[6],
            deliverables=deliverables,
            valid_refunds_length=raw[8],
            deliverables_head=raw[9],
            deliverables_count=raw[10],
            acknowledged=raw[11],
        )
