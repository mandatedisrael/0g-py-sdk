from typing import Optional

from ...exceptions import ContractError, NetworkError
from ..contract.contract import FineTuningContract
from ..provider.provider import FineTuningProvider
from ..constants import get_storage_config, get_model_config


class DatasetProcessor:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
    ):
        self.contract = contract
        self.provider = provider

    def upload_dataset_to_tee(
        self, provider_address: str, dataset_path: str
    ) -> dict:
        return self.provider.upload_dataset_to_tee(provider_address, dataset_path)

    def upload_dataset(
        self,
        private_key: str,
        data_path: str,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
    ) -> str:
        """Upload dataset to 0G Storage. Requires 0g-storage-client binary."""
        import subprocess
        import re

        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)

        cmd = [
            "0g-storage-client",
            "upload",
            "--url", config["rpc_url"],
            "--key", private_key,
            "--indexer", config["indexer_url"],
            "--file", data_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                raise ContractError(
                    "uploadDataset",
                    f"Storage client failed: {result.stderr}",
                )

            match = re.search(r"root\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
            if not match:
                raise ContractError(
                    "uploadDataset",
                    "Could not parse root hash from storage client output",
                )
            return match.group(1)

        except FileNotFoundError:
            raise ContractError(
                "uploadDataset",
                "0g-storage-client binary not found. "
                "Install it or use upload_dataset_to_tee() instead.",
            )
        except subprocess.TimeoutExpired:
            raise ContractError("uploadDataset", "Upload timed out after 600s")

    def download_dataset(self, data_path: str, data_root: str) -> None:
        """Download dataset from 0G Storage. Requires 0g-storage-client binary."""
        import subprocess

        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)

        cmd = [
            "0g-storage-client",
            "download",
            "--file", data_path,
            "--indexer", config["indexer_url"],
            "--roots", data_root,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                raise ContractError(
                    "downloadDataset",
                    f"Storage client failed: {result.stderr}",
                )
        except FileNotFoundError:
            raise ContractError(
                "downloadDataset",
                "0g-storage-client binary not found.",
            )
        except subprocess.TimeoutExpired:
            raise ContractError("downloadDataset", "Download timed out after 600s")

    def calculate_token(
        self,
        dataset_path: str,
        pre_trained_model_name: str,
        use_python: bool = True,
        provider_address: Optional[str] = None,
    ) -> int:
        """Calculate token count for a dataset."""
        chain_id = self.contract.get_chain_id()
        model_config = get_model_config(chain_id)

        if pre_trained_model_name in model_config:
            tokenizer = model_config[pre_trained_model_name]["tokenizer"]
            data_type = model_config[pre_trained_model_name]["type"]
        elif provider_address:
            custom = self.provider.get_customized_model(
                provider_address, pre_trained_model_name
            )
            tokenizer = custom.tokenizer
            data_type = custom.data_type
        else:
            raise ContractError(
                "calculateToken",
                f"Model '{pre_trained_model_name}' not found in standard models. "
                "Provide provider_address for custom models.",
            )

        if use_python:
            return self._calculate_token_python(dataset_path, data_type, tokenizer)
        else:
            return self._calculate_token_binary(dataset_path, data_type, tokenizer)

    @staticmethod
    def _calculate_token_python(
        dataset_path: str, data_type: str, tokenizer_path: str
    ) -> int:
        try:
            from transformers import AutoTokenizer
        except ImportError:
            raise ContractError(
                "calculateToken",
                "transformers package required. Install with: pip install transformers",
            )

        import json

        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        total_tokens = 0

        with open(dataset_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data_type == "text":
                        text = ""
                        if "messages" in data:
                            for msg in data["messages"]:
                                text += msg.get("content", "") + " "
                        elif "text" in data:
                            text = data["text"]
                        tokens = tokenizer.encode(text)
                        total_tokens += len(tokens)
                except (json.JSONDecodeError, KeyError):
                    continue

        return total_tokens

    @staticmethod
    def _calculate_token_binary(
        dataset_path: str, data_type: str, tokenizer_path: str
    ) -> int:
        import subprocess

        cmd = ["token_counter", dataset_path, data_type, tokenizer_path]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                raise ContractError(
                    "calculateToken",
                    f"Token counter failed: {result.stderr}",
                )
            parts = result.stdout.strip().split()
            return int(parts[0])
        except FileNotFoundError:
            raise ContractError(
                "calculateToken",
                "token_counter binary not found. Use use_python=True instead.",
            )
        except (ValueError, IndexError):
            raise ContractError(
                "calculateToken", "Could not parse token counter output"
            )
