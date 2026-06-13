"""Structured return + on_log callback parity for InferenceManager.verify_service.

Mirrors the TS SDK's ``InferenceBroker.verifyService`` contract:
- silent by default (no stdout writes from the SDK itself)
- returns a typed ``VerificationResult`` instead of an ad-hoc dict
- emits ``VerificationStep`` entries to an optional ``on_log`` callback,
  and exposes the same sequence on ``result.steps``
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.inference import InferenceManager
from zerog_py_sdk.exceptions import NetworkError
from zerog_py_sdk.models import ServiceMetadata
from zerog_py_sdk.verifier import VerificationResult, VerificationStep


PROVIDER = "0x" + "ab" * 20


def _service() -> ServiceMetadata:
    return ServiceMetadata(
        provider=PROVIDER,
        service_type="chatbot",
        url="https://provider.example",
        input_price=0,
        output_price=0,
        updated_at=0,
        model="m",
        verifiability="TeeML",
        additional_info="{}",
    )


def _manager() -> InferenceManager:
    mgr = InferenceManager.__new__(InferenceManager)
    mgr.account = MagicMock(address=PROVIDER)
    mgr.contract = MagicMock()
    mgr.contract.functions.getAccount.return_value.call.side_effect = Exception(
        "no account"
    )
    return mgr


def _fake_quote_response(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    return resp


def test_verify_service_returns_typed_result(capsys):
    mgr = _manager()
    mgr.get_service = MagicMock(return_value=_service())
    mgr._extract_tee_signer_address = MagicMock(return_value=("0xsigner", "tdx"))
    mgr._verify_quote_with_automata = MagicMock(return_value=True)

    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_fake_quote_response({"quote": "deadbeef"}),
    ):
        result = mgr.verify_service(PROVIDER)

    assert isinstance(result, VerificationResult)
    assert result.success is True
    assert result.tee_signer == "0xsigner"
    assert result.model == "m"
    assert result.service_type == "chatbot"
    assert result.verifiability == "TeeML"
    assert result.steps, "steps should be populated even without on_log"
    assert all(isinstance(s, VerificationStep) for s in result.steps)
    # SDK must be silent — no stdout writes when on_log is not provided.
    assert capsys.readouterr().out == ""


def test_verify_service_on_log_receives_each_step(capsys):
    mgr = _manager()
    mgr.get_service = MagicMock(return_value=_service())
    mgr._extract_tee_signer_address = MagicMock(return_value=("0xsigner", "tdx"))
    mgr._verify_quote_with_automata = MagicMock(return_value=True)

    received: list[VerificationStep] = []

    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_fake_quote_response({"quote": "deadbeef"}),
    ):
        result = mgr.verify_service(PROVIDER, on_log=received.append)

    assert received, "on_log should fire at least once"
    assert all(isinstance(s, VerificationStep) for s in received)
    # The callback sequence must equal result.steps exactly.
    assert [(s.type, s.message) for s in received] == [
        (s.type, s.message) for s in result.steps
    ]
    # Still silent — on_log opting in must not also enable prints.
    assert capsys.readouterr().out == ""


def test_verify_service_quote_failure_marks_failure(capsys):
    mgr = _manager()
    mgr.get_service = MagicMock(return_value=_service())

    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_fake_quote_response({}, status=500),
    ):
        result = mgr.verify_service(PROVIDER)

    assert isinstance(result, VerificationResult)
    assert result.success is False
    assert result.quote_available is False
    assert any("Quote fetch failed" in e for e in result.errors)
    assert capsys.readouterr().out == ""


def test_verify_service_automata_rejection_marks_failure(capsys):
    mgr = _manager()
    mgr.get_service = MagicMock(return_value=_service())
    mgr._extract_tee_signer_address = MagicMock(
        return_value=("0xsigner", "tdx")
    )
    mgr._verify_quote_with_automata = MagicMock(return_value=False)

    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_fake_quote_response({"quote": "deadbeef"}),
    ):
        result = mgr.verify_service(PROVIDER)

    assert result.success is False
    assert result.attestation_verified is False
    assert result.attestation_method == "automata_contract"
    assert "Automata rejected" in result.attestation_error
    assert result.attestation_error in result.errors
    assert any(step.type == "error" for step in result.steps)
    assert capsys.readouterr().out == ""


def test_verify_service_automata_outage_remains_unavailable(capsys):
    mgr = _manager()
    mgr.get_service = MagicMock(return_value=_service())
    mgr._extract_tee_signer_address = MagicMock(
        return_value=("0xsigner", "tdx")
    )
    mgr._verify_quote_with_automata = MagicMock(
        side_effect=NetworkError(
            "Automata is unavailable",
            endpoint="https://1rpc.io/ata",
        )
    )

    with patch(
        "zerog_py_sdk.inference.requests.get",
        return_value=_fake_quote_response({"quote": "deadbeef"}),
    ):
        result = mgr.verify_service(PROVIDER)

    assert result.success is True
    assert result.attestation_verified is None
    assert result.attestation_method == "automata_contract"
    assert "unavailable" in result.attestation_error
    assert result.errors == []
    assert any(
        "Automata verification unavailable" in step.message
        for step in result.steps
    )
    assert capsys.readouterr().out == ""
