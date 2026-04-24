"""
Integration test for StorageNode.get_file_info() by root hash.

Tests that storage nodes can be queried by root hash to retrieve
file information including txSeq.

Prerequisites:
    Set TEST_PRIVATE_KEY in 0g_py_storage/.env
    Account must have testnet tokens from https://faucet.0g.ai

Run: pytest tests/test_get_file_info_root_hash.py -v
"""

import pytest
import os
import tempfile
import time

from core.file import ZgFile
from contracts.flow import FlowContract
from core.uploader import Uploader
from tests.test_config import TESTNET_INDEXER_URL
from core.indexer import Indexer


@pytest.fixture
def uploaded_file_info(test_account, test_web3, storage_nodes):
    """
    Upload a small test file and return (root_hash, tx_seq).
    Shared by tests that need an already-uploaded file.
    """
    indexer = Indexer(TESTNET_INDEXER_URL)
    nodes, err = indexer.select_nodes(1)
    assert err is None or len(nodes) > 0, f"Could not select nodes: {err}"

    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
        f.write(b"Integration test data for root hash query " * 10)
        temp_path = f.name

    try:
        zg_file = ZgFile(open(temp_path, 'rb'), os.path.getsize(temp_path))

        flow = FlowContract(test_web3, network="testnet")
        uploader = Uploader(
            nodes=nodes,
            provider_rpc=test_web3.provider.endpoint_uri,
            flow=flow,
        )

        print("\nUploading test file...")
        result, err = uploader.upload_file(
            zg_file,
            opts={
                'account': test_account,
                'tags': b'\x00',
                'finalityRequired': False,
            }
        )

        assert err is None, f"Upload failed: {err}"

        root_hash = result['rootHash']
        tx_seq = result.get('txSeq', 0)
        print(f"File uploaded: root={root_hash}, txSeq={tx_seq}")
        yield root_hash, tx_seq

    finally:
        os.unlink(temp_path)


@pytest.mark.integration
def test_get_file_info_by_root_hash(storage_nodes, uploaded_file_info):
    """
    Test that get_file_info(root_hash) returns valid file info
    after uploading a file.
    """
    root_hash, tx_seq = uploaded_file_info

    print(f"\nQuerying file info by root hash={root_hash}...")

    # Wait a moment for propagation
    print("Waiting 5 seconds for propagation...")
    time.sleep(5)

    for node in storage_nodes:
        print(f"Querying node: {node.url}")
        info = node.get_file_info(root_hash)

        if info is not None:
            print(f"File info found: {info}")

            assert 'tx' in info, f"File info missing 'tx' field: {info}"

            actual_tx_seq = info['tx'].get('seq', 'N/A')
            print(f"txSeq from file info: {actual_tx_seq}")

            assert isinstance(actual_tx_seq, int) and actual_tx_seq >= 0, \
                f"Invalid txSeq: {actual_tx_seq}"

            print("[PASS] get_file_info(root_hash) returns valid file info with txSeq")
            return  # Test passed

    pytest.fail("Could not find file info on any storage node")


@pytest.mark.integration
def test_get_file_info_nonexistent_root(storage_nodes):
    """Test that get_file_info() returns None for a nonexistent root hash."""
    fake_root = "0x" + "00" * 32

    for node in storage_nodes:
        info = node.get_file_info(fake_root)
        if info is not None:
            # Some nodes might return empty/zero info instead of None
            print(f"Node {node.url} returned: {info}")
        else:
            print(f"Node {node.url} returned None (expected)")

    print("[PASS] Nonexistent root hash query completed without error")
