import json
import time
from typing import Dict, Any, List, Optional

from web3 import Web3

from ...exceptions import ContractError, NetworkError
from ..contract.contract import FineTuningContract
from ..contract.types import (
    FineTuningAccountDetails,
    FineTuningAccountDetail,
    FineTuningService,
    Task,
)
from ..provider.provider import FineTuningProvider
from ..crypto.signing import sign_request, sign_task_id, get_nonce
from ..constants import get_model_config


class ServiceProcessor:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
        ledger_manager,
    ):
        self.contract = contract
        self.provider = provider
        self.ledger = ledger_manager

    def get_lock_time(self) -> int:
        return self.contract.lock_time()

    def list_service(
        self, include_unacknowledged: bool = False
    ) -> List[FineTuningService]:
        return self.contract.list_service(include_unacknowledged)

    def get_account(self, provider_address: str) -> FineTuningAccountDetails:
        return self.contract.get_account(provider_address)

    def get_account_with_detail(
        self, provider_address: str
    ) -> FineTuningAccountDetail:
        account = self.contract.get_account(provider_address)
        lock_time = self.contract.lock_time()
        now = int(time.time())
        valid_length = account.valid_refunds_length

        refunds = []
        for r in account.refunds[:valid_length]:
            if r.amount != 0:
                remain = lock_time - (now - r.created_at)
                refunds.append({"amount": r.amount, "remain_time": max(remain, 0)})

        return FineTuningAccountDetail(account=account, refunds=refunds)

    def acknowledge_provider_signer(
        self, provider_address: str, gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        provider_address = Web3.to_checksum_address(provider_address)

        # Create sub-account via ledger if it doesn't exist
        try:
            self.contract.get_account(provider_address)
        except ContractError:
            self.ledger.transfer_fund(provider_address, "fine-tuning-v1.1", 0)

        # Fetch TEE quote to verify provider is reachable
        quote = self.provider.get_quote(provider_address)
        if not quote.raw_report or not quote.signing_address:
            raise ContractError(
                "acknowledgeProviderSigner", "Invalid quote from provider"
            )

        # Check if already acknowledged
        account = self.contract.get_account(provider_address)
        if account.acknowledged:
            return {"status": "already_acknowledged"}

        return self.contract.acknowledge_tee_signer(
            provider_address, True, gas_price
        )

    def create_task(
        self,
        provider_address: str,
        pre_trained_model_name: str,
        dataset_hash: str,
        training_path: str,
        gas_price: Optional[int] = None,
    ) -> str:
        # Resolve model hash
        chain_id = self.contract.get_chain_id()
        model_config = get_model_config(chain_id)

        if pre_trained_model_name in model_config:
            model_hash = model_config[pre_trained_model_name]["turbo"]
        else:
            custom_model = self.provider.get_customized_model(
                provider_address, pre_trained_model_name
            )
            model_hash = custom_model.hash

        # Read training params from file
        with open(training_path, "r") as f:
            training_params = f.read()
        json.loads(training_params)  # validate JSON

        # Generate nonce and sign
        nonce = get_nonce()
        user_address = self.contract.account.address
        signature = sign_request(
            self.contract.account, user_address, nonce, dataset_hash
        )

        task = Task(
            user_address=user_address,
            pre_trained_model_hash=model_hash,
            dataset_hash=dataset_hash,
            training_params=training_params,
            fee="0",
            nonce=str(nonce),
            signature=signature,
        )

        return self.provider.create_task(provider_address, task)

    def cancel_task(self, provider_address: str, task_id: str) -> str:
        signature = sign_task_id(self.contract.account, task_id)
        return self.provider.cancel_task(provider_address, task_id, signature)

    def list_task(self, provider_address: str) -> List[Task]:
        return self.provider.list_task(provider_address)

    def get_task(
        self, provider_address: str, task_id: Optional[str] = None
    ) -> Task:
        if task_id is None:
            tasks = self.provider.list_task(provider_address, latest=True)
            if not tasks:
                raise ContractError("getTask", "No tasks found")
            return tasks[0]
        return self.provider.get_task(provider_address, task_id)

    def get_log(
        self, provider_address: str, task_id: Optional[str] = None
    ) -> str:
        if task_id is None:
            tasks = self.provider.list_task(provider_address, latest=True)
            if not tasks:
                raise ContractError("getLog", "No tasks found")
            task_id = tasks[0].id
        return self.provider.get_log(provider_address, task_id)
