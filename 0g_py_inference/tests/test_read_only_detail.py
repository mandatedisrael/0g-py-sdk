"""Tests for read-only service detail enrichment."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.read_only import (
    CacheTokenBillingInfo,
    HealthMetrics,
    MultiModelInfo,
    PricingTier,
    ProviderModelInfo,
    ProviderModels,
    ReadOnlyInferenceBroker,
    ServiceHealthMetric,
    ServiceWithDetail,
    TieredPricingInfo,
    parse_multi_model_info,
)


PROVIDER = "0xABC"
VALID_PROVIDER = "0x00000000000000000000000000000000000000aa"


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
    broker._fetch_service_health_metrics = MagicMock(
        return_value=[
            ServiceHealthMetric(
                service_type="text-to-image",
                model="flux-dev",
                provider=PROVIDER,
                status="healthy",
                checks={"uptime": 99.9},
                performance={"response_time": {"avg": 123}},
                last_check="2026-05-18T00:00:00Z",
            )
        ]
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
    broker._fetch_service_health_metrics = MagicMock(return_value=[])
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


def test_parse_multi_model_info_matches_typescript_behavior():
    assert parse_multi_model_info(
        '{"MultiModel":true,"priceDenomination":"USD"}'
    ) == MultiModelInfo(multi_model=True, price_denomination="USD")
    assert parse_multi_model_info('{"MultiModel":false}') == MultiModelInfo(
        multi_model=False
    )
    assert parse_multi_model_info("not json") == MultiModelInfo(
        multi_model=False
    )


def test_list_service_with_detail_adds_multi_model_catalog_and_health():
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
                model="default-model",
                verifiability="TeeML",
                additional_info=(
                    '{"MultiModel":true,"priceDenomination":"NATIVE"}'
                ),
            )
        ]
    )
    health = ServiceHealthMetric(
        service_type="chatbot",
        model="canonical-model",
        provider=PROVIDER,
        status="healthy",
        checks={"uptime": 99.5},
        performance={"response_time": {"avg": 88}},
        last_check="2026-06-12T00:00:00Z",
    )
    broker._fetch_service_health_metrics = MagicMock(return_value=[health])
    model = ProviderModelInfo(
        id="served-model",
        provider=PROVIDER,
        canonical_id="canonical-model",
    )
    broker._fetch_model_info = MagicMock(
        return_value={PROVIDER.lower(): [model]}
    )

    service = broker.list_service_with_detail()[0]

    assert service.multi_model is True
    assert service.price_denomination == "NATIVE"
    assert service.models == [model]
    assert service.models[0].health_metrics == health


def test_get_provider_models_uses_provider_catalog_and_enriches_health():
    broker = _build_broker()
    broker.get_service = MagicMock(
        return_value=ServiceWithDetail(
            provider=VALID_PROVIDER,
            service_type="chatbot",
            url="https://provider.example.com/",
            input_price=1,
            output_price=2,
            updated_at=3,
            model="default-model",
            verifiability="TeeML",
            additional_info=(
                '{"MultiModel":true,"priceDenomination":"USD"}'
            ),
        )
    )
    provider_response = MagicMock()
    provider_response.headers = {}
    provider_response.iter_content.return_value = [
        (
            b'{"object":"list","data":[{"id":"provider-model",'
            b'"canonical_id":"canonical-model","pricing":{"prompt":"1"}}]}'
        )
    ]
    health_response = MagicMock(status_code=200)
    health_response.json.return_value = {
        "services": [
            {
                "serviceType": "chatbot",
                "model": "canonical-model",
                "provider": VALID_PROVIDER,
                "status": "healthy",
                "checks": {"uptime": 99.9},
                "performance": {"response_time": {"avg": 50}},
                "lastCheck": "2026-06-12T00:00:00Z",
            }
        ]
    }

    with patch(
        "zerog_py_sdk.read_only.requests.get",
        side_effect=[provider_response, health_response],
    ) as get:
        result = broker.get_provider_models(VALID_PROVIDER)

    assert result == ProviderModels(
        provider=VALID_PROVIDER,
        url="https://provider.example.com/",
        multi_model=True,
        price_denomination="USD",
        default_model="default-model",
        models=result.models,
    )
    assert result.models[0].canonical_id == "canonical-model"
    assert result.models[0].health_metrics is not None
    assert get.call_args_list[0].args[0] == (
        "https://provider.example.com/v1/models"
    )


def test_get_provider_models_rejects_invalid_provider_response_shape():
    broker = _build_broker()
    broker.get_service = MagicMock(
        return_value=ServiceWithDetail(
            provider=VALID_PROVIDER,
            service_type="chatbot",
            url="https://provider.example.com",
            input_price=1,
            output_price=2,
            updated_at=3,
            model="default-model",
            verifiability="",
        )
    )
    response = MagicMock()
    response.headers = {}
    response.iter_content.return_value = [b'{"error":"bad response"}']

    with patch("zerog_py_sdk.read_only.requests.get", return_value=response):
        with pytest.raises(Exception, match='missing "data" array'):
            broker.get_provider_models(VALID_PROVIDER)
