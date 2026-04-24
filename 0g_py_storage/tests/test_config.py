"""
Testnet integration test configuration for 0G Storage SDK.

Provides network constants and lazy .env loading.
Fixtures are defined in conftest.py following pytest conventions.

SETUP:
    Create a .env file in the 0g_py_storage/ directory:

        TEST_PRIVATE_KEY=0xyour_private_key_here

    Ensure the account has testnet tokens from the faucet:
        https://faucet.0g.ai
"""

import os
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv, find_dotenv

# ─── Network Constants ─────────────────────────────────────────────────
# 0G Galileo Testnet
TESTNET_RPC_URL = "https://evmrpc-testnet.0g.ai"
TESTNET_INDEXER_URL = "https://indexer-storage-testnet-turbo.0g.ai"
TESTNET_CHAIN_ID = 16602

# ─── .env Loading (lazy) ──────────────────────────────────────────────
# Loaded on first call to get_test_account() or get_test_web3(),
# not at module import time. This allows unit tests to mock the
# environment without side effects.

_dotenv_loaded = False


def _ensure_dotenv():
    """Load .env file once, lazily. No-op on subsequent calls."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    # find_dotenv walks up from __file__ to locate .env
    # override=False: existing env vars (e.g. from CI) take precedence
    load_dotenv(find_dotenv(usecwd=True), override=False)


def get_test_account():
    """
    Load test account from TEST_PRIVATE_KEY environment variable.

    On first call, loads .env file if present (lazy initialization).
    Subsequent calls skip .env loading.

    Returns:
        LocalAccount instance

    Raises:
        ValueError: If TEST_PRIVATE_KEY is not set
    """
    _ensure_dotenv()

    private_key = os.environ.get('TEST_PRIVATE_KEY')
    if not private_key:
        raise ValueError(
            "TEST_PRIVATE_KEY environment variable is not set. "
            "Please set it in .env or export it before running tests."
        )

    try:
        return Account.from_key(private_key)
    except Exception as e:
        raise ValueError(f"Invalid TEST_PRIVATE_KEY: {e}") from e


def get_test_web3():
    """
    Create a Web3 instance connected to the 0G testnet.

    On first call, loads .env file if present (lazy initialization).

    Returns:
        Web3 instance connected to testnet

    Raises:
        ConnectionError: If connection to testnet fails
    """
    _ensure_dotenv()

    rpc_url = os.environ.get('TESTNET_RPC_URL', TESTNET_RPC_URL)
    web3 = Web3(Web3.HTTPProvider(rpc_url))

    if not web3.is_connected():
        raise ConnectionError(
            f"Failed to connect to 0G testnet at {rpc_url}. "
            "Check your network connection."
        )

    return web3
