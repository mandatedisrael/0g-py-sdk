"""Tests for inference contract/admin parity helpers."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.exceptions import ContractError
from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.models import ServiceMetadata
from zerog_py_sdk.utils import format_address

PROVIDER = "0x00000000000000000000000000000000000000aa"
USER = "0x00000000000000000000000000000000000000bb"
TEE_SIGNER = "0x00000000000000000000000000000000000000cc"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _service_tuple(*, acknowledged: bool = True, signer: str = TEE_SIGNER):
    return (
        format_address(PROVIDER),
        "chatbot",
        "https://provider.example.com",
        1,
        2,
        123,
        "llama-3",
        "TeeML",
        "extra-info",
        format_address(signer) if signer != ZERO_ADDRESS else ZERO_ADDRESS,
        acknowledged,
    )


def _build_manager() -> InferenceManager:
    manager = object.__new__(InferenceManager)
    manager.contract = MagicMock()
    manager.account = MagicMock()
    manager.account.address = format_address(USER)
    manager.account.sign_transaction.return_value = SimpleNamespace(
        raw_transaction=b"signed"
    )
    manager.web3 = MagicMock()
    manager.web3.eth.chain_id = 16601
    manager.web3.eth.gas_price = 11
    manager.web3.eth.get_transaction_count.return_value = 7
    manager.web3.eth.send_raw_transaction.return_value = b"\xab"
    manager.web3.eth.wait_for_transaction_receipt.return_value = {
        "transactionHash": b"\x01",
        "blockNumber": 22,
        "gasUsed": 33,
        "status": 1,
    }
    manager.ledger_manager = None
    manager._session_manager = MagicMock()
    return manager


def _mock_tx_function(manager: InferenceManager, name: str) -> MagicMock:
    builder = MagicMock()
    builder.build_transaction.return_value = {"tx": name}
    getattr(manager.contract.functions, name).return_value = builder
    return builder


def test_service_metadata_parses_tee_signer_fields():
    manager = _build_manager()
    manager.contract.functions.getAllServices.return_value.call.return_value = (
        [_service_tuple()],
        1,
    )
    manager.contract.functions.getService.return_value.call.return_value = (
        _service_tuple()
    )

    listed = manager.list_service()
    service = manager.get_service(PROVIDER)

    assert listed[0].additional_info == "extra-info"
    assert listed[0].tee_signer_address == format_address(TEE_SIGNER)
    assert listed[0].tee_signer_acknowledged is True
    assert service.tee_signer_address == format_address(TEE_SIGNER)
    manager.contract.functions.getService.assert_called_once_with(
        format_address(PROVIDER)
    )


def test_list_service_can_filter_unacknowledged_signers():
    manager = _build_manager()
    manager.contract.functions.getAllServices.return_value.call.return_value = (
        [_service_tuple(acknowledged=False)],
        1,
    )

    assert manager.list_service(include_unacknowledged=False) == []


def test_check_provider_signer_status_creates_missing_account():
    manager = _build_manager()
    manager.ledger_manager = MagicMock()
    manager.ledger_manager.MIN_TRANSFER_AMOUNT_WEI = 10**18
    manager.get_account = MagicMock(
        side_effect=ContractError("getAccount", "missing")
    )
    manager._get_service_with_signer = MagicMock(
        return_value=ServiceMetadata(
            provider=format_address(PROVIDER),
            service_type="chatbot",
            url="https://provider.example.com",
            input_price=1,
            output_price=2,
            updated_at=0,
            model="llama-3",
            verifiability="TeeML",
            tee_signer_address=format_address(TEE_SIGNER),
            tee_signer_acknowledged=True,
        )
    )

    status = manager.check_provider_signer_status(PROVIDER)

    assert status == {
        "is_acknowledged": True,
        "tee_signer_address": format_address(TEE_SIGNER),
    }
    manager.ledger_manager.transfer_fund.assert_called_once_with(
        format_address(PROVIDER),
        "inference",
        10**18,
    )


def test_check_provider_signer_status_requires_nonzero_signer():
    manager = _build_manager()
    manager._get_service_with_signer = MagicMock(
        return_value=ServiceMetadata(
            provider=format_address(PROVIDER),
            service_type="chatbot",
            url="https://provider.example.com",
            input_price=1,
            output_price=2,
            updated_at=0,
            model="llama-3",
            verifiability="TeeML",
            tee_signer_address=ZERO_ADDRESS,
            tee_signer_acknowledged=True,
        )
    )

    assert manager.check_provider_signer_status(PROVIDER) == {
        "is_acknowledged": False,
        "tee_signer_address": ZERO_ADDRESS,
    }


def test_owner_tee_signer_transactions_accept_gas_override():
    manager = _build_manager()
    ack_builder = _mock_tx_function(manager, "acknowledgeTEESignerByOwner")
    revoke_builder = _mock_tx_function(
        manager, "revokeTEESignerAcknowledgement"
    )

    ack_result = manager.acknowledge_provider_tee_signer(
        PROVIDER, gas_price=123
    )
    revoke_result = manager.revoke_provider_tee_signer_acknowledgement(
        PROVIDER, gas_price=456
    )

    assert ack_result["success"] is True
    assert revoke_result["success"] is True
    manager.contract.functions.acknowledgeTEESignerByOwner.assert_called_once_with(
        format_address(PROVIDER)
    )
    manager.contract.functions.revokeTEESignerAcknowledgement.assert_called_once_with(
        format_address(PROVIDER)
    )
    assert ack_builder.build_transaction.call_args.args[0]["gasPrice"] == 123
    assert revoke_builder.build_transaction.call_args.args[0]["gasPrice"] == 456


def test_token_revocation_helpers_validate_and_use_gas_override():
    manager = _build_manager()
    single_builder = _mock_tx_function(manager, "revokeToken")
    batch_builder = _mock_tx_function(manager, "revokeTokens")
    all_builder = _mock_tx_function(manager, "revokeAllTokens")

    with pytest.raises(ValueError):
        manager.revoke_api_key(PROVIDER, 255)
    with pytest.raises(ValueError):
        manager.revoke_tokens(PROVIDER, [])
    with pytest.raises(ValueError):
        manager.revoke_tokens(PROVIDER, [1, 255])

    manager.revoke_api_key(PROVIDER, 4, gas_price=77)
    manager.revoke_tokens(PROVIDER, [5, 6], gas_price=88)
    manager.revoke_all_tokens(PROVIDER, gas_price=99)

    manager.contract.functions.revokeToken.assert_called_once_with(
        format_address(PROVIDER), 4
    )
    manager.contract.functions.revokeTokens.assert_called_once_with(
        format_address(PROVIDER), [5, 6]
    )
    manager.contract.functions.revokeAllTokens.assert_called_once_with(
        format_address(PROVIDER)
    )
    assert single_builder.build_transaction.call_args.args[0]["gasPrice"] == 77
    assert batch_builder.build_transaction.call_args.args[0]["gasPrice"] == 88
    assert all_builder.build_transaction.call_args.args[0]["gasPrice"] == 99
    manager._session_manager.clear_session_cache.assert_called_once_with(
        format_address(PROVIDER)
    )


def test_account_helpers_parse_current_contract_shape():
    manager = _build_manager()
    refund = (0, 100, 10, False)
    account_data = (
        format_address(USER),
        format_address(PROVIDER),
        3,
        1000,
        250,
        [refund],
        "account-info",
        True,
        1,
        2,
        8,
    )
    manager.contract.functions.getAccount.return_value.call.return_value = (
        account_data
    )
    manager.contract.functions.lockTime.return_value.call.return_value = 86400

    account = manager.get_account(PROVIDER)

    assert manager.get_chain_id() == 16601
    assert manager.get_user_address() == format_address(USER)
    assert manager.lock_time() == 86400
    assert account.locked_balance == 750
    assert account.refunds[0].amount == 100
    assert account.additional_info == "account-info"
    assert account.acknowledged is True
    assert account.generation == 2
    assert account.revoked_bitmap == 8


def test_update_service_preserves_additional_info_and_tee_signer():
    manager = _build_manager()
    current = ServiceMetadata(
        provider=format_address(USER),
        service_type="chatbot",
        url="https://old.example.com",
        input_price=1,
        output_price=2,
        updated_at=0,
        model="old-model",
        verifiability="TeeML",
        additional_info="keep-me",
        tee_signer_address=format_address(TEE_SIGNER),
    )
    manager.get_service = MagicMock(return_value=current)
    builder = _mock_tx_function(manager, "addOrUpdateService")

    manager.update_service(url="https://new.example.com", gas_price=1234)

    manager.contract.functions.addOrUpdateService.assert_called_once_with(
        (
            "chatbot",
            "https://new.example.com",
            "old-model",
            "TeeML",
            1,
            2,
            "keep-me",
            format_address(TEE_SIGNER),
        )
    )
    assert builder.build_transaction.call_args.args[0]["gasPrice"] == 1234
