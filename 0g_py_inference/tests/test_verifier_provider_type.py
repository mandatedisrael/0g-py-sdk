"""Guards on ResponseVerifier.get_signing_address for centralized providers.

Verifies TS PR #195 semantics: when a service advertises
ProviderType="centralized", the broker TEE signs responses (since the LLM
is an external service like OpenAI/Anthropic with no TEE key), so the
verifier must keep the broker tee_signer_address even if TargetSeparated
and TargetTeeAddress are set.
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.models import AdditionalInfo
from zerog_py_sdk.verifier import ResponseVerifier


BROKER_SIGNER = "0x1111111111111111111111111111111111111111"
TARGET_SIGNER = "0x2222222222222222222222222222222222222222"


def _service(additional_info: str) -> MagicMock:
    svc = MagicMock()
    svc.additional_info = additional_info
    return svc


class TestGetSigningAddress:
    def test_decentralized_separated_uses_target(self):
        info = json.dumps({
            "TargetSeparated": True,
            "TargetTeeAddress": TARGET_SIGNER,
        })
        addr = ResponseVerifier.get_signing_address(_service(info), BROKER_SIGNER)
        assert addr == TARGET_SIGNER

    def test_centralized_separated_uses_broker(self):
        info = json.dumps({
            "TargetSeparated": True,
            "TargetTeeAddress": TARGET_SIGNER,
            "ProviderType": "centralized",
        })
        addr = ResponseVerifier.get_signing_address(_service(info), BROKER_SIGNER)
        assert addr == BROKER_SIGNER

    def test_explicit_decentralized_matches_default(self):
        info = json.dumps({
            "TargetSeparated": True,
            "TargetTeeAddress": TARGET_SIGNER,
            "ProviderType": "decentralized",
        })
        addr = ResponseVerifier.get_signing_address(_service(info), BROKER_SIGNER)
        assert addr == TARGET_SIGNER

    def test_missing_target_address_uses_broker(self):
        info = json.dumps({"TargetSeparated": True})
        addr = ResponseVerifier.get_signing_address(_service(info), BROKER_SIGNER)
        assert addr == BROKER_SIGNER

    def test_not_separated_uses_broker(self):
        info = json.dumps({
            "TargetSeparated": False,
            "TargetTeeAddress": TARGET_SIGNER,
        })
        addr = ResponseVerifier.get_signing_address(_service(info), BROKER_SIGNER)
        assert addr == BROKER_SIGNER

    def test_empty_additional_info_uses_broker(self):
        addr = ResponseVerifier.get_signing_address(_service(""), BROKER_SIGNER)
        assert addr == BROKER_SIGNER

    def test_malformed_json_falls_back_to_broker(self):
        addr = ResponseVerifier.get_signing_address(
            _service("not-json"), BROKER_SIGNER
        )
        assert addr == BROKER_SIGNER


class TestAdditionalInfoProviderType:
    def test_defaults_to_decentralized(self):
        info = AdditionalInfo.from_json(json.dumps({}))
        assert info.provider_type == "decentralized"

    def test_parses_centralized(self):
        info = AdditionalInfo.from_json(json.dumps({"ProviderType": "centralized"}))
        assert info.provider_type == "centralized"

    def test_invalid_value_warns_and_defaults(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zerog_py_sdk.models"):
            info = AdditionalInfo.from_json(json.dumps({"ProviderType": "bogus"}))
        assert info.provider_type == "decentralized"
        assert any("Invalid ProviderType" in r.message for r in caplog.records)
