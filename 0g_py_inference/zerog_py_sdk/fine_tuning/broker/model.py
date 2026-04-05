import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple

from ...exceptions import ContractError
from ..contract.contract import FineTuningContract
from ..contract.types import Deliverable, CustomizedModel
from ..provider.provider import FineTuningProvider
from ..constants import get_model_config, get_storage_config

logger = logging.getLogger(__name__)


class ModelProcessor:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
    ):
        self.contract = contract
        self.provider = provider

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
        download_method: str = "tee",
    ) -> Dict[str, Any]:
        deliverable = self.contract.get_deliverable(provider_address, task_id)

        if download_method == "tee":
            self.provider.download_lora_from_tee(
                provider_address, task_id, data_path
            )
            self._verify_model_hash(data_path, task_id, deliverable.model_root_hash)
        else:
            # 0G Storage download — requires external storage client
            raise ContractError(
                "acknowledgeModel",
                f"Download method '{download_method}' not yet supported. Use 'tee'.",
            )

        return self.contract.acknowledge_deliverable(
            provider_address, task_id, gas_price
        )

    def download_lora_from_tee(
        self, provider_address: str, task_id: str, output_path: str
    ) -> None:
        self.provider.download_lora_from_tee(
            provider_address, task_id, output_path
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

    @staticmethod
    def _verify_model_hash(
        file_path: str, task_id: str, expected_hash: bytes
    ) -> None:
        if not expected_hash:
            return

        try:
            from web3 import Web3

            with open(file_path, "rb") as f:
                content = f.read()
            actual_hash = Web3.keccak(content)

            if actual_hash != expected_hash:
                logger.warning(
                    "Model hash mismatch for task %s. "
                    "Expected: %s, Got: %s",
                    task_id,
                    expected_hash.hex(),
                    actual_hash.hex(),
                )
        except Exception as e:
            logger.warning("Could not verify model hash for task %s: %s", task_id, e)
