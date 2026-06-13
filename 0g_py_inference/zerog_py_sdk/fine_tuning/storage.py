"""Subprocess wrapper for the official 0G Storage client."""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..exceptions import ContractError
from .binaries import BinaryResolver, STORAGE_CLIENT


class StorageClient:
    """Run 0G Storage operations with bounded, atomic subprocess handling."""

    def __init__(
        self,
        binary_resolver: Optional[BinaryResolver] = None,
        timeout: int = 600,
    ):
        self.binary_resolver = binary_resolver or BinaryResolver()
        self.timeout = timeout

    def upload(
        self,
        private_key: str,
        data_path: str,
        rpc_url: str,
        indexer_url: str,
        gas_price: Optional[int] = None,
        max_gas_price: Optional[int] = None,
    ) -> str:
        source = Path(data_path)
        if not source.is_file():
            raise ContractError(
                "uploadDataset",
                f"Dataset is not a regular file: {source}",
            )

        command = [
            self._resolve("uploadDataset"),
            "upload",
            "--url",
            rpc_url,
            "--key",
            private_key,
            "--indexer",
            indexer_url,
            "--file",
            str(source),
            "--skip-tx=false",
            "--log-level=debug",
        ]
        if gas_price is not None:
            command.extend(["--gas-price", str(gas_price)])
        if max_gas_price is not None:
            command.extend(["--max-gas-price", str(max_gas_price)])

        result = self._run(command, "uploadDataset")
        output = f"{result.stdout}\n{result.stderr}"
        match = re.search(r"root\s*=\s*(0x[0-9a-fA-F]+)", output)
        if not match:
            raise ContractError(
                "uploadDataset",
                "Upload completed but the storage client returned no root hash",
            )
        return match.group(1)

    def download(
        self,
        data_path: str,
        data_root: str,
        indexer_url: str,
        operation: str = "downloadDataset",
    ) -> None:
        destination = Path(data_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = ""
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".part",
                dir=str(destination.parent),
            )
            os.close(descriptor)
            os.unlink(temporary_path)

            command = [
                self._resolve(operation),
                "download",
                "--file",
                temporary_path,
                "--indexer",
                indexer_url,
                "--roots",
                data_root,
            ]
            self._run(command, operation)

            temporary = Path(temporary_path)
            if not temporary.is_file():
                raise ContractError(
                    operation,
                    "Storage client succeeded without creating the output file",
                )
            with temporary.open("rb") as downloaded:
                os.fsync(downloaded.fileno())
            os.replace(temporary_path, destination)
            temporary_path = ""
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def _resolve(self, operation: str) -> str:
        try:
            return self.binary_resolver.resolve(STORAGE_CLIENT)
        except Exception as e:
            raise ContractError(operation, str(e)) from e

    def _run(
        self,
        command,
        operation: str,
    ) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as e:
            raise ContractError(
                operation,
                "Resolved 0g-storage-client executable was not found",
            ) from e
        except subprocess.TimeoutExpired as e:
            raise ContractError(
                operation,
                f"Storage client timed out after {self.timeout}s",
            ) from e
        except OSError as e:
            raise ContractError(
                operation,
                f"Could not execute 0g-storage-client: {e}",
            ) from e

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if len(detail) > 2000:
                detail = detail[-2000:]
            raise ContractError(
                operation,
                f"Storage client exited with code {result.returncode}"
                + (f": {detail}" if detail else ""),
            )
        return result
