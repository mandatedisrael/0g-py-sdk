from unittest.mock import MagicMock

import pytest
from eth_abi import encode
from web3 import Web3
from web3.exceptions import ContractLogicError

from zerog_py_sdk.contract_errors import (
    contract_error_from_exception,
    decode_contract_error,
    extract_revert_data,
)
from zerog_py_sdk.exceptions import ContractError
from zerog_py_sdk.fine_tuning.contract.contract import FineTuningContract
from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.ledger import LedgerManager


def _payload(signature, types=(), values=()):
    selector = bytes(Web3.keccak(text=signature)[:4])
    arguments = encode(types, values) if types else b""
    return "0x" + (selector + arguments).hex()


def test_decodes_nested_ledger_custom_error():
    data = _payload(
        "TooManyProviders(uint256,uint256)",
        ("uint256", "uint256"),
        (9, 5),
    )
    error = ValueError(
        {
            "code": 3,
            "error": {
                "data": {
                    "transaction": {
                        "return": data,
                    }
                }
            },
        }
    )

    decoded = decode_contract_error(error)

    assert decoded.name == "TooManyProviders"
    assert decoded.args == (9, 5)
    assert decoded.named_args == {"requested": 9, "maximum": 5}
    assert decoded.revert_data == data


def test_decodes_fine_tuning_error_from_web3_data_attribute():
    data = _payload(
        "DeliverableNotExists(string)",
        ("string",),
        ("task-7",),
    )
    error = ContractLogicError("execution reverted", data=data)

    decoded = decode_contract_error(error)

    assert decoded.name == "DeliverableNotExists"
    assert decoded.args == ("task-7",)
    assert decoded.named_args == {"id": "task-7"}


def test_decodes_standard_solidity_error_string():
    data = _payload("Error(string)", ("string",), ("provider rejected",))

    error = contract_error_from_exception(
        "sendRequest",
        ValueError({"data": data}),
    )

    assert error.reason == "provider rejected"
    assert error.error_name == "Error"
    assert error.error_args == ("provider rejected",)
    assert error.revert_data == data


def test_decodes_standard_solidity_panic():
    data = _payload("Panic(uint256)", ("uint256",), (0x11,))

    error = contract_error_from_exception("settle", ValueError(data))

    assert error.error_name == "Panic"
    assert error.error_args == (0x11,)
    assert error.reason == "Solidity panic 0x11: arithmetic overflow or underflow"


def test_extracts_revert_bytes_directly():
    data = _payload("AdditionalInfoTooLong()")

    assert extract_revert_data(bytes.fromhex(data[2:])) == data


def test_unknown_selector_falls_back_to_original_message():
    error = ValueError({"data": "0x12345678"})

    wrapped = contract_error_from_exception("unknown", error)

    assert wrapped.error_name is None
    assert wrapped.error_args == ()
    assert wrapped.revert_data is None
    assert wrapped.reason == str(error)


def test_malformed_known_payload_is_not_partially_decoded():
    selector_only = _payload("Error(string)")

    assert decode_contract_error(selector_only) is None


def test_rewrapping_contract_error_avoids_nested_messages():
    original = ContractError("inner", "plain reason")

    wrapped = contract_error_from_exception("outer", original)

    assert wrapped.operation == "outer"
    assert wrapped.reason == "plain reason"
    assert "Contract operation 'inner'" not in str(wrapped)


def test_rewrapping_rich_contract_error_preserves_metadata():
    original = ContractError(
        "inner",
        "decoded",
        error_name="ServiceNotExist",
        error_args=("0x" + "11" * 20,),
        revert_data="0x12345678",
    )

    wrapped = contract_error_from_exception("outer", original)

    assert wrapped.error_name == original.error_name
    assert wrapped.error_args == original.error_args
    assert wrapped.revert_data == original.revert_data


def test_fine_tuning_transaction_preserves_decoded_cause():
    data = _payload(
        "DeliverableNotExists(string)",
        ("string",),
        ("task-7",),
    )
    original = ContractLogicError("execution reverted", data=data)
    contract = FineTuningContract.__new__(FineTuningContract)
    contract._gas_price = 1
    contract._max_gas_price = None
    contract._step = 11
    contract.account = MagicMock(address="0x" + "11" * 20)
    contract.web3 = MagicMock()
    tx_func = MagicMock()
    tx_func.build_transaction.side_effect = original

    with pytest.raises(ContractError) as exc_info:
        contract._send_tx("acknowledgeDeliverable", tx_func)

    assert exc_info.value.error_name == "DeliverableNotExists"
    assert exc_info.value.error_args == ("task-7",)
    assert exc_info.value.__cause__ is original


def test_ledger_read_call_preserves_decoded_cause():
    data = _payload(
        "LedgerNotExists(address)",
        ("address",),
        ("0x" + "11" * 20,),
    )
    original = ContractLogicError("execution reverted", data=data)
    manager = LedgerManager.__new__(LedgerManager)
    manager.account = MagicMock(address="0x" + "11" * 20)
    manager.contract = MagicMock()
    manager.contract.functions.getLedger.return_value.call.side_effect = original

    with pytest.raises(ContractError) as exc_info:
        manager.get_ledger()

    assert exc_info.value.error_name == "LedgerNotExists"
    assert exc_info.value.__cause__ is original


def test_inference_read_call_preserves_decoded_cause():
    data = _payload(
        "InvalidTEESignature(string)",
        ("string",),
        ("bad signer",),
    )
    original = ContractLogicError("execution reverted", data=data)
    manager = InferenceManager.__new__(InferenceManager)
    manager.contract = MagicMock()
    manager.contract.functions.lockTime.return_value.call.side_effect = original

    with pytest.raises(ContractError) as exc_info:
        manager.lock_time()

    assert exc_info.value.error_name == "InvalidTEESignature"
    assert exc_info.value.error_args == ("bad signer",)
    assert exc_info.value.__cause__ is original
