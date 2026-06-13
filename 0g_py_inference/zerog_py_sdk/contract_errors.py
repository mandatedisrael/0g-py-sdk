"""ABI-aware decoding for Solidity contract reverts."""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from eth_abi import decode
from web3 import Web3

from .contracts.abis import LEDGER_CONTRACT_ABI, SERVING_CONTRACT_ABI
from .exceptions import ContractError
from .fine_tuning.contract.abi import FINE_TUNING_SERVING_ABI


HEX_DATA_PATTERN = re.compile(r"0x[0-9a-fA-F]{8,}")
LABELED_HEX_PATTERN = re.compile(
    r"(?:data|result|output|revert(?:ed)?(?:\s+with)?)"
    r"[^0-9a-fA-F]*(0x[0-9a-fA-F]{8,})",
    re.IGNORECASE,
)
PANIC_REASONS = {
    0x01: "assertion failed",
    0x11: "arithmetic overflow or underflow",
    0x12: "division or modulo by zero",
    0x21: "invalid enum conversion",
    0x22: "invalid storage byte array encoding",
    0x31: "pop on an empty array",
    0x32: "array index out of bounds",
    0x41: "memory allocation overflow",
    0x51: "call to an uninitialized function",
}


@dataclass(frozen=True)
class ErrorSpec:
    name: str
    signature: str
    input_types: Tuple[str, ...]
    input_names: Tuple[str, ...]


@dataclass(frozen=True)
class DecodedContractError:
    name: str
    signature: str
    args: Tuple[Any, ...]
    named_args: Dict[str, Any]
    revert_data: str

    def format_reason(self) -> str:
        if self.name == "Error" and self.args:
            return str(self.args[0])
        if self.name == "Panic" and self.args:
            code = int(self.args[0])
            detail = PANIC_REASONS.get(code, "unknown panic")
            return f"Solidity panic 0x{code:x}: {detail}"

        values = []
        for index, value in enumerate(self.args):
            name = (
                self.input_names[index]
                if index < len(self.input_names)
                and self.input_names[index]
                else f"arg{index}"
            )
            values.append(f"{name}={_format_value(value)}")
        suffix = f"({', '.join(values)})" if values else ""
        return f"Contract reverted with {self.name}{suffix}"

    @property
    def input_names(self) -> Tuple[str, ...]:
        return tuple(self.named_args.keys())


def decode_contract_error(
    value: Any,
    abis: Optional[Sequence[Sequence[Dict[str, Any]]]] = None,
) -> Optional[DecodedContractError]:
    """Decode revert data found in a value or nested RPC exception."""
    revert_data = extract_revert_data(value)
    if revert_data is None:
        return None

    raw = bytes.fromhex(revert_data[2:])
    if len(raw) < 4:
        return None
    registry = (
        _default_registry()
        if abis is None
        else _build_registry(abis)
    )
    spec = registry.get(raw[:4])
    if spec is None:
        return None

    try:
        args = (
            tuple(decode(spec.input_types, raw[4:]))
            if spec.input_types
            else ()
        )
    except Exception:
        return None
    named_args = {
        (name or f"arg{index}"): args[index]
        for index, name in enumerate(spec.input_names)
    }
    return DecodedContractError(
        name=spec.name,
        signature=spec.signature,
        args=args,
        named_args=named_args,
        revert_data=revert_data,
    )


def contract_error_from_exception(
    operation: str,
    error: BaseException,
) -> ContractError:
    """Create a rich ``ContractError`` while preserving fallback behavior."""
    if isinstance(error, ContractError) and error.error_name:
        return ContractError(
            operation,
            error.reason,
            error_name=error.error_name,
            error_args=error.error_args,
            revert_data=error.revert_data,
        )

    decoded = decode_contract_error(error)
    if decoded is not None:
        return ContractError(
            operation,
            decoded.format_reason(),
            error_name=decoded.name,
            error_args=decoded.args,
            revert_data=decoded.revert_data,
        )

    reason = error.reason if isinstance(error, ContractError) else str(error)
    return ContractError(operation, reason)


def extract_revert_data(value: Any) -> Optional[str]:
    """Find hex revert bytes in common Web3 and JSON-RPC error shapes."""
    seen = set()

    def walk(item: Any) -> Optional[str]:
        if item is None:
            return None
        item_id = id(item)
        if item_id in seen:
            return None
        seen.add(item_id)

        if isinstance(item, (bytes, bytearray)):
            return _normalize_hex(bytes(item).hex())
        if isinstance(item, str):
            labeled = LABELED_HEX_PATTERN.search(item)
            if labeled:
                return _normalize_hex(labeled.group(1))
            full = _normalize_hex(item)
            if full:
                return full
            candidates = HEX_DATA_PATTERN.findall(item)
            if candidates:
                return _normalize_hex(candidates[-1])
            return None
        if isinstance(item, dict):
            priority_keys = (
                "data",
                "revertData",
                "return",
                "result",
                "output",
                "originalError",
                "error",
            )
            for key in priority_keys:
                if key in item:
                    found = walk(item[key])
                    if found:
                        return found
            for nested in item.values():
                found = walk(nested)
                if found:
                    return found
            return None
        if isinstance(item, (list, tuple)):
            for nested in item:
                found = walk(nested)
                if found:
                    return found
            return None
        if isinstance(item, BaseException):
            found = walk(item.args)
            if found:
                return found
            found = walk(item.__cause__)
            if found:
                return found
            return walk(item.__context__)
        return None

    return walk(value)


@lru_cache(maxsize=1)
def _default_registry() -> Dict[bytes, ErrorSpec]:
    return _build_registry(
        (
            LEDGER_CONTRACT_ABI,
            SERVING_CONTRACT_ABI,
            FINE_TUNING_SERVING_ABI,
        )
    )


def _build_registry(
    abis: Sequence[Sequence[Dict[str, Any]]],
) -> Dict[bytes, ErrorSpec]:
    specs: List[ErrorSpec] = [
        ErrorSpec("Error", "Error(string)", ("string",), ("reason",)),
        ErrorSpec("Panic", "Panic(uint256)", ("uint256",), ("code",)),
    ]
    for abi in abis:
        for entry in abi:
            if entry.get("type") != "error":
                continue
            inputs = entry.get("inputs", [])
            input_types = tuple(_canonical_type(item) for item in inputs)
            input_names = tuple(item.get("name", "") for item in inputs)
            signature = f"{entry['name']}({','.join(input_types)})"
            specs.append(
                ErrorSpec(
                    entry["name"],
                    signature,
                    input_types,
                    input_names,
                )
            )

    return {
        bytes(Web3.keccak(text=spec.signature)[:4]): spec
        for spec in specs
    }


def _canonical_type(abi_input: Dict[str, Any]) -> str:
    abi_type = abi_input["type"]
    if not abi_type.startswith("tuple"):
        return abi_type
    suffix = abi_type[len("tuple"):]
    components = ",".join(
        _canonical_type(component)
        for component in abi_input.get("components", [])
    )
    return f"({components}){suffix}"


def _normalize_hex(value: str) -> Optional[str]:
    candidate = value.strip()
    if candidate[:2].lower() == "0x":
        candidate = candidate[2:]
    if len(candidate) < 8 or len(candidate) % 2:
        return None
    if not re.fullmatch(r"[0-9a-fA-F]+", candidate):
        return None
    return "0x" + candidate.lower()


def _format_value(value: Any) -> str:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, str):
        return repr(value)
    return str(value)
