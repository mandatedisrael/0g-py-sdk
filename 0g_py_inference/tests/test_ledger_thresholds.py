"""Guards on ledger.add_ledger / deposit_fund / transfer_fund.

Verifies the minimum-balance checks that mirror the LedgerManager contract's
MIN_ACCOUNT_BALANCE (3 0G) and the broker proxy's MinimumLockedBalance (1 0G).
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.exceptions import ContractError
from zerog_py_sdk.ledger import LedgerManager


def _make_manager(ledger_exists: bool = True) -> LedgerManager:
    contract = MagicMock()
    account = MagicMock()
    account.address = "0x0000000000000000000000000000000000000001"
    web3 = MagicMock()

    mgr = LedgerManager(
        contract,
        account,
        web3,
        inference_address="0x0000000000000000000000000000000000000002",
        fine_tuning_address="0x0000000000000000000000000000000000000003",
    )
    # Short-circuit on-chain service-name resolution so amount-guard tests
    # aren't coupled to getServiceInfo behavior.
    mgr._service_names = {"inference": "inference", "fine-tuning": "fine-tuning"}
    if not ledger_exists:
        mgr.get_ledger = MagicMock(
            side_effect=ContractError("getLedger", "not found")
        )
    else:
        mgr.get_ledger = MagicMock()
    return mgr


class TestAddLedger:
    def test_rejects_below_minimum(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="3 0G"):
            mgr.add_ledger("2")

    def test_rejects_zero(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="3 0G"):
            mgr.add_ledger("0")

    def test_accepts_minimum(self):
        # Guard passes; downstream contract call is mocked and irrelevant here.
        mgr = _make_manager()
        mgr.contract.functions.addLedger.side_effect = RuntimeError("stop")
        with pytest.raises(ContractError):
            mgr.add_ledger("3")


class TestDepositFund:
    def test_rejects_zero(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="greater than 0"):
            mgr.deposit_fund("0")

    def test_rejects_sub_minimum_when_no_ledger(self):
        mgr = _make_manager(ledger_exists=False)
        with pytest.raises(ValueError, match="minimum of 3 0G"):
            mgr.deposit_fund("1")

    def test_allows_sub_minimum_when_ledger_exists(self):
        mgr = _make_manager(ledger_exists=True)
        mgr.contract.functions.depositFund.side_effect = RuntimeError("stop")
        with pytest.raises(ContractError):
            mgr.deposit_fund("1")


class TestTransferFund:
    def test_rejects_negative(self):
        mgr = _make_manager()
        with pytest.raises(ValueError, match="negative"):
            mgr.transfer_fund("0xabc", "inference", -1)

    def test_allows_zero_without_warning(self, caplog):
        mgr = _make_manager()
        mgr.contract.functions.transferFund.side_effect = RuntimeError("stop")
        with caplog.at_level(logging.WARNING, logger="zerog_py_sdk.ledger"):
            with pytest.raises(ContractError):
                mgr.transfer_fund("0xabc", "inference", 0)
        assert not any(
            "recommended minimum" in r.message for r in caplog.records
        )

    def test_warns_below_recommended_minimum(self, caplog):
        mgr = _make_manager()
        mgr.contract.functions.transferFund.side_effect = RuntimeError("stop")
        with caplog.at_level(logging.WARNING, logger="zerog_py_sdk.ledger"):
            with pytest.raises(ContractError):
                mgr.transfer_fund("0xabc", "inference", 10 ** 17)  # 0.1 0G
        assert any(
            "recommended minimum" in r.message for r in caplog.records
        )

    def test_no_warning_at_or_above_minimum(self, caplog):
        mgr = _make_manager()
        mgr.contract.functions.transferFund.side_effect = RuntimeError("stop")
        with caplog.at_level(logging.WARNING, logger="zerog_py_sdk.ledger"):
            with pytest.raises(ContractError):
                mgr.transfer_fund("0xabc", "inference", 10 ** 18)  # 1 0G
        assert not any(
            "recommended minimum" in r.message for r in caplog.records
        )


class TestServiceNameResolution:
    def _manager_with_registry(self, inference_name: str, ft_name=None):
        contract = MagicMock()
        account = MagicMock()
        account.address = "0x0000000000000000000000000000000000000001"
        web3 = MagicMock()

        def _get_service_info(addr):
            # ServiceInfo tuple: (serviceAddress, serviceContract, serviceType,
            # version, fullName, description, serviceId, registeredAt)
            if addr.lower().endswith("02"):
                return (addr, addr, "inference", "1.0", inference_name, "", 0, 0)
            if ft_name is None:
                raise RuntimeError("not registered")
            return (addr, addr, "fine-tuning", "1.0", ft_name, "", 0, 0)

        contract.functions.getServiceInfo.side_effect = (
            lambda a: MagicMock(call=lambda: _get_service_info(a))
        )
        return LedgerManager(
            contract,
            account,
            web3,
            inference_address="0x0000000000000000000000000000000000000002",
            fine_tuning_address="0x0000000000000000000000000000000000000003",
        )

    def test_canonical_key_resolves_to_on_chain_name(self):
        mgr = self._manager_with_registry("0G-InferenceServing-v1.2")
        mgr.contract.functions.transferFund.return_value.build_transaction.return_value = {}
        mgr.account.sign_transaction.return_value = MagicMock(raw_transaction=b"")
        mgr.web3.eth.send_raw_transaction.return_value = b""
        mgr.web3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": b"\x00" * 32,
            "blockNumber": 1,
            "gasUsed": 0,
        }

        mgr.transfer_fund("0xabc", "inference", 10 ** 18)

        args, _ = mgr.contract.functions.transferFund.call_args
        assert args[1] == "0G-InferenceServing-v1.2"

    def test_missing_registration_raises(self):
        mgr = self._manager_with_registry("")  # empty fullName
        with pytest.raises(ContractError, match="resolve on-chain service name"):
            mgr.transfer_fund("0xabc", "inference", 10 ** 18)

    def test_unknown_key_passes_through_unchanged(self):
        mgr = self._manager_with_registry("0G-InferenceServing-v1.2")
        mgr.contract.functions.transferFund.side_effect = RuntimeError("stop")
        with pytest.raises(ContractError):
            mgr.transfer_fund("0xabc", "custom-service-name", 10 ** 18)
        args, _ = mgr.contract.functions.transferFund.call_args
        assert args[1] == "custom-service-name"

    @staticmethod
    def _prepare_successful_transaction(mgr):
        mgr.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b""
        )
        mgr.web3.eth.send_raw_transaction.return_value = b""
        mgr.web3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": b"\x00" * 32,
            "blockNumber": 1,
            "gasUsed": 0,
        }

    def test_retrieve_fund_uses_registered_service_name(self):
        mgr = self._manager_with_registry("0G-InferenceServing-v1.2")
        provider = "0x0000000000000000000000000000000000000004"
        detail = MagicMock()
        detail.inference_providers = [(provider, 10, 0)]
        mgr.get_ledger_with_detail = MagicMock(return_value=detail)
        mgr.contract.functions.retrieveFund.return_value.build_transaction.return_value = {}
        self._prepare_successful_transaction(mgr)

        mgr.retrieve_fund("inference")

        mgr.contract.functions.retrieveFund.assert_called_once_with(
            [provider], "0G-InferenceServing-v1.2"
        )


class TestProviderBalanceParity:
    def _make_manager(self):
        contract = MagicMock()
        account = MagicMock()
        account.address = "0x0000000000000000000000000000000000000001"
        web3 = MagicMock()
        web3.to_checksum_address.side_effect = lambda address: address
        inference_contract = MagicMock()
        fine_tuning_contract = MagicMock()
        manager = LedgerManager(
            contract,
            account,
            web3,
            inference_address="0x0000000000000000000000000000000000000002",
            fine_tuning_address="0x0000000000000000000000000000000000000003",
            inference_contract=inference_contract,
            fine_tuning_contract=fine_tuning_contract,
        )
        manager._service_names = {
            "inference": "0G-InferenceServing-v1.2",
            "fine-tuning": "0G-FineTuningServing-v1.2",
        }
        contract.functions.getLedger.return_value.call.return_value = (
            account.address,
            40,
            100,
            "",
        )

        inference_providers = ["0xprovider1", "0xprovider2", "0xprovider3"]
        fine_tuning_providers = ["0xfine1"]

        def _providers(_user, service_name):
            providers = (
                inference_providers
                if service_name == "0G-InferenceServing-v1.2"
                else fine_tuning_providers
            )
            return MagicMock(call=lambda: providers)

        contract.functions.getLedgerProviders.side_effect = _providers
        inference_accounts = {
            "0xprovider1": (account.address, "0xprovider1", 0, 10, 0),
            "0xprovider2": (account.address, "0xprovider2", 0, 0, 0),
            "0xprovider3": (account.address, "0xprovider3", 0, 5, 7),
        }
        inference_contract.functions.getAccount.side_effect = (
            lambda _user, provider: MagicMock(
                call=lambda: inference_accounts[provider]
            )
        )
        fine_tuning_contract.functions.getAccount.return_value.call.return_value = (
            account.address,
            "0xfine1",
            0,
            8,
            2,
        )
        return manager

    def test_get_ledger_with_detail_uses_current_provider_api(self):
        manager = self._make_manager()

        detail = manager.get_ledger_with_detail()

        assert detail.total_balance == 100
        assert detail.locked_balance == 60
        assert detail.available_balance == 40
        assert detail.inference_providers == [
            ("0xprovider1", 10, 0),
            ("0xprovider2", 0, 0),
            ("0xprovider3", 5, 7),
        ]
        assert detail.fine_tuning_providers == [("0xfine1", 8, 2)]

    def test_get_providers_with_balance_filters_zero_accounts(self):
        manager = self._make_manager()

        assert manager.get_providers_with_balance("inference") == [
            ("0xprovider1", 10, 0),
            ("0xprovider3", 5, 7),
        ]

    def test_retrieve_fund_filters_overdrawn_pending_refunds(self):
        manager = self._make_manager()
        manager.contract.functions.retrieveFund.return_value.build_transaction.return_value = {}
        manager.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b""
        )
        manager.web3.eth.send_raw_transaction.return_value = b""
        manager.web3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": b"\x00" * 32,
            "blockNumber": 1,
            "gasUsed": 0,
        }

        manager.retrieve_fund("inference")

        manager.contract.functions.retrieveFund.assert_called_once_with(
            ["0xprovider1", "0xprovider2"],
            "0G-InferenceServing-v1.2",
        )

    def test_retrieve_from_provider_uses_registered_service_name(self):
        mgr = self._make_manager()
        provider = "0x0000000000000000000000000000000000000004"
        mgr.contract.functions.retrieveFund.return_value.build_transaction.return_value = {}
        mgr.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b""
        )
        mgr.web3.eth.send_raw_transaction.return_value = b""
        mgr.web3.eth.wait_for_transaction_receipt.return_value = {
            "status": 1,
            "transactionHash": b"\x00" * 32,
            "blockNumber": 1,
            "gasUsed": 0,
        }

        mgr.retrieve_fund_from_provider(provider, "inference")

        mgr.contract.functions.retrieveFund.assert_called_once_with(
            [provider], "0G-InferenceServing-v1.2"
        )
