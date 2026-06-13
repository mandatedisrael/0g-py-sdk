import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ...exceptions import ConfigurationError, ContractError
from ..contract.contract import FineTuningContract
from ..provider.provider import FineTuningProvider
from ..constants import (
    TOKEN_COUNTER_FILE_HASH,
    TOKEN_COUNTER_MERKLE_ROOT,
    get_storage_config,
    get_model_config,
)
from ..binaries import TOKEN_COUNTER
from ..storage import StorageClient


class DatasetProcessor:
    def __init__(
        self,
        contract: FineTuningContract,
        provider: FineTuningProvider,
        storage_client: Optional[StorageClient] = None,
    ):
        self.contract = contract
        self.provider = provider
        self.storage_client = storage_client or StorageClient()

    def upload_dataset_to_tee(
        self,
        provider_address: str,
        dataset_path: str,
        *,
        max_file_size_mb: float = 100,
        timeout_ms: Optional[int] = None,
    ) -> dict:
        return self.provider.upload_dataset_to_tee(
            provider_address,
            dataset_path,
            max_file_size_mb=max_file_size_mb,
            timeout_ms=timeout_ms,
        )

    def upload_dataset(
        self,
        private_key: str,
        data_path: str,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
    ) -> str:
        """Upload a dataset to 0G Storage."""
        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)
        return self.storage_client.upload(
            private_key=private_key,
            data_path=data_path,
            rpc_url=config["rpc_url"],
            indexer_url=config["indexer_url"],
            gas_price=gas_price,
            max_gas_price=max_gas_price,
        )

    def download_dataset(self, data_path: str, data_root: str) -> None:
        """Download a dataset from 0G Storage."""
        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)
        self.storage_client.download(
            data_path=data_path,
            data_root=data_root,
            indexer_url=config["indexer_url"],
            operation="downloadDataset",
        )

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

    def _calculate_token_binary(
        self,
        dataset_path: str,
        data_type: str,
        tokenizer_path: str,
    ) -> int:
        binary_path = self._resolve_token_counter()
        cmd = [binary_path, dataset_path, data_type, tokenizer_path]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                raise ContractError(
                    "calculateToken",
                    f"Token counter failed: {result.stderr}",
                )
            parts = result.stdout.strip().split()
            return int(parts[0])
        except FileNotFoundError as e:
            raise ContractError(
                "calculateToken",
                "Resolved token_counter executable was not found",
            ) from e
        except subprocess.TimeoutExpired as e:
            raise ContractError(
                "calculateToken",
                "Token counter timed out after 300s",
            ) from e
        except OSError as e:
            raise ContractError(
                "calculateToken",
                f"Could not execute token_counter: {e}",
            ) from e
        except (ValueError, IndexError) as e:
            raise ContractError(
                "calculateToken", "Could not parse token counter output"
            ) from e

    def _resolve_token_counter(self) -> str:
        resolver = self.storage_client.binary_resolver
        try:
            binary_path = resolver.resolve(TOKEN_COUNTER)
        except ConfigurationError as e:
            if resolver.has_override(TOKEN_COUNTER):
                raise ContractError("calculateToken", str(e)) from e
            return self._download_token_counter()

        actual_hash = resolver.file_sha256(Path(binary_path))
        if actual_hash.lower() == TOKEN_COUNTER_FILE_HASH.lower():
            return binary_path

        cached_path = resolver.cache_path(TOKEN_COUNTER).resolve()
        if Path(binary_path).resolve() == cached_path:
            try:
                os.unlink(binary_path)
            except FileNotFoundError:
                pass
            return self._download_token_counter()

        raise ContractError(
            "calculateToken",
            "Configured token_counter failed SHA-256 verification. "
            f"Expected {TOKEN_COUNTER_FILE_HASH}, got {actual_hash}.",
        )

    def _download_token_counter(self) -> str:
        chain_id = self.contract.get_chain_id()
        config = get_storage_config(chain_id)
        resolver = self.storage_client.binary_resolver
        with tempfile.TemporaryDirectory(
            prefix="0g-token-counter-"
        ) as temporary_dir:
            downloaded_path = os.path.join(temporary_dir, TOKEN_COUNTER)
            self.storage_client.download(
                data_path=downloaded_path,
                data_root=TOKEN_COUNTER_MERKLE_ROOT,
                indexer_url=config["indexer_url"],
                operation="downloadTokenCounter",
            )
            return resolver.install_verified(
                TOKEN_COUNTER,
                downloaded_path,
                TOKEN_COUNTER_FILE_HASH,
            )
