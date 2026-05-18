"""Tests for auto-funding parity behavior."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.models import ServiceMetadata
from zerog_py_sdk.utils import format_address


PROVIDER = "0x00000000000000000000000000000000000000aa"
USER = "0x00000000000000000000000000000000000000bb"


def _build_manager() -> InferenceManager:
    manager = object.__new__(InferenceManager)
    manager.account = MagicMock(address=USER)
    manager.auth_manager = MagicMock()
    manager.ledger_manager = MagicMock()
    manager._auto_funding_stops = {}
    manager._cached_fees = {}
    manager._session_manager = MagicMock()
    manager._session_manager.get_request_headers.return_value = {
        "Authorization": "Bearer test"
    }
    manager.contract = MagicMock()
    return manager


def test_min_locked_balance_matches_ts_threshold():
    assert InferenceManager._MIN_LOCKED_BALANCE == 10 ** 18


def test_get_request_headers_checks_and_funds_inline():
    manager = _build_manager()
    manager.has_auto_funding = MagicMock(return_value=False)
    manager._check_and_fund = MagicMock()

    headers = manager.get_request_headers(PROVIDER)

    assert headers["Authorization"] == "Bearer test"
    manager._check_and_fund.assert_called_once()
    manager._session_manager.get_request_headers.assert_called_once()


def test_get_request_headers_skips_inline_check_when_background_funding_active():
    manager = _build_manager()
    manager.has_auto_funding = MagicMock(return_value=True)
    manager._check_and_fund = MagicMock()

    manager.get_request_headers(PROVIDER)

    manager._check_and_fund.assert_not_called()


def test_fetch_unsettled_fee_uses_provider_endpoint_and_caches_value():
    manager = _build_manager()
    manager.get_service = MagicMock(
        return_value=ServiceMetadata(
            provider=PROVIDER,
            service_type="chatbot",
            url="https://provider.example.com",
            input_price=1,
            output_price=2,
            updated_at=0,
            model="model-a",
            verifiability="",
        )
    )
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"unsettledFee": "123"}

    with patch("zerog_py_sdk.inference.requests.get", return_value=response) as get:
        fee = manager._fetch_unsettled_fee(PROVIDER)

    assert fee == 123
    assert manager._get_cached_fee(PROVIDER) == 123
    assert get.call_args.args[0].endswith(f"/v1/user/{USER}/unsettledfee")


def test_fetch_unsettled_fee_falls_back_to_cached_fee_on_non_200():
    manager = _build_manager()
    manager._update_cached_fee(PROVIDER, 55)
    manager.get_service = MagicMock(
        return_value=ServiceMetadata(
            provider=PROVIDER,
            service_type="chatbot",
            url="https://provider.example.com",
            input_price=1,
            output_price=2,
            updated_at=0,
            model="model-a",
            verifiability="",
        )
    )
    response = MagicMock(status_code=404)

    with patch("zerog_py_sdk.inference.requests.get", return_value=response):
        fee = manager._fetch_unsettled_fee(PROVIDER)

    assert fee == 55


def test_check_and_fund_uses_minimum_transfer_and_clears_cached_fee():
    manager = _build_manager()
    manager._update_cached_fee(PROVIDER, 77)
    manager._fetch_unsettled_fee = MagicMock(return_value=25)
    manager._get_transfer_deficit = MagicMock(return_value=1)

    manager._check_and_fund(PROVIDER, 2)

    manager.ledger_manager.transfer_fund.assert_called_once_with(
        format_address(PROVIDER), "inference", 10 ** 18
    )
    assert manager._get_cached_fee(PROVIDER) == 0


def test_process_response_updates_cached_fee_for_usage_payload():
    manager = _build_manager()
    service = ServiceMetadata(
        provider=PROVIDER,
        service_type="chatbot",
        url="https://provider.example.com",
        input_price=3,
        output_price=5,
        updated_at=0,
        model="model-a",
        verifiability="",
    )
    extractor = MagicMock()
    extractor.get_svc_info.return_value = service
    extractor.get_input_count.return_value = 4
    extractor.get_output_count.return_value = 6
    manager.get_service = MagicMock(return_value=service)
    manager.get_extractor = MagicMock(return_value=extractor)

    result = manager.process_response(PROVIDER, '{"prompt_tokens": 4, "completion_tokens": 6}')

    assert result is True
    assert manager._get_cached_fee(PROVIDER) == (4 * 3) + (6 * 5)
