"""Parity tests for the TypeScript SDK speech-to-text billing modes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from zerog_py_sdk.extractors import SpeechToTextExtractor
from zerog_py_sdk.models import ServiceMetadata


@pytest.fixture
def extractor() -> SpeechToTextExtractor:
    service = ServiceMetadata(
        provider="0x0000000000000000000000000000000000000001",
        service_type="speech-to-text",
        url="https://provider.example.com",
        input_price=3,
        output_price=5,
        updated_at=0,
        model="whisper",
        verifiability="",
    )
    return SpeechToTextExtractor(service)


def test_duration_usage_uses_seconds_as_input(extractor):
    usage = '{"type":"duration","seconds":207}'
    assert extractor.get_input_count(usage) == 207
    assert extractor.get_output_count(usage) == 0


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(207.5, 208), (207.4, 207), (0.4, 1), (0, 0), (-5, 0)],
)
def test_duration_usage_matches_typescript_rounding(extractor, seconds, expected):
    usage = f'{{"type":"duration","seconds":{seconds}}}'
    assert extractor.get_input_count(usage) == expected


def test_positive_seconds_without_type_uses_duration_billing(extractor):
    assert extractor.get_input_count('{"seconds":42}') == 42
    assert extractor.get_output_count('{"seconds":42}') == 0


def test_token_usage_uses_input_and_output_tokens(extractor):
    usage = (
        '{"type":"tokens","input_tokens":120,"output_tokens":30}'
    )
    assert extractor.get_input_count(usage) == 120
    assert extractor.get_output_count(usage) == 30


def test_explicit_tokens_type_ignores_stray_seconds(extractor):
    usage = (
        '{"type":"tokens","input_tokens":120,"output_tokens":0,"seconds":99}'
    )
    assert extractor.get_input_count(usage) == 120
    assert extractor.get_output_count(usage) == 0


def test_token_usage_accepts_string_encoded_counts(extractor):
    usage = (
        '{"type":"tokens","input_tokens":"120","output_tokens":"30"}'
    )
    assert extractor.get_input_count(usage) == 120
    assert extractor.get_output_count(usage) == 30


@pytest.mark.parametrize("content", ["", "not json", "{}"])
def test_malformed_usage_returns_zero(extractor, content):
    assert extractor.get_input_count(content) == 0
    assert extractor.get_output_count(content) == 0
