from zerog_py_sdk import (
    HARDHAT_CHAIN_ID,
    MAINNET_CHAIN_ID,
    TESTNET_CHAIN_ID,
    get_network_type,
)


def test_get_network_type_matches_typescript_network_names():
    assert get_network_type(MAINNET_CHAIN_ID) == "mainnet"
    assert get_network_type(TESTNET_CHAIN_ID) == "testnet"
    assert get_network_type(HARDHAT_CHAIN_ID) == "hardhat"


def test_get_network_type_reports_unknown_chain_ids():
    assert get_network_type(1) == "unknown"
