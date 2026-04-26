"""
Shared pytest fixtures for 0G Storage SDK tests.

Fixtures defined here are automatically available to all test files
in the tests/ directory. No need to import them.

Run all unit tests (fast, no network):
    pytest -v -m "not integration"

Run integration tests only (requires testnet):
    pytest -v -m integration

Run everything:
    pytest -v
"""

import pytest
import sys
import os

# Ensure parent directory is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.test_config import (
    get_test_account,
    get_test_web3,
    TESTNET_RPC_URL,
    TESTNET_INDEXER_URL,
    TESTNET_CHAIN_ID,
)


# ─── Integration Test Fixtures ─────────────────────────────────────────
# These fixtures connect to the real 0G testnet.
# Only used when running integration tests.

@pytest.fixture
def test_account():
    """
    Real testnet account loaded from .env.

    Requires TEST_PRIVATE_KEY in .env or environment.
    Account must have testnet tokens from https://faucet.0g.ai
    """
    return get_test_account()


@pytest.fixture
def test_web3():
    """Web3 instance connected to 0G Galileo testnet."""
    return get_test_web3()


@pytest.fixture
def test_flow(test_web3):
    """FlowContract instance connected to testnet."""
    from contracts.flow import FlowContract
    return FlowContract(test_web3, network="testnet")


@pytest.fixture
def storage_nodes():
    """
    List of available storage nodes from the testnet indexer.
    Returns at least one node.
    """
    from core.indexer import Indexer
    indexer = Indexer(TESTNET_INDEXER_URL)
    nodes, err = indexer.select_nodes(1)
    assert err is None or len(nodes) > 0, f"Could not get storage nodes: {err}"
    return nodes


@pytest.fixture
def uploader(test_web3, test_flow, storage_nodes):
    """Uploader instance configured for testnet."""
    from core.uploader import Uploader
    return Uploader(
        nodes=storage_nodes,
        provider_rpc=test_web3.provider.endpoint_uri,
        flow=test_flow,
    )
