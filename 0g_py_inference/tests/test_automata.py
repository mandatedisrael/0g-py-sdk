from unittest.mock import MagicMock

import pytest

from zerog_py_sdk.automata import AUTOMATA_ABI, Automata
from zerog_py_sdk.constants import AUTOMATA_CONTRACT_ADDRESS
from zerog_py_sdk.exceptions import NetworkError
from zerog_py_sdk.inference import InferenceManager


def _client(result=(True, b"verified")):
    web3 = MagicMock()
    contract = web3.eth.contract.return_value
    contract.functions.verifyAndAttestOnChain.return_value.call.return_value = (
        result
    )
    return Automata(web3=web3), web3, contract


def test_uses_official_contract_method_and_decodes_success():
    client, web3, contract = _client()

    assert client.verify_quote("0x1234") is True
    web3.eth.contract.assert_called_once_with(
        address=AUTOMATA_CONTRACT_ADDRESS,
        abi=AUTOMATA_ABI,
    )
    contract.functions.verifyAndAttestOnChain.assert_called_once_with(
        b"\x12\x34"
    )


def test_typescript_alias_and_bytes_input_return_rejection():
    client, _, contract = _client(result=(False, b"rejected"))

    assert client.verifyQuote(b"\xab\xcd") is False
    contract.functions.verifyAndAttestOnChain.assert_called_once_with(
        b"\xab\xcd"
    )


@pytest.mark.parametrize("quote", ["", "0x", "not-hex", "0x123"])
def test_rejects_invalid_quote_before_contract_call(quote):
    client, _, contract = _client()

    with pytest.raises(ValueError, match="quote"):
        client.verify_quote(quote)

    contract.functions.verifyAndAttestOnChain.assert_not_called()


def test_wraps_contract_failure_as_network_error_with_cause():
    client, _, contract = _client()
    contract.functions.verifyAndAttestOnChain.return_value.call.side_effect = (
        RuntimeError("rpc unavailable")
    )

    with pytest.raises(NetworkError, match="Automata") as exc_info:
        client.verify_quote("0x1234")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.parametrize("result", [None, (), ("true", b"")])
def test_rejects_malformed_contract_results(result):
    client, _, _ = _client(result=result)

    with pytest.raises(NetworkError, match="malformed|non-boolean"):
        client.verify_quote("0x1234")


def test_inference_manager_delegates_to_automata_client():
    manager = InferenceManager.__new__(InferenceManager)
    manager._automata = MagicMock()
    manager._automata.verify_quote.return_value = True

    assert manager._verify_quote_with_automata("0x1234") is True
    manager._automata.verify_quote.assert_called_once_with("0x1234")
