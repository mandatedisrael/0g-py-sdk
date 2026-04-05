from typing import Callable, Dict, Any, List, Optional, Tuple

from web3 import Web3
from eth_account.signers.local import LocalAccount

from ...exceptions import ContractError
from ...ledger import LedgerManager
from ..contract.contract import FineTuningContract
from ..contract.types import (
    FineTuningAccountDetails,
    FineTuningAccountDetail,
    FineTuningService,
    Task,
    Deliverable,
    CustomizedModel,
)
from ..provider.provider import FineTuningProvider
from .service import ServiceProcessor
from .model import ModelProcessor
from .dataset import DatasetProcessor
from .verifier import Verifier


class FineTuningBroker:
    def __init__(
        self,
        account: LocalAccount,
        web3: Web3,
        contract_address: str,
        ledger_manager: LedgerManager,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
        step: int = 11,
    ):
        self._account = account
        self._web3 = web3

        self._contract = FineTuningContract(
            account=account,
            web3=web3,
            contract_address=contract_address,
            gas_price=gas_price,
            max_gas_price=max_gas_price,
            step=step,
        )

        self._provider = FineTuningProvider(
            contract=self._contract,
            account=account,
        )

        self._service = ServiceProcessor(
            contract=self._contract,
            provider=self._provider,
            ledger_manager=ledger_manager,
        )

        self._model = ModelProcessor(
            contract=self._contract,
            provider=self._provider,
        )

        self._dataset = DatasetProcessor(
            contract=self._contract,
            provider=self._provider,
        )

        self._verifier = Verifier(
            contract=self._contract,
            provider=self._provider,
        )

    # --- Service discovery ---

    def list_service(
        self, include_unacknowledged: bool = False
    ) -> List[FineTuningService]:
        try:
            return self._service.list_service(include_unacknowledged)
        except Exception as e:
            raise ContractError("listService", str(e))

    def list_model(self) -> Tuple[List[tuple], List[tuple]]:
        try:
            return self._model.list_model()
        except Exception as e:
            raise ContractError("listModel", str(e))

    # --- Account management ---

    def get_account(self, provider_address: str) -> FineTuningAccountDetails:
        try:
            return self._service.get_account(provider_address)
        except Exception as e:
            raise ContractError("getAccount", str(e))

    def get_account_with_detail(
        self, provider_address: str
    ) -> FineTuningAccountDetail:
        try:
            return self._service.get_account_with_detail(provider_address)
        except Exception as e:
            raise ContractError("getAccountWithDetail", str(e))

    def get_locked_time(self) -> int:
        try:
            return self._service.get_lock_time()
        except Exception as e:
            raise ContractError("getLockedTime", str(e))

    def acknowledge_provider_signer(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self._service.acknowledge_provider_signer(
                provider_address, gas_price
            )
        except Exception as e:
            raise ContractError("acknowledgeProviderSigner", str(e))

    def acknowledge_tee_signer_by_owner(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self._contract.acknowledge_tee_signer_by_owner(
                provider_address, gas_price
            )
        except Exception as e:
            raise ContractError("acknowledgeTEESignerByOwner", str(e))

    def revoke_tee_signer_acknowledgement(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self._contract.revoke_tee_signer_acknowledgement(
                provider_address, gas_price
            )
        except Exception as e:
            raise ContractError("revokeTEESignerAcknowledgement", str(e))

    def remove_service(
        self, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return self._contract.remove_service(gas_price)
        except Exception as e:
            raise ContractError("removeService", str(e))

    # --- Task management ---

    def create_task(
        self,
        provider_address: str,
        pre_trained_model_name: str,
        dataset_hash: str,
        training_path: str,
        gas_price: Optional[int] = None,
    ) -> str:
        try:
            return self._service.create_task(
                provider_address,
                pre_trained_model_name,
                dataset_hash,
                training_path,
                gas_price,
            )
        except Exception as e:
            raise ContractError("createTask", str(e))

    def cancel_task(self, provider_address: str, task_id: str) -> str:
        try:
            return self._service.cancel_task(provider_address, task_id)
        except Exception as e:
            raise ContractError("cancelTask", str(e))

    def list_task(self, provider_address: str) -> List[Task]:
        try:
            return self._service.list_task(provider_address)
        except Exception as e:
            raise ContractError("listTask", str(e))

    def get_task(
        self, provider_address: str, task_id: Optional[str] = None
    ) -> Task:
        try:
            return self._service.get_task(provider_address, task_id)
        except Exception as e:
            raise ContractError("getTask", str(e))

    def get_log(
        self, provider_address: str, task_id: Optional[str] = None
    ) -> str:
        try:
            return self._service.get_log(provider_address, task_id)
        except Exception as e:
            raise ContractError("getLog", str(e))

    # --- Dataset management ---

    def upload_dataset_to_tee(
        self, provider_address: str, dataset_path: str
    ) -> dict:
        try:
            return self._dataset.upload_dataset_to_tee(
                provider_address, dataset_path
            )
        except Exception as e:
            raise ContractError("uploadDatasetToTEE", str(e))

    def upload_dataset(
        self,
        data_path: str,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
    ) -> str:
        try:
            private_key = self._account.key.hex()
            return self._dataset.upload_dataset(
                private_key, data_path, gas_price, max_gas_price
            )
        except Exception as e:
            raise ContractError("uploadDataset", str(e))

    def download_dataset(self, data_path: str, data_root: str) -> None:
        try:
            self._dataset.download_dataset(data_path, data_root)
        except Exception as e:
            raise ContractError("downloadDataset", str(e))

    def calculate_token(
        self,
        dataset_path: str,
        pre_trained_model_name: str,
        use_python: bool = True,
        provider_address: Optional[str] = None,
    ) -> int:
        try:
            return self._dataset.calculate_token(
                dataset_path, pre_trained_model_name, use_python, provider_address
            )
        except Exception as e:
            raise ContractError("calculateToken", str(e))

    # --- Model management ---

    def acknowledge_model(
        self,
        provider_address: str,
        task_id: str,
        data_path: str,
        gas_price: Optional[int] = None,
        download_method: str = "tee",
    ) -> Dict[str, Any]:
        try:
            return self._model.acknowledge_model(
                provider_address, task_id, data_path, gas_price, download_method
            )
        except Exception as e:
            raise ContractError("acknowledgeModel", str(e))

    def download_lora_from_tee(
        self, provider_address: str, task_id: str, output_path: str
    ) -> None:
        try:
            self._model.download_lora_from_tee(
                provider_address, task_id, output_path
            )
        except Exception as e:
            raise ContractError("downloadLoRAFromTEE", str(e))

    def model_usage(
        self, provider_address: str, model_name: str, output_path: str
    ) -> None:
        try:
            self._model.model_usage(provider_address, model_name, output_path)
        except Exception as e:
            raise ContractError("modelUsage", str(e))

    def decrypt_model(
        self,
        provider_address: str,
        task_id: str,
        encrypted_model_path: str,
        decrypted_model_path: str,
    ) -> None:
        try:
            self._model.decrypt_model(
                provider_address,
                task_id,
                encrypted_model_path,
                decrypted_model_path,
            )
        except Exception as e:
            raise ContractError("decryptModel", str(e))

    # --- Verification ---

    def verify_service(
        self,
        provider_address: str,
        output_dir: str = ".",
        on_log: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._verifier.verify_service(
                provider_address, output_dir, on_log
            )
        except Exception as e:
            raise ContractError("verifyService", str(e))
