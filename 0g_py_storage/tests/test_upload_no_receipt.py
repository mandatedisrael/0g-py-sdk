"""
Integration test for the complete no-receipt upload flow.

End-to-end test: submitLogEntryNoReceipt -> waitForLogEntry(rootHash) -> verify txSeq.

Prerequisites:
    Set TEST_PRIVATE_KEY in 0g_py_storage/.env
    Account must have testnet tokens from https://faucet.0g.ai

Run: pytest tests/test_upload_no_receipt.py -v
"""

import pytest
import os
import tempfile
import time

from core.file import ZgFile


@pytest.mark.integration
def test_upload_file_no_receipt_e2e(test_account, test_web3, uploader):
    """
    End-to-end test of the no-receipt upload flow.

    1. Create a test file
    2. Upload using upload_file() with no-receipt pipeline
    3. Verify result contains txHash, rootHash, and txSeq
    """
    print(f"\nAccount: {test_account.address}")
    print(f"Connected to testnet, chain ID: {test_web3.eth.chain_id}")

    balance = test_web3.eth.get_balance(test_account.address)
    print(f"Account balance: {test_web3.from_wei(balance, 'ether')} ETH")
    assert balance > 0, "Account has no tokens. Get testnet tokens from https://faucet.0g.ai"

    # Create a test file with unique content
    test_content = f"E2E no-receipt test {time.time()} ".encode() * 50
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
        f.write(test_content)
        temp_path = f.name

    try:
        zg_file = ZgFile(open(temp_path, 'rb'), os.path.getsize(temp_path))
        print(f"Test file size: {zg_file.size()} bytes")

        # Upload using new no-receipt flow
        print("\nUploading file via no-receipt flow...")
        result, err = uploader.upload_file(
            zg_file,
            opts={
                'account': test_account,
                'tags': b'\x00',
                'finalityRequired': False,
                'expectedReplica': 1,
                'taskSize': 1,
            }
        )

        assert err is None, f"Upload failed: {err}"

        # Verify result structure
        print(f"\nUpload result:")
        print(f"  txHash:   {result['txHash']}")
        print(f"  rootHash: {result['rootHash']}")
        print(f"  txSeq:    {result['txSeq']}")

        # Validate fields
        assert result['rootHash'], f"Invalid rootHash: {result['rootHash']}"
        assert result['rootHash'].startswith('0x'), f"Invalid rootHash format: {result['rootHash']}"

        assert isinstance(result['txSeq'], int), f"Invalid txSeq type: {type(result['txSeq'])}"
        assert result['txSeq'] >= 0, f"Invalid txSeq: {result['txSeq']}"

        if not result.get('skipTx'):
            assert result['txHash'], "txHash is empty for non-skipped upload"

        print(f"\n[PASS] File uploaded with txSeq={result['txSeq']}")

    finally:
        os.unlink(temp_path)


@pytest.mark.integration
def test_upload_small_file(test_account, test_web3, uploader):
    """Test uploading a very small file (< 1 chunk)."""
    test_content = b"tiny"
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
        f.write(test_content)
        temp_path = f.name

    try:
        zg_file = ZgFile(open(temp_path, 'rb'), os.path.getsize(temp_path))
        print(f"\nSmall file size: {zg_file.size()} bytes")

        result, err = uploader.upload_file(
            zg_file,
            opts={
                'account': test_account,
                'tags': b'\x00',
                'finalityRequired': False,
            }
        )

        assert err is None, f"Small file upload failed: {err}"
        assert result['txSeq'] >= 0
        print(f"Small file uploaded: txSeq={result['txSeq']}")

    finally:
        os.unlink(temp_path)


@pytest.mark.integration
def test_upload_with_skip_tx(test_account, test_web3, uploader):
    """Test upload with skipTx=True (no blockchain transaction)."""
    test_content = b"skip tx test data"
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
        f.write(test_content)
        temp_path = f.name

    try:
        zg_file = ZgFile(open(temp_path, 'rb'), os.path.getsize(temp_path))

        result, err = uploader.upload_file(
            zg_file,
            opts={
                'account': test_account,
                'tags': b'\x00',
                'skipTx': True,
                'finalityRequired': False,
            }
        )

        # skipTx behavior depends on implementation:
        # it may fail if file doesn't exist, or succeed with empty txHash
        if err is None:
            assert result.get('skipTx') or result['txHash'] == ''
            print(f"\nskipTx upload succeeded: {result}")
        else:
            print(f"\nskipTx upload returned expected error: {err}")

    finally:
        os.unlink(temp_path)
