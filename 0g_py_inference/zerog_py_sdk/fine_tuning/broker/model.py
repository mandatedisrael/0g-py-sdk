import hashlib
import logging
import os
from typing import Dict, Any, List, Optional, Tuple

from ...exceptions import ContractError
from ..contract.contract import FineTuningContract
from ..contract.types import Deliverable, CustomizedModel
from ..provider.provider import FineTuningProvider
from ..constants import get_model_config, get_storage_config
from ..storage import StorageClient

logger = logging.getLogger(__name__)


class ModelProcessor:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
        storage_client: Optional[StorageClient] = None,
    ):
        self.contract = contract
        self.provider = provider
        self.storage_client = storage_client or StorageClient()

    def list_model(self) -> Tuple[List[tuple], List[tuple]]:
        chain_id = self.contract.get_chain_id()
        model_config = get_model_config(chain_id)

        standard_models = [
            (name, config) for name, config in model_config.items()
        ]

        # Fetch customized models from each provider
        customized_models = []
        try:
            services = self.contract.list_service(include_unacknowledged=True)
            for service in services:
                try:
                    models = self.provider.get_customized_models(
                        service.provider
                    )
                    for m in models:
                        customized_models.append(
                            (
                                m.name,
                                {
                                    "description": m.description,
                                    "provider": service.provider,
                                },
                            )
                        )
                except Exception:
                    pass
        except Exception:
            pass

        return (standard_models, customized_models)

    def acknowledge_model(
        self,
        provider_address: str,
        task_id: str,
        data_path: str,
        gas_price: Optional[int] = None,
        download_method: str = "auto",
        tee_idle_timeout_ms: Optional[int] = None,
        tee_max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        deliverable = self.contract.get_deliverable(provider_address, task_id)
        method = self._normalize_download_method(download_method)

        if method == "tee":
            self.provider.download_lora_from_tee(
                provider_address,
                task_id,
                data_path,
                idle_timeout_ms=tee_idle_timeout_ms,
                max_retries=tee_max_retries,
            )
            self._verify_model_hash(data_path, task_id, deliverable.model_root_hash)
        elif method == "0g-storage":
            self._download_from_0g_storage(
                provider_address, task_id, data_path, deliverable
            )
        else:
            try:
                self._download_from_0g_storage(
                    provider_address, task_id, data_path, deliverable
                )
            except Exception as storage_err:
                logger.warning(
                    "0G Storage download failed for task %s: %s. "
                    "Falling back to TEE download.",
                    task_id,
                    storage_err,
                )
                self.provider.download_lora_from_tee(
                    provider_address,
                    task_id,
                    data_path,
                    idle_timeout_ms=tee_idle_timeout_ms,
                    max_retries=tee_max_retries,
                )
                self._verify_model_hash(
                    data_path, task_id, deliverable.model_root_hash
                )

        return self.contract.acknowledge_deliverable(
            provider_address, task_id, gas_price
        )

    def acknowledge_deliverable(
        self,
        provider_address: str,
        task_id: str,
        gas_price: Optional[int] = None,
    ) -> Dict[str, Any]:
        deliverable = self.contract.get_deliverable(provider_address, task_id)
        if deliverable.acknowledged:
            return {"status": "already_acknowledged"}
        return self.contract.acknowledge_deliverable(
            provider_address, task_id, gas_price
        )

    def download_model_from_0g_storage(
        self, provider_address: str, task_id: str, data_path: str
    ) -> None:
        deliverable = self.contract.get_deliverable(provider_address, task_id)
        self._download_from_0g_storage(
            provider_address, task_id, data_path, deliverable
        )

    def download_lora_from_tee(
        self,
        provider_address: str,
        task_id: str,
        output_path: str,
        idle_timeout_ms: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.provider.download_lora_from_tee(
            provider_address,
            task_id,
            output_path,
            idle_timeout_ms=idle_timeout_ms,
            max_retries=max_retries,
        )

    def decrypt_model(
        self,
        provider_address: str,
        task_id: str,
        encrypted_model_path: str,
        decrypted_model_path: str,
    ) -> None:
        from ..crypto.encryption import ecies_decrypt, aes_gcm_decrypt_to_file

        service = self.contract.get_service(provider_address)
        deliverable = self.contract.get_deliverable(provider_address, task_id)

        if not deliverable.acknowledged:
            raise ContractError(
                "decryptModel", "Deliverable not yet acknowledged"
            )
        if not deliverable.encrypted_secret:
            raise ContractError(
                "decryptModel", "No encrypted secret found on deliverable"
            )

        private_key = self.contract.account.key.hex()
        aes_key = ecies_decrypt(private_key, deliverable.encrypted_secret)
        aes_key_hex = aes_key.hex() if isinstance(aes_key, bytes) else aes_key

        aes_gcm_decrypt_to_file(
            key_hex=aes_key_hex,
            encrypted_path=encrypted_model_path,
            decrypted_path=decrypted_model_path,
            provider_signer=service.tee_signer_address,
        )

    def model_usage(
        self, provider_address: str, model_name: str, output_path: str
    ) -> None:
        self.provider.download_model_usage(
            provider_address, model_name, output_path
        )

    def _download_from_0g_storage(
        self,
        provider_address: str,
        task_id: str,
        data_path: str,
        deliverable: Deliverable,
    ) -> None:
        root_hash = self._root_hash_to_hex(deliverable.model_root_hash)
        if not root_hash or self._is_zero_hash(root_hash):
            raise ContractError(
                "downloadModelFrom0GStorage",
                f"No model root hash found for task {task_id}",
            )

        download_path = self._resolve_download_path(data_path, task_id)
        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)
        self.storage_client.download(
            data_path=download_path,
            data_root=root_hash,
            indexer_url=config["indexer_url"],
            operation="downloadModelFrom0GStorage",
        )

    @staticmethod
    def _normalize_download_method(download_method: str) -> str:
        method = (download_method or "auto").lower()
        if method == "storage":
            return "0g-storage"
        if method in {"auto", "tee", "0g-storage"}:
            return method
        raise ContractError(
            "acknowledgeModel",
            "download_method must be one of 'auto', 'tee', or '0g-storage'",
        )

    @staticmethod
    def _resolve_download_path(data_path: str, task_id: str) -> str:
        if os.path.isdir(data_path):
            return os.path.join(data_path, f"model_{task_id}.bin")
        return data_path

    @staticmethod
    def _root_hash_to_hex(root_hash) -> str:
        if root_hash is None:
            return ""
        if isinstance(root_hash, str):
            return root_hash if root_hash.startswith("0x") else f"0x{root_hash}"
        if isinstance(root_hash, (bytes, bytearray)):
            return "0x" + bytes(root_hash).hex()
        if hasattr(root_hash, "hex"):
            value = root_hash.hex()
            return value if value.startswith("0x") else f"0x{value}"
        return str(root_hash)

    @staticmethod
    def _is_zero_hash(root_hash: str) -> bool:
        return root_hash.lower() == "0x" + "0" * 64

    @classmethod
    def _verify_model_hash(cls, file_path: str, task_id: str, expected_hash) -> None:
        if not expected_hash:
            return

        try:
            from web3 import Web3

            actual_file = cls._resolve_actual_model_file(file_path)
            if actual_file is None:
                logger.warning(
                    "Cannot determine downloaded file for task %s at %s, "
                    "skipping hash verification",
                    task_id,
                    file_path,
                )
                return

            with open(actual_file, "rb") as f:
                content = f.read()
            actual_hash = Web3.keccak(content).hex()
            if not actual_hash.startswith("0x"):
                actual_hash = f"0x{actual_hash}"
            expected_hash_hex = cls._root_hash_to_hex(expected_hash).lower()

            if cls._is_zero_hash(expected_hash_hex):
                logger.info(
                    "No on-chain hash to verify for task %s, computed hash: %s",
                    task_id,
                    actual_hash,
                )
                return

            if actual_hash.lower() != expected_hash_hex:
                logger.warning(
                    "Model hash mismatch for task %s. "
                    "Expected: %s, Got: %s",
                    task_id,
                    expected_hash_hex,
                    actual_hash,
                )
        except Exception as e:
            logger.warning("Could not verify model hash for task %s: %s", task_id, e)

    @staticmethod
    def _resolve_actual_model_file(file_path: str) -> Optional[str]:
        if os.path.isfile(file_path):
            return file_path
        if not os.path.isdir(file_path):
            return None

        files = [
            os.path.join(file_path, f)
            for f in os.listdir(file_path)
            if os.path.isfile(os.path.join(file_path, f))
        ]
        preferred = [
            f
            for f in files
            if os.path.basename(f).startswith("lora_model_")
            or f.endswith(".data")
            or f.endswith(".zip")
            or f.endswith(".bin")
        ]
        if preferred:
            return preferred[0]
        if len(files) == 1:
            return files[0]
        return None
