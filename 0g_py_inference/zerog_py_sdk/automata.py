"""Automata DCAP attestation verification.

This module mirrors the official TypeScript SDK's Automata helper while
providing Python-style dependency injection and typed network failures.
"""

from typing import Optional, Union

from web3 import Web3

from .constants import AUTOMATA_CONTRACT_ADDRESS, AUTOMATA_RPC
from .exceptions import NetworkError


AUTOMATA_ABI = [
    {
        "inputs": [
            {
                "internalType": "bytes",
                "name": "rawQuote",
                "type": "bytes",
            }
        ],
        "name": "verifyAndAttestOnChain",
        "outputs": [
            {
                "internalType": "bool",
                "name": "success",
                "type": "bool",
            },
            {
                "internalType": "bytes",
                "name": "output",
                "type": "bytes",
            },
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


class Automata:
    """Verify raw TEE quotes using Automata's DCAP attestation contract."""

    def __init__(
        self,
        rpc_url: str = AUTOMATA_RPC,
        contract_address: str = AUTOMATA_CONTRACT_ADDRESS,
        web3: Optional[Web3] = None,
        timeout: int = 15,
    ):
        self.rpc_url = rpc_url
        self.web3 = web3 or Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": timeout},
            )
        )
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=AUTOMATA_ABI,
        )

    def verify_quote(
        self,
        raw_quote: Union[str, bytes, bytearray],
    ) -> bool:
        """Return the contract's verification result for a raw TEE quote."""
        quote_bytes = self._normalize_quote(raw_quote)
        try:
            result = (
                self.contract.functions.verifyAndAttestOnChain(
                    quote_bytes
                ).call()
            )
        except Exception as e:
            raise NetworkError(
                f"Automata quote verification failed: {e}",
                endpoint=self.rpc_url,
            ) from e

        if not isinstance(result, (list, tuple)) or not result:
            raise NetworkError(
                "Automata returned a malformed verification result",
                endpoint=self.rpc_url,
            )
        if not isinstance(result[0], bool):
            raise NetworkError(
                "Automata returned a non-boolean verification status",
                endpoint=self.rpc_url,
            )
        return result[0]

    def verifyQuote(
        self,
        raw_quote: Union[str, bytes, bytearray],
    ) -> bool:
        """TypeScript-compatible alias for :meth:`verify_quote`."""
        return self.verify_quote(raw_quote)

    @staticmethod
    def _normalize_quote(
        raw_quote: Union[str, bytes, bytearray],
    ) -> bytes:
        if isinstance(raw_quote, (bytes, bytearray)):
            quote_bytes = bytes(raw_quote)
        elif isinstance(raw_quote, str):
            value = raw_quote[2:] if raw_quote[:2].lower() == "0x" else raw_quote
            try:
                quote_bytes = bytes.fromhex(value)
            except ValueError as e:
                raise ValueError(
                    "Automata quote must be a hex-encoded byte string"
                ) from e
        else:
            raise TypeError("Automata quote must be hex text or bytes")

        if not quote_bytes:
            raise ValueError("Automata quote must not be empty")
        return quote_bytes
