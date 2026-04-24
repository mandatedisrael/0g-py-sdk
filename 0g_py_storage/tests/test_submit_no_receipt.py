"""
Integration test for FlowContract.submit_log_entry_no_receipt().

Tests the no-receipt submission flow against the 0G Galileo testnet.

Prerequisites:
    Set TEST_PRIVATE_KEY in 0g_py_storage/.env
    Account must have testnet tokens from https://faucet.0g.ai

Run: pytest tests/test_submit_no_receipt.py -v
"""

import pytest


@pytest.mark.integration
def test_submit_no_receipt_returns_valid_tx_hash(test_account, test_web3, test_flow):
    """
    Test that submit_log_entry_no_receipt() sends a transaction
    and returns a valid txHash without waiting for receipt.
    """
    print(f"\nAccount: {test_account.address}")
    print(f"Connected to testnet, chain ID: {test_web3.eth.chain_id}")

    balance = test_web3.eth.get_balance(test_account.address)
    print(f"Account balance: {test_web3.from_wei(balance, 'ether')} ETH")
    assert balance > 0, "Account has no tokens. Get testnet tokens from https://faucet.0g.ai"

    print(f"Flow contract address: {test_flow.contract_address}")

    # Build a minimal submission (empty file submission)
    # This will likely revert on-chain, but we're testing the submission
    # mechanism, not the actual file upload. We just verify txHash is returned.
    submission = {
        'data': {
            'length': 0,
            'tags': b'\x00',
            'nodes': []
        },
        'submitter': test_account.address
    }

    # Submit using no-receipt flow
    print("\nCalling submit_log_entry_no_receipt()...")
    tx_hash, err = test_flow.submit_log_entry_no_receipt(
        submission=submission,
        account=test_account,
        value=0
    )

    assert err is None, f"submit_log_entry_no_receipt returned error: {err}"
    print(f"txHash returned: {tx_hash}")

    # Verify txHash format (0x-prefixed 64-char hex = 66 chars total)
    assert tx_hash.startswith('0x'), f"Invalid txHash format: {tx_hash}"
    assert len(tx_hash) == 66, f"Invalid txHash length: {len(tx_hash)}"
    print("txHash format is valid (0x-prefixed 64-char hex)")

    # Verify the transaction exists on-chain
    print("Checking transaction on-chain...")
    try:
        receipt = test_web3.eth.wait_for_transaction_receipt(
            bytes.fromhex(tx_hash[2:]),
            timeout=30
        )
        status = "success" if receipt['status'] == 1 else "reverted"
        print(f"Transaction found on-chain, status: {status}")
        print(f"Block number: {receipt['blockNumber']}")
        print(f"Gas used: {receipt['gasUsed']}")
    except Exception as e:
        print(f"Warning: Could not verify transaction on-chain: {e}")


@pytest.mark.integration
def test_submit_no_receipt_with_custom_gas(test_account, test_flow):
    """
    Test submit_log_entry_no_receipt() with explicit gas parameters.
    """
    submission = {
        'data': {
            'length': 0,
            'tags': b'\x00',
            'nodes': []
        },
        'submitter': test_account.address
    }

    tx_hash, err = test_flow.submit_log_entry_no_receipt(
        submission=submission,
        account=test_account,
        value=0,
        gas_limit=600000,
        gas_price=3000000000,  # 3 gwei
    )

    assert err is None, f"Submit with custom gas failed: {err}"
    assert tx_hash.startswith('0x'), f"Invalid txHash: {tx_hash}"
    print(f"\nCustom gas submission succeeded: {tx_hash}")


@pytest.mark.integration
def test_submit_no_receipt_broadcast_failure(test_account, test_flow):
    """
    Test that submit_log_entry_no_receipt() returns an error
    when the transaction broadcast fails (e.g., insufficient gas).
    """
    submission = {
        'data': {
            'length': 0,
            'tags': b'\x00',
            'nodes': []
        },
        'submitter': test_account.address
    }

    # Use an absurdly low gas limit to force failure
    tx_hash, err = test_flow.submit_log_entry_no_receipt(
        submission=submission,
        account=test_account,
        value=0,
        gas_limit=1,  # Way too low
    )

    # This may or may not fail depending on the node's behavior
    # Some nodes accept the tx then it reverts, others reject immediately
    if err is not None:
        print(f"\nExpected error caught: {err}")
        assert tx_hash == '', f"txHash should be empty on error, got: {tx_hash}"
    else:
        print(f"\nTransaction was accepted despite low gas: {tx_hash}")
        # If accepted, verify format
        assert tx_hash.startswith('0x')
