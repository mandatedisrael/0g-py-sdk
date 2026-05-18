"""Tests for read-only service detail enrichment."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.read_only import (
    CacheTokenBillingInfo,
    HealthMetrics,
    PricingTier,
    ProviderModelInfo,
    ReadOnlyInferenceBroker,
    ServiceWithDetail,
    TieredPricingInfo,
)


PROVIDER = "0xABC"


def _build_broker() -> ReadOnlyInferenceBroker:
    broker = object.__new__(ReadOnlyInferenceBroker)
    broker.web3 = MagicMock()
    broker.web3.eth.chain_id = 16602
    broker.contract = MagicMock()
    return broker


def test_list_service_populates_tee_fields():
    broker = _build_broker()
    broker.contract.functions.getAllServices.return_value.call.return_value = (
        [
            (
                PROVIDER,
                "chatbot",
                "https://provider.example.com",
                1,
                2,
                3,
                "model-a",
                "TeeML",
                "{}",
                "0xSigner",
                False,
            )
        ],
        1,
    )

    services = broker.list_service()

    assert len(services) == 1
    assert services[0].tee_signer_address == "0xSigner"
    assert services[0].tee_signer_acknowledged is False


def test_list_service_with_detail_merges_health_and_model_info():
    broker = _build_broker()
    broker.list_service = MagicMock(
        return_value=[
            ServiceWithDetail(
                provider=PROVIDER,
                service_type="text-to-image",
                url="https://provider.example.com",
                input_price=1,
                output_price=2,
                updated_at=3,
                model="flux-dev",
                verifiability="TeeML",
            )
        ]
    )
    broker._fetch_health_metrics = MagicMock(
        return_value={
            PROVIDER.lower(): HealthMetrics(
                status="healthy",
                uptime=99.9,
                avg_response_time=123,
                last_check="2026-05-18T00:00:00Z",
            )
        }
    )
    broker._fetch_model_info = MagicMock(
        return_value={
            PROVIDER.lower(): [
                ProviderModelInfo(
                    id="flux-dev",
                    provider=PROVIDER,
                    name="Flux Dev",
                    pricing={
                        "tiered_pricing": [
                            {
                                "max_input_tokens": 4096,
                                "input_multiplier": 1.5,
                                "output_multiplier": 2.0,
                            }
                        ],
                        "cache_token_billing": {"divisor": 8},
                    },
                )
            ]
        }
    )

    services = broker.list_service_with_detail()

    assert services[0].health_metrics is not None
    assert services[0].health_metrics.status == "healthy"
    assert services[0].model_info is not None
    assert services[0].model_info.name == "Flux Dev"
    assert services[0].tiered_pricing == TieredPricingInfo(
        tiers=[
            PricingTier(
                max_input_tokens=4096,
                input_multiplier=1.5,
                output_multiplier=2.0,
            )
        ]
    )
    assert services[0].cache_token_billing == CacheTokenBillingInfo(divisor=8)


def test_list_service_with_detail_prefers_additional_info_pricing():
    broker = _build_broker()
    broker.list_service = MagicMock(
        return_value=[
            ServiceWithDetail(
                provider=PROVIDER,
                service_type="chatbot",
                url="https://provider.example.com",
                input_price=1,
                output_price=2,
                updated_at=3,
                model="model-a",
                verifiability="TeeML",
                additional_info=(
                    '{"tieredPricing":{"tiers":[{"maxInputTokens":2048,'
                    '"inputMultiplier":2,"outputMultiplier":3}]},'
                    '"cacheTokenBilling":{"divisor":4}}'
                ),
            )
        ]
    )
    broker._fetch_health_metrics = MagicMock(return_value={})
    broker._fetch_model_info = MagicMock(
        return_value={
            PROVIDER.lower(): [
                ProviderModelInfo(
                    id="model-a",
                    provider=PROVIDER,
                    pricing={
                        "tiered_pricing": [
                            {
                                "max_input_tokens": 4096,
                                "input_multiplier": 9,
                                "output_multiplier": 9,
                            }
                        ],
                        "cache_token_billing": {"divisor": 99},
                    },
                )
            ]
        }
    )

    service = broker.list_service_with_detail()[0]

    assert service.tiered_pricing == TieredPricingInfo(
        tiers=[
            PricingTier(
                max_input_tokens=2048,
                input_multiplier=2.0,
                output_multiplier=3.0,
            )
        ]
    )
    assert service.cache_token_billing == CacheTokenBillingInfo(divisor=4)


def test_fetch_model_info_parses_status_api_payload():
    broker = _build_broker()

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "data": [
            {"id": "model-a", "provider": PROVIDER, "context_length": 8192},
            {"id": "model-b"},
        ]
    }

    with patch("zerog_py_sdk.read_only.requests.get", return_value=response) as get:
        model_map = broker._fetch_model_info()

    assert get.call_args.args[0].endswith("/models")
    assert PROVIDER.lower() in model_map
    assert model_map[PROVIDER.lower()][0].context_length == 8192
