"""
Integration test for the skipIfFinalized upload option.

Tests that re-uploading an already finalized file with skipIfFinalized=True
skips the upload and returns immediately without submitting a new transaction.

Prerequisites:
    Set TEST_PRIVATE_KEY in 0g_py_storage/.env
    Account must have testnet tokens from https://faucet.0g.ai

NOTE: This test first uploads a file and waits for finalization, which may
take several minutes on testnet. It is marked with @pytest.mark.slow.

Run manually: pytest tests/test_skip_if_finalized.py -v -m slow --run-slow

Run: pytest tests/test_skip_if_finalized.py -v
"""

import pytest
import os
import tempfile
import time

from core.file import ZgFile


@pytest.fixture
def uploaded_file(test_account, test_web3, uploader):
    """
    Upload a test file and return (zg_file, temp_path, result).
    Caller is responsible for cleanup via temp_path.
    """
    test_content = f"skipIfFinalized test {time.time()} ".encode() * 50
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dat') as f:
        f.write(test_content)
        temp_path = f.name

    zg_file = ZgFile(open(temp_path, 'rb'), os.path.getsize(temp_path))
    print(f"\nTest file size: {zg_file.size()} bytes")

    result, err = uploader.upload_file(
        zg_file,
        opts={
            'account': test_account,
            'tags': b'\x00',
            'finalityRequired': False,
        }
    )
    assert err is None, f"Initial upload failed: {err}"
    return zg_file, temp_path, result


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skip(reason="Requires waiting for finalization (1-3 minutes). Run manually with: pytest -m slow --run-slow")
def test_skip_if_finalized_skips_upload(test_account, test_web3, uploader, storage_nodes, uploaded_file):
    """
    Test skipIfFinalized upload option.

    1. Upload a file using the no-receipt flow
    2. Wait for finalization (with timeout)
    3. Re-upload the same file with skipIfFinalized=True
    4. Verify no new transaction was submitted
    """
    zg_file, temp_path, first_result = uploaded_file
    root_hash = first_result['rootHash']
    first_tx_hash = first_result['txHash']
    first_tx_seq = first_result['txSeq']

    print(f"Initial upload: root={root_hash}, txSeq={first_tx_seq}, txHash={first_tx_hash}")

    try:
        # Wait for finalization (up to 3 minutes)
        print("\nWaiting for finalization (max 3 minutes)...")
        finalized = False
        max_wait = 180
        start_time = time.time()

        while time.time() - start_time < max_wait:
            for node in storage_nodes:
                info = node.get_file_info(root_hash)
                if info is not None and info.get('finalized', False):
                    finalized = True
                    print(f"File finalized! txSeq={info['tx']['seq']}")
                    break
            if finalized:
                break
            print(f"  Not finalized yet... ({int(time.time() - start_time)}s)")
            time.sleep(10)

        if not finalized:
            pytest.skip("File not finalized within timeout. Cannot test skipIfFinalized.")

        # Re-upload with skipIfFinalized=True
        print("\nRe-uploading with skipIfFinalized=True...")
        result2, err2 = uploader.upload_file(
            zg_file,
            opts={
                'account': test_account,
                'tags': b'\x00',
                'skipIfFinalized': True,
                'finalityRequired': False,
            }
        )
        assert err2 is None, f"Re-upload failed: {err2}"

        print(f"Re-upload result: txHash={result2['txHash']}, txSeq={result2['txSeq']}")

        # Verify no new transaction was submitted
        assert result2['txHash'] == '', \
            f"txHash should be empty when skipped, got: {result2['txHash']}"
        assert result2['rootHash'] == root_hash, \
            f"rootHash mismatch: {result2['rootHash']} != {root_hash}"

        print("\n[PASS] skipIfFinalized works correctly - upload was skipped")

    finally:
        os.unlink(temp_path)
