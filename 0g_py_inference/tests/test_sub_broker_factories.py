from unittest.mock import MagicMock

from zerog_py_sdk import (
    FineTuningBroker,
    InferenceBroker,
    LedgerBroker,
    create_fine_tuning_broker,
    create_inference_broker,
    create_ledger_broker,
    create_read_only_broker,
    create_read_only_inference_broker,
)


LEDGER_ADDRESS = "0x0000000000000000000000000000000000000001"
INFERENCE_ADDRESS = "0x0000000000000000000000000000000000000002"
FINE_TUNING_ADDRESS = "0x0000000000000000000000000000000000000003"


def test_read_only_inference_factory_alias():
    assert create_read_only_inference_broker is create_read_only_broker


def test_standalone_broker_factories_return_public_broker_types():
    account = MagicMock()
    account.address = "0x0000000000000000000000000000000000000004"
    web3 = MagicMock()
    web3.eth.contract.side_effect = [
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    ]

    ledger = create_ledger_broker(
        account,
        web3,
        LEDGER_ADDRESS,
        INFERENCE_ADDRESS,
        FINE_TUNING_ADDRESS,
    )
    inference = create_inference_broker(
        account,
        web3,
        INFERENCE_ADDRESS,
        ledger,
    )
    fine_tuning = create_fine_tuning_broker(
        account,
        web3,
        FINE_TUNING_ADDRESS,
        ledger,
        gas_price=10,
        max_gas_price=20,
        step=12,
    )

    assert isinstance(ledger, LedgerBroker)
    assert isinstance(inference, InferenceBroker)
    assert isinstance(fine_tuning, FineTuningBroker)
