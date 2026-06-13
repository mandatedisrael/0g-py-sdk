"""Secure resolution and installation of fine-tuning helper binaries."""

import hashlib
import os
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from ..exceptions import ConfigurationError


STORAGE_CLIENT = "0g-storage-client"
TOKEN_COUNTER = "token_counter"
SUPPORTED_BINARIES = (STORAGE_CLIENT, TOKEN_COUNTER)
ENVIRONMENT_VARIABLES = {
    STORAGE_CLIENT: "ZG_STORAGE_CLIENT_PATH",
    TOKEN_COUNTER: "ZG_TOKEN_COUNTER_PATH",
}


@dataclass(frozen=True)
class BinaryConfig:
    """Optional binary path and cache overrides for fine-tuning operations."""

    storage_client_path: Optional[str] = None
    token_counter_path: Optional[str] = None
    cache_dir: Optional[str] = None


class BinaryResolver:
    """Resolve helper executables without modifying the installed package."""

    def __init__(self, config: Optional[BinaryConfig] = None):
        self.config = config or BinaryConfig()
        cache_override = self.config.cache_dir or os.environ.get(
            "ZG_BINARY_CACHE_DIR"
        )
        self.cache_dir = Path(
            cache_override
            or Path.home() / ".cache" / "0g-compute-python" / "binary"
        ).expanduser()
        self.package_dir = Path(__file__).resolve().parent / "binary"

    def resolve(self, name: str) -> str:
        """Return an executable path using deterministic precedence."""
        self._validate_name(name)
        configured = self._configured_paths().get(name)
        if configured:
            return self._validate_executable(
                Path(configured).expanduser(),
                source="configured path",
            )

        environment_name = ENVIRONMENT_VARIABLES[name]
        environment_path = os.environ.get(environment_name)
        if environment_path:
            return self._validate_executable(
                Path(environment_path).expanduser(),
                source=environment_name,
            )

        for source, candidate in (
            ("user cache", self.cache_path(name)),
            ("installed package", self.package_dir / name),
        ):
            if candidate.exists():
                return self._validate_executable(candidate, source=source)

        path_candidate = shutil.which(name)
        if path_candidate:
            return self._validate_executable(
                Path(path_candidate),
                source="PATH",
            )

        system = f"{platform.system().lower()}/{platform.machine().lower()}"
        if name == STORAGE_CLIENT:
            guidance = (
                "Build the official client from "
                "https://github.com/0gfoundation/0g-storage-client and set "
                "ZG_STORAGE_CLIENT_PATH to the resulting executable."
            )
        else:
            guidance = (
                "Set ZG_TOKEN_COUNTER_PATH, or allow the SDK to fetch the "
                "official hash-pinned binary through 0G Storage."
            )
        raise ConfigurationError(
            f"Could not resolve '{name}' on {system}. {guidance}"
        )

    def cache_path(self, name: str) -> Path:
        self._validate_name(name)
        return self.cache_dir / name

    def has_override(self, name: str) -> bool:
        """Return whether a caller explicitly selected this binary."""
        self._validate_name(name)
        return bool(
            self._configured_paths().get(name)
            or os.environ.get(ENVIRONMENT_VARIABLES[name])
        )

    def install_verified(
        self,
        name: str,
        source_path: str,
        expected_sha256: str,
    ) -> str:
        """Atomically install a hash-pinned executable in the user cache."""
        self._validate_name(name)
        source = Path(source_path)
        if not source.is_file():
            raise ConfigurationError(
                f"Downloaded '{name}' is not a regular file: {source}"
            )

        actual_sha256 = self.file_sha256(source)
        if actual_sha256.lower() != expected_sha256.lower():
            raise ConfigurationError(
                f"Downloaded '{name}' failed SHA-256 verification. "
                f"Expected {expected_sha256}, got {actual_sha256}."
            )

        self.cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{name}.",
                suffix=".part",
                dir=str(self.cache_dir),
                delete=False,
            ) as destination:
                temporary_path = destination.name
                with source.open("rb") as source_file:
                    shutil.copyfileobj(source_file, destination)
                destination.flush()
                os.fsync(destination.fileno())

            os.chmod(temporary_path, 0o700)
            target = self.cache_path(name)
            os.replace(temporary_path, target)
            temporary_path = ""
            return self._validate_executable(target, source="user cache")
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _configured_paths(self) -> Dict[str, Optional[str]]:
        return {
            STORAGE_CLIENT: self.config.storage_client_path,
            TOKEN_COUNTER: self.config.token_counter_path,
        }

    @staticmethod
    def _validate_name(name: str) -> None:
        if name not in SUPPORTED_BINARIES:
            raise ConfigurationError(f"Unsupported helper binary: {name}")

    @staticmethod
    def _validate_executable(path: Path, source: str) -> str:
        absolute = path.resolve()
        if not absolute.is_file():
            raise ConfigurationError(
                f"{source} for helper binary is not a regular file: {absolute}"
            )
        if not os.access(str(absolute), os.X_OK):
            raise ConfigurationError(
                f"{source} for helper binary is not executable: {absolute}"
            )
        return str(absolute)
