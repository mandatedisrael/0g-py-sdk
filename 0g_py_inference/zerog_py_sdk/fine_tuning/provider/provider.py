import time
import json
from typing import List, Optional

import requests
from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account.signers.local import LocalAccount

from ...exceptions import NetworkError, ContractError
from ..contract.contract import FineTuningContract
from ..contract.types import Task, CustomizedModel, TdxQuoteResponse

REQUEST_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300


class FineTuningProvider:
    def __init__(self, contract: FineTuningContract, account: LocalAccount):
        self.contract = contract
        self.account = account

    def _get_provider_url(self, provider_address: str) -> str:
        service = self.contract.get_service(provider_address)
        url = service.url.rstrip("/")
        if not url:
            raise NetworkError(
                f"Provider {provider_address} has no endpoint URL",
                endpoint=provider_address,
            )
        return url

    def _user_address(self) -> str:
        return self.account.address

    # --- Quote ---

    def get_quote(self, provider_address: str) -> TdxQuoteResponse:
        url = self._get_provider_url(provider_address)
        try:
            resp = requests.get(f"{url}/v1/quote", timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return TdxQuoteResponse(
                raw_report=resp.text,
                signing_address=data.get("report_data", ""),
            )
        except requests.RequestException as e:
            raise NetworkError(str(e), endpoint=f"{url}/v1/quote")

    # --- Task CRUD ---

    def create_task(self, provider_address: str, task: Task) -> str:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()
        try:
            resp = requests.post(
                f"{url}/v1/user/{user_addr}/task",
                json=task.to_dict(),
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            if not resp.ok:
                detail = resp.text
                raise NetworkError(
                    f"{resp.status_code}: {detail}",
                    endpoint=f"{url}/v1/user/{user_addr}/task",
                )
            data = resp.json()
            return data.get("id", "")
        except NetworkError:
            raise
        except requests.RequestException as e:
            raise NetworkError(str(e), endpoint=f"{url}/v1/user/{user_addr}/task")

    def cancel_task(
        self, provider_address: str, task_id: str, signature: str
    ) -> str:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()
        try:
            resp = requests.post(
                f"{url}/v1/user/{user_addr}/task/{task_id}/cancel",
                json={"signature": signature},
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            raise NetworkError(
                str(e),
                endpoint=f"{url}/v1/user/{user_addr}/task/{task_id}/cancel",
            )

    def get_task(self, provider_address: str, task_id: str) -> Task:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()
        try:
            resp = requests.get(
                f"{url}/v1/user/{user_addr}/task/{task_id}",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return Task.from_dict(resp.json())
        except requests.RequestException as e:
            raise NetworkError(
                str(e),
                endpoint=f"{url}/v1/user/{user_addr}/task/{task_id}",
            )

    def list_task(
        self, provider_address: str, latest: bool = False
    ) -> List[Task]:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()
        endpoint = f"{url}/v1/user/{user_addr}/task"
        if latest:
            endpoint += "?latest=true"
        try:
            resp = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [Task.from_dict(t) for t in data]
            return []
        except requests.RequestException as e:
            raise NetworkError(str(e), endpoint=endpoint)

    def get_pending_task_counter(self, provider_address: str) -> int:
        url = self._get_provider_url(provider_address)
        try:
            resp = requests.get(
                f"{url}/v1/task/pending", timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            return int(resp.text.strip())
        except (requests.RequestException, ValueError) as e:
            raise NetworkError(str(e), endpoint=f"{url}/v1/task/pending")

    def get_log(self, provider_address: str, task_id: str) -> str:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()
        try:
            resp = requests.get(
                f"{url}/v1/user/{user_addr}/task/{task_id}/log",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            raise NetworkError(
                str(e),
                endpoint=f"{url}/v1/user/{user_addr}/task/{task_id}/log",
            )

    # --- Model ---

    def get_customized_models(self, provider_address: str) -> List[CustomizedModel]:
        url = self._get_provider_url(provider_address)
        try:
            resp = requests.get(f"{url}/v1/model", timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [CustomizedModel.from_dict(m) for m in data]
            return []
        except requests.RequestException as e:
            raise NetworkError(str(e), endpoint=f"{url}/v1/model")

    def get_customized_model(
        self, provider_address: str, model_name: str
    ) -> CustomizedModel:
        url = self._get_provider_url(provider_address)
        try:
            resp = requests.get(
                f"{url}/v1/model/{model_name}", timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            return CustomizedModel.from_dict(resp.json())
        except requests.RequestException as e:
            raise NetworkError(
                str(e), endpoint=f"{url}/v1/model/{model_name}"
            )

    def download_model_usage(
        self, provider_address: str, model_name: str, output_path: str
    ) -> None:
        url = self._get_provider_url(provider_address)
        try:
            resp = requests.get(
                f"{url}/v1/model/desc/{model_name}",
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException as e:
            raise NetworkError(
                str(e), endpoint=f"{url}/v1/model/desc/{model_name}"
            )

    # --- LoRA download from TEE ---

    def download_lora_from_tee(
        self, provider_address: str, task_id: str, output_path: str
    ) -> None:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()

        timestamp = int(time.time())
        task_id_hex = task_id.replace("-", "")
        message = task_id_hex + str(timestamp)
        message_hash = Web3.keccak(text=message)
        signable = encode_defunct(primitive=message_hash)
        signed = self.account.sign_message(signable)
        signature = "0x" + signed.signature.hex()

        try:
            resp = requests.post(
                f"{url}/v1/user/{user_addr}/task/{task_id}/lora",
                json={"signature": signature, "timestamp": timestamp},
                headers={"Content-Type": "application/json"},
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException as e:
            raise NetworkError(
                str(e),
                endpoint=f"{url}/v1/user/{user_addr}/task/{task_id}/lora",
            )

    # --- Dataset upload to TEE ---

    def upload_dataset_to_tee(
        self, provider_address: str, dataset_path: str
    ) -> dict:
        url = self._get_provider_url(provider_address)
        user_addr = self._user_address()

        timestamp = int(time.time())
        message = user_addr + str(timestamp)
        message_hash = Web3.keccak(text=message)
        signable = encode_defunct(primitive=message_hash)
        signed = self.account.sign_message(signable)
        signature = "0x" + signed.signature.hex()

        try:
            with open(dataset_path, "rb") as f:
                files = {"file": f}
                data = {"signature": signature, "timestamp": str(timestamp)}
                resp = requests.post(
                    f"{url}/v1/user/{user_addr}/dataset",
                    files=files,
                    data=data,
                    timeout=DOWNLOAD_TIMEOUT,
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise NetworkError(
                str(e),
                endpoint=f"{url}/v1/user/{user_addr}/dataset",
            )
