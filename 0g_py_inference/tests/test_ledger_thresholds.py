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

    mgr = LedgerManager(contract, account, web3)
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
